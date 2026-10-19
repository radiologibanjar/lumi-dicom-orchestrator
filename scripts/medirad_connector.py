#!/usr/bin/env python3
"""
Lumi DICOM — MediRad Adapter
Copyright © 2026 Lumi DICOM. All rights reserved.

Bridge adapter: fetch order radiologi dari Web Service MediRad (RSU Kota Banjar)
dan forward ke Lumi DICOM Orchestrator.

Flow:
    1. POST /gettoken  → dapat x-token
    2. POST /getorderrad (header x-token, param tglAwal/tglAkhir) → list order
    3. Transform → POST /api/v1/worklist (Lumi DICOM)

Usage:
    python scripts/medirad_connector.py              # sekali fetch
    python scripts/medirad_connector.py --loop       # periodic (default 5 menit)
    python scripts/medirad_connector.py --start-date 2026-10-01 --end-date 2026-10-19
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# ─── Config ───────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "medirad.env"


def _load_config() -> None:
    """Load MEDIRAD_TOKEN and MEDIRAD_BASE_URL from config/medirad.env.

    Environment variables take precedence over the config file. The token
    is never logged or printed.
    """
    global MEDIRAD_BASE_URL, LUMI_DICOM_URL, LUMI_DICOM_API_KEY, FETCH_INTERVAL_MINUTES
    if CONFIG_PATH.exists():
        for line in CONFIG_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key == "MEDIRAD_TOKEN":
                os.environ.setdefault("MEDIRAD_TOKEN", value)
            elif key == "MEDIRAD_BASE_URL":
                MEDIRAD_BASE_URL = value
            elif key == "LUMI_DICOM_URL":
                LUMI_DICOM_URL = value
            elif key == "LUMI_DICOM_API_KEY":
                LUMI_DICOM_API_KEY = value
            elif key == "FETCH_INTERVAL_MINUTES" and value.isdigit():
                FETCH_INTERVAL_MINUTES = int(value)


_load_config()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("lumi-dicom.medirad")


# ─── MediRad API ─────────────────────────────────────────────────────────────

def get_medirad_token() -> str:
    """Ambil x-token MediRad dari environment atau config/medirad.env.

    Token tidak pernah ditampilkan di log atau output.
    """
    token = os.environ.get("MEDIRAD_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "MEDIRAD_TOKEN tidak diset. Set environment variable "
            "MEDIRAD_TOKEN atau isi config/medirad.env."
        )
    return token


def get_order_radiologi(token: str, tgl_awal: str, tgl_akhir: str) -> list:
    """GET /getorderrad → list order radiologi dari SIMRS via MediRad.

    MediRad gateway: parameter dikirim sebagai query parameter pada GET.
    Response: {"response": [...], "metaData": {"code": 200, ...}}
    """
    url = f"{MEDIRAD_BASE_URL}/getorderrad"
    headers = {"x-token": token, "Accept": "application/json"}
    params = {"tglAwal": tgl_awal, "tglAkhir": tgl_akhir}

    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        # Response gateway MediRad: {"response": [...], "metaData": {"code": 200}}
        orders = data.get("response") or data.get("data") or []
        if isinstance(orders, dict):
            orders = orders.get("list") or orders.get("orders") or []
        # Unwrap nested records (format integrasi AIRIS)
        if (
            isinstance(orders, list)
            and orders
            and isinstance(orders[0], dict)
            and orders[0].get("metadata")
            and ("response" in orders[0] or "data" in orders[0])
        ):
            orders = orders[0].get("response") or orders[0].get("data") or []
        code = data.get("metaData", {}).get("code") or data.get("metadata", {}).get("code")
        if code is not None and int(code) not in (200, 0):
            msg = data.get("metaData", {}).get("message") or "unknown error"
            raise ValueError(f"MediRad error {code}: {msg}")
        logger.info(f"Order radiologi diterima: {len(orders)} item")
        return orders
    except Exception as e:
        logger.error(f"Gagal fetch order dari MediRad: {e}")
        raise


# ─── Transform MediRad → Lumi DICOM ───────────────────────────────────────────

def transform_order(order: dict) -> dict:
    """Transform satu order MediRad ke format WorklistCreateRequest Lumi DICOM.

    Field MediRad (dari response /getorderrad) → Field Lumi DICOM:
        NoRadiology       → accession_number
        NoCM              → patient_id
        NamaPasien        → patient_name
        JK                → patient_sex (L→M, P→F)
        TglLahir          → patient_birth_date
        Modality_Code     → modality
        NamaDokterPengirim → referring_physician_name
        NamaPelayanan     → procedure_description
        TglPendaftaran    → scheduled_procedure_step_start_date
        KdPelayananRS     → procedure_code
        CatatanKlinis     → study_description
    """
    def normalize_date(val, default_today: bool = False):
        """Normalize tanggal ke YYYYMMDD.

        ``default_today=True`` hanya untuk tanggal yang wajar diisi hari ini
        (TglPendaftaran). TglLahir yang kosong harus tetap None — bukan
        tanggal hari ini (pura-pura pasien baru lahir).
        """
        if not val:
            return datetime.now().strftime("%Y%m%d") if default_today else None
        val = str(val).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%Y%m%d"):
            try:
                return datetime.strptime(val, fmt).strftime("%Y%m%d")
            except ValueError:
                continue
        if val:
            return val.replace("-", "")[:8]
        return datetime.now().strftime("%Y%m%d") if default_today else None

    def normalize_time(val):
        """Normalize jam ke HHMMSS."""
        if not val:
            return None
        val = str(val).strip()
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(val, fmt).strftime("%H%M%S")
            except ValueError:
                continue
        return val.replace(":", "")[:6] if val else None

    def format_patient_name(nama: str) -> str:
        """Gunakan nama persis seperti SIMRS, tanpa penambahan karakter."""
        if not nama or str(nama).strip().upper() in {"", "NULL", "-"}:
            return "UNKNOWN"
        return str(nama).strip()

    tgl = normalize_date(order.get("TglPendaftaran"), default_today=True)
    jam = normalize_time(order.get("TglPendaftaran"))
    source_id = f"medirad-{order.get('NoRadiology', '')}"

    return {
        "source_id": source_id,
        "accession_number": str(order.get("NoRadiology") or ""),
        "patient_id": str(order.get("NoCM") or ""),
        "patient_name": format_patient_name(order.get("NamaPasien") or ""),
        "patient_birth_date": normalize_date(order.get("TglLahir")),
        "patient_sex": "M" if order.get("JK") == "L" else "F" if order.get("JK") == "P" else None,
        "scheduled_procedure_step_start_date": tgl,
        "scheduled_procedure_step_start_time": jam,
        "modality": str(order.get("Modality_Code") or "OT"),
        "procedure_code": str(order.get("KdPelayananRS") or ""),
        "procedure_description": order.get("NamaPelayanan") or "",
        "referring_physician_name": order.get("NamaDokterPengirim") or "",
        "study_description": order.get("CatatanKlinis") if str(order.get("CatatanKlinis") or "").upper() not in {"", "NULL", "-"} else None,
        "source": "medirad",
    }


# ─── Lumi DICOM API ───────────────────────────────────────────────────────────

def forward_to_lumi(items: list) -> dict:
    """Forward list order ke Lumi DICOM POST /api/v1/worklist."""
    url = f"{LUMI_DICOM_URL}/api/v1/worklist"
    headers = {"X-API-Key": LUMI_DICOM_API_KEY, "Content-Type": "application/json"}

    success = 0
    failed = 0
    for item in items:
        try:
            resp = httpx.post(url, headers=headers, json=item, timeout=15)
            resp.raise_for_status()
            success += 1
        except Exception as e:  # noqa: BLE001 — 1 order gagal tak boleh hentikan batch
            failed += 1
            logger.warning(f"Forward gagal untuk {item.get('accession_number','?')}: {e}")

    logger.info(f"Forward ke Lumi DICOM: {success} sukses, {failed} gagal")
    return {"success": success, "failed": failed}


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_once(tgl_awal: str, tgl_akhir: str):
    """Fetch dari MediRad → forward ke Lumi DICOM."""
    logger.info(f"Fetch order radiologi {tgl_awal} s/d {tgl_akhir}")

    token = get_medirad_token()
    orders = get_order_radiologi(token, tgl_awal, tgl_akhir)
    logger.info(f"Token acquired and API call successful. Token length: {len(token)}")

    if not orders:
        logger.info("Tidak ada order radiologi")
        return {"success": 0, "failed": 0}

    # Order tanpa nomor radiologi tidak bisa jadi worklist (pernah masuk
    # sebagai baris sampah: accession kosong, nama UNKNOWN, dll).
    def _valid_order(o: dict) -> bool:
        acc = str(o.get("NoRadiology") or "").strip()
        return bool(acc) and acc.upper() not in {"NULL", "-"}

    valid = [o for o in orders if _valid_order(o)]
    skipped = len(orders) - len(valid)
    if skipped:
        logger.warning(f"Melewatkan {skipped} order tanpa NoRadiologi valid")

    transformed = [transform_order(o) for o in valid]
    return forward_to_lumi(transformed)


def main():
    parser = argparse.ArgumentParser(description="MediRad → Lumi DICOM connector")
    parser.add_argument("--loop", action="store_true", help="Periodic fetch")
    parser.add_argument("--start-date", default=None, help="Tanggal awal (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=None, help="Tanggal akhir (YYYY-MM-DD)")
    args = parser.parse_args()

    today = datetime.now()
    tgl_awal = args.start_date or (today - timedelta(days=7)).strftime("%Y-%m-%d")
    tgl_akhir = args.end_date or today.strftime("%Y-%m-%d")

    if args.loop:
        logger.info(f"Memulai loop setiap {FETCH_INTERVAL_MINUTES} menit")
        while True:
            try:
                result = run_once(tgl_awal, tgl_akhir)
                logger.info(f"Result: {result}")
            except Exception as e:  # noqa: BLE001 — loop tetap jalan di iterasi berikutnya
                logger.error(f"Fetch gagal: {e}")
            time.sleep(FETCH_INTERVAL_MINUTES * 60)
    else:
        result = run_once(tgl_awal, tgl_akhir)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

"""
Lumi DICOM — API Layer & Regression Tests
Copyright © 2026 Lumi DICOM. All rights reserved.

Regression tests for the HTTP layer and configuration loading:
- app bootstrap / middleware annotation resolution (Python <=3.13 NameError)
- API-key middleware behaviour on /api/v1/*
- worklist CRUD with procedure_code_sequence round-trip
- dashboard data feed (no embedded credential) and config loaders
"""

import json
import typing
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from lumi_dicom.__main__ import _resolve_tls
from lumi_dicom.api.server import create_app
from lumi_dicom.config import load_settings
from lumi_dicom.db.manager import DatabaseManager

API_KEY = "lumi-dicom-dev-key"
ROOT = Path(__file__).resolve().parent.parent


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def db(tmp_path):
    manager = DatabaseManager(db_path=str(tmp_path / "api_test.db"))
    manager.init()
    return manager


@pytest.fixture()
def app(db):
    return create_app(db_manager=db, config={"api": {"api_keys": [API_KEY]}})


@pytest.fixture()
def client(app):
    return TestClient(app)


def _find_middleware(stack, class_name: str):
    """Walk the Starlette middleware stack until a class name matches."""
    current, guard = stack, 0
    while current is not None and guard < 50:
        if type(current).__name__ == class_name:
            return current
        current = getattr(current, "app", None)
        guard += 1
    return None


def _worklist_payload(**overrides) -> dict:
    payload = {
        "accession_number": "ACC-API-001",
        "patient_id": "PAT-API-001",
        "patient_name": "DOE^JANE",
        "scheduled_procedure_step_start_date": "2026-10-19",
        "modality": "CT",
    }
    payload.update(overrides)
    return payload


# ── Bootstrap / middleware annotations ───────────────────────────────────────


def test_create_app_boots(client):
    """Regression #1: create_app must build the middleware stack.

    On Python <=3.13 annotations are evaluated eagerly, so an unresolved
    `Request` name in LumiAPIKeyMiddleware.dispatch raised NameError here.
    """
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "lumi-dicom"


def test_middleware_annotations_resolve(client):
    """The middleware's `request: Request` annotation must be resolvable."""
    client.get("/health")  # ensure the middleware stack is built
    mw = _find_middleware(app_middleware_stack(client), "LumiAPIKeyMiddleware")
    assert mw is not None, "LumiAPIKeyMiddleware not found in stack"
    hints = typing.get_type_hints(type(mw).dispatch)
    assert "request" in hints


def app_middleware_stack(client):
    return client.app.middleware_stack


# ── API key middleware ───────────────────────────────────────────────────────


def test_api_requires_key(client):
    assert client.get("/api/v1/worklist").status_code == 401
    assert (
        client.get(
            "/api/v1/worklist", headers={"X-API-Key": "wrong-key"}
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/worklist", headers={"X-API-Key": API_KEY}
        ).status_code
        == 200
    )


def test_health_is_public(client):
    assert client.get("/health").status_code == 200


# ── Worklist CRUD with procedure_code_sequence (#2, #3) ───────────────────────


def test_create_and_read_worklist_with_procedure_code_sequence(client, db):
    """Regression #2 (missing `json` import) and #3 (from_row decode).

    POST used to raise NameError when procedure_code_sequence was present;
    reading the stored row used to raise pydantic ValidationError.
    """
    payload = _worklist_payload(
        accession_number="ACC-SEQ-001",
        procedure_code_sequence=[
            {
                "code_value": "RND1",
                "coding_scheme_designator": "LUMI",
                "code_meaning": "Random test",
            }
        ],
    )
    headers = {"X-API-Key": API_KEY}

    created = client.post("/api/v1/worklist", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    item_id = created.json()["id"]

    listed = client.get("/api/v1/worklist", headers=headers)
    assert listed.status_code == 200, listed.text
    assert any(i["accession_number"] == "ACC-SEQ-001" for i in listed.json())

    detail = client.get(f"/api/v1/worklist/{item_id}", headers=headers)
    assert detail.status_code == 200, detail.text

    # DB round-trip keeps the field a JSON string (declared type)
    stored = db.get_worklist_item(item_id)
    assert isinstance(stored.procedure_code_sequence, str)
    assert json.loads(stored.procedure_code_sequence)[0]["code_value"] == "RND1"


def test_create_worklist_date_normalized(client):
    headers = {"X-API-Key": API_KEY}
    resp = client.post(
        "/api/v1/worklist", headers=headers, json=_worklist_payload()
    )
    assert resp.status_code == 201
    assert resp.json()["scheduled_procedure_step_start_date"] == "20261019"


def test_status_update_roundtrip(client):
    headers = {"X-API-Key": API_KEY}
    created = client.post(
        "/api/v1/worklist", headers=headers, json=_worklist_payload()
    )
    item_id = created.json()["id"]

    patched = client.patch(
        f"/api/v1/worklist/{item_id}/status",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "in_progress"

    bad = client.patch(
        f"/api/v1/worklist/{item_id}/status",
        headers=headers,
        json={"status": "not-a-status"},
    )
    assert bad.status_code == 422  # pydantic rejects unknown enum values


# ── Dashboard feed (#7) ──────────────────────────────────────────────────────


def test_dashboard_feed_needs_no_api_key(client):
    """The dashboard browser page must be able to load worklist data
    without embedding an X-API-Key credential."""
    headers = {"X-API-Key": API_KEY}
    client.post("/api/v1/worklist", headers=headers, json=_worklist_payload())

    resp = client.get("/dashboard/api/worklist")
    assert resp.status_code == 200, resp.text
    assert any(
        i["accession_number"] == "ACC-API-001" for i in resp.json()
    )

    # shared handler keeps validation: bad status filter still 400s
    assert client.get("/dashboard/api/worklist?status=nope").status_code == 400

    # /api/v1/* stays protected
    assert client.get("/api/v1/worklist").status_code == 401


def test_dashboard_feed_date_filter(client):
    """Filter tanggal memakai format YYYYMMDD (format kolom DB) —
    sama dengan yang dikirim dashboard setelah konversi dari input date."""
    from datetime import datetime

    headers = {"X-API-Key": API_KEY}
    today = datetime.now().strftime("%Y%m%d")
    client.post(
        "/api/v1/worklist",
        headers=headers,
        json=_worklist_payload(
            accession_number="ACC-DATE-001",
            scheduled_procedure_step_start_date=today,
        ),
    )

    in_range = client.get(f"/dashboard/api/worklist?date_from={today}&date_to={today}")
    assert in_range.status_code == 200
    assert any(i["accession_number"] == "ACC-DATE-001" for i in in_range.json())

    out_of_range = client.get("/dashboard/api/worklist?date_from=19990101&date_to=19990102")
    assert out_of_range.status_code == 200
    assert not any(i["accession_number"] == "ACC-DATE-001" for i in out_of_range.json())


# ── Realtime (WebSocket) ──────────────────────────────────────────────────────


def test_worklist_fingerprint_changes(db):
    import uuid as _uuid

    from lumi_dicom.dashboard import _worklist_fingerprint
    from lumi_dicom.models.worklist import WorklistItem, WorklistStatus

    fp1 = _worklist_fingerprint(db)
    db.create_worklist_item(
        WorklistItem(
            source_id=f"fp-{_uuid.uuid4().hex[:8]}",
            accession_number=f"ACC-FP-{_uuid.uuid4().hex[:6]}",
            study_instance_uid=_uuid.uuid4().hex,
            patient_id="P1",
            patient_name="FP^TEST",
            scheduled_procedure_step_start_date="20261019",
            modality="CT",
            status=WorklistStatus.PENDING,
            source="simrs",
        )
    )
    fp2 = _worklist_fingerprint(db)
    assert fp1 != fp2, "fingerprint harus berubah setelah INSERT"


def test_dashboard_ws_pushes_refresh_on_change(client):
    """Klien WS menerima {"type":"refresh"} ketika worklist berubah."""
    import concurrent.futures
    import time as _time
    import uuid as _uuid

    from lumi_dicom import dashboard
    from lumi_dicom.models.worklist import WorklistItem, WorklistStatus

    dashboard.WS_POLL_SECONDS = 0.1  # percepat deteksi untuk test
    try:
        with client.websocket_connect("/dashboard/ws") as ws:
            hello = ws.receive_json()
            assert hello == {"type": "connected"}

            # biar monitor mengambil baseline fingerprint dulu
            _time.sleep(0.4)

            # perubahan data langsung di DB (penulis proses apa pun)
            client.app.state.db_manager.create_worklist_item(
                WorklistItem(
                    source_id=f"ws-{_uuid.uuid4().hex[:8]}",
                    accession_number=f"ACC-WS-{_uuid.uuid4().hex[:6]}",
                    study_instance_uid=_uuid.uuid4().hex,
                    patient_id="P2",
                    patient_name="WS^TEST",
                    scheduled_procedure_step_start_date="20261019",
                    modality="MR",
                    status=WorklistStatus.PENDING,
                    source="simrs",
                )
            )

            with concurrent.futures.ThreadPoolExecutor() as ex:
                fut = ex.submit(ws.receive_json)
                msg = fut.result(timeout=10)  # gagal = TimeoutError, bukan hang
            assert msg == {"type": "refresh"}
    finally:
        dashboard.WS_POLL_SECONDS = 2.0


def test_dashboard_html_has_no_hardcoded_api_key(client):
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text
    assert "/dashboard/api/worklist" in html
    assert "lumi-dicom-dev-key" not in html


def test_dashboard_js_is_valid_syntax(client):
    """Regression: escape Python non-raw (`\\n`, `\\r\\n`) di dalam
    DASHBOARD_HTML pernah membuat regex/string JS pecah → syntax error →
    seluruh script gagal → UI stuck di 'Menghubungkan.../Memuat...'."""
    import os
    import shutil
    import subprocess
    import tempfile

    node = shutil.which("node")
    if node is None:
        pytest.skip("node tidak tersedia untuk validasi JS")

    html = client.get("/").text
    start = html.find("<script>")
    end = html.rfind("</script>")
    assert start != -1 and end != -1, "tag <script> tidak ditemukan"
    js = html[start + len("<script>"):end]

    fd, path = tempfile.mkstemp(suffix=".js")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(js)
        result = subprocess.run(
            [node, "--check", path], check=False, capture_output=True, text=True
        )
        assert result.returncode == 0, f"JS tidak valid:\n{result.stderr}"
    finally:
        os.unlink(path)


# ── Configuration loaders (#5) ───────────────────────────────────────────────


def test_load_settings_reads_default_yaml():
    settings = load_settings(str(ROOT / "config" / "default.yaml"))
    assert settings.api.port == 8765
    assert settings.api.api_keys == ["lumi-dicom-dev-key"]
    assert settings.database.path == "worklist.db"
    assert settings.mwl_scp.enabled is True
    assert settings.mwl_scp.ae_title == "LUMI_DICOM"
    assert settings.mwl_scp.tls_cert == ""  # tls.enabled is false
    assert settings.mpps.enabled is False
    assert settings.image_route.enabled is False
    assert settings.logging.level == "INFO"


def test_resolve_tls():
    assert _resolve_tls(None) == ("", "")
    assert _resolve_tls({}) == ("", "")
    assert _resolve_tls({"enabled": False, "cert_file": "c.pem"}) == ("", "")
    assert _resolve_tls(
        {"enabled": True, "cert_file": "c.pem", "key_file": "k.pem"}
    ) == ("c.pem", "k.pem")
    # enabled but no paths configured → still no TLS
    assert _resolve_tls({"enabled": True}) == ("", "")


def test_load_config_env_overrides(tmp_path, monkeypatch):
    """__main__.load_config keeps its env-override contract."""
    from lumi_dicom.__main__ import load_config

    monkeypatch.setenv("LUMI_DICOM_API__PORT", "18765")
    monkeypatch.setenv("LUMI_DICOM_MWL_SCP__ENABLED", "false")
    cfg = load_config(str(ROOT / "config" / "default.yaml"))
    assert cfg["api"]["port"] == 18765
    assert cfg["mwl_scp"]["enabled"] is False

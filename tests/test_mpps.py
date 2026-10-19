"""
Lumi DICOM — MPPS SCP Test
Copyright © 2026 Lumi DICOM. All rights reserved.

Membuktikan jalur status worklist via MPPS berfungsi:

1. Test handler langsung (tanpa jaringan) — kontrak handler + transisi DB.
2. Test integrasi jaringan — MPPSSCP sungguhan di port 31115, SCU
   pynetdicom mengirim N-CREATE (mulai) dan N-SET (selesai).

Transisi yang diverifikasi: pending → in_progress → completed,
plus baris mpps_events 'IN PROGRESS' → 'COMPLETED'.
"""

import asyncio
import logging
import types

from pydicom.dataset import Dataset
from pydicom.uid import generate_uid
from pynetdicom import AE
from pynetdicom.sop_class import ModalityPerformedProcedureStep

from lumi_dicom.db.manager import DatabaseManager
from lumi_dicom.dicom.mpps import MPPSSCP
from lumi_dicom.models.worklist import WorklistItem, WorklistStatus

logger = logging.getLogger("test-mpps")

ACCESSION = "ACC-MPPS-001"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _insert_test_item(db: DatabaseManager, accession: str = ACCESSION) -> WorklistItem:
    item = WorklistItem(
        source_id=f"test-mpps-{accession}",
        accession_number=accession,
        study_instance_uid=generate_uid(),
        patient_id="PAT001",
        patient_name="JOHN^DOE",
        patient_birth_date="19800101",
        patient_sex="M",
        scheduled_procedure_step_start_date="20261019",
        modality="CT",
        scheduled_station_aetitle="CT_STATION_1",
        procedure_description="CT Chest with Contrast",
        status=WorklistStatus.PENDING,
        source="simrs",
    )
    db.create_worklist_item(item)
    return item


def _worklist_status(db: DatabaseManager, accession: str) -> str:
    with db.connect() as conn:
        row = conn.execute(
            "SELECT status FROM worklist_items WHERE accession_number = ?",
            (accession,),
        ).fetchone()
    return row["status"] if row else ""


def _mpps_event_status(db: DatabaseManager, accession: str) -> str:
    with db.connect() as conn:
        row = conn.execute(
            """
            SELECT e.mpps_status FROM mpps_events e
            JOIN worklist_items w ON w.id = e.worklist_item_id
            WHERE w.accession_number = ?
            """,
            (accession,),
        ).fetchone()
    return row["mpps_status"] if row else ""


def _run_scu(port: int, accession: str) -> tuple[int, int]:
    """Kirim MPPS N-CREATE lalu N-SET; kembalikan (status_create, status_set)."""
    ae = AE(ae_title="LUMI_SCU_TEST")
    ae.add_requested_context(ModalityPerformedProcedureStep)
    assoc = ae.associate("127.0.0.1", port, ae_title="LUMI_MPPS")
    if not assoc.is_established:
        raise RuntimeError("Asosiasi MPPS gagal")

    sop_uid = generate_uid()

    n_create = Dataset()
    n_create.AccessionNumber = accession
    n_create.Modality = "CT"
    n_create.PerformedStationAETitle = "CT_STATION_1"
    status_ds, _ = assoc.send_n_create(
        n_create, ModalityPerformedProcedureStep, instance_uid=sop_uid
    )
    create_status = int(getattr(status_ds, "Status", -1))

    n_set = Dataset()
    n_set.AccessionNumber = accession  # handler membaca accession dari dataset
    n_set.PerformedProcedureStepStatus = "COMPLETED"
    status_ds2, _ = assoc.send_n_set(
        n_set, ModalityPerformedProcedureStep, instance_uid=sop_uid
    )
    set_status = int(getattr(status_ds2, "Status", -1))

    assoc.release()
    return create_status, set_status


# ── 1. Handler langsung (unit) ────────────────────────────────────────────────


def test_mpps_handlers_direct(tmp_path):
    db = DatabaseManager(str(tmp_path / "mpps_unit.db"))
    db.init()
    _insert_test_item(db)
    scp = MPPSSCP(db_manager=db)

    assert _worklist_status(db, ACCESSION) == "pending"

    # N-CREATE → in_progress
    ds = Dataset()
    ds.AccessionNumber = ACCESSION
    ds.Modality = "CT"
    ds.PerformedStationAETitle = "CT_STATION_1"
    ds.SOPInstanceUID = generate_uid()
    status, _ = scp._handle_n_create(types.SimpleNamespace(attribute_list=ds))
    assert status == 0x0000
    assert _worklist_status(db, ACCESSION) == "in_progress"
    assert _mpps_event_status(db, ACCESSION) == "IN PROGRESS"

    # N-SET → completed
    ds2 = Dataset()
    ds2.AccessionNumber = ACCESSION
    status, _ = scp._handle_n_set(types.SimpleNamespace(modification_list=ds2))
    assert status == 0x0000
    assert _worklist_status(db, ACCESSION) == "completed"
    assert _mpps_event_status(db, ACCESSION) == "COMPLETED"


def test_mpps_n_create_unknown_accession_is_harmless(tmp_path):
    """Accession tak dikenal tidak boleh melempar (modalitas bisa kirim duluan)."""
    db = DatabaseManager(str(tmp_path / "mpps_unk.db"))
    db.init()
    scp = MPPSSCP(db_manager=db)

    ds = Dataset()
    ds.AccessionNumber = "ACC-TIDAK-ADA"
    status, _ = scp._handle_n_create(types.SimpleNamespace(attribute_list=ds))
    assert status == 0x0000


# ── 2. Integrasi jaringan ─────────────────────────────────────────────────────


def test_mpps_scp_n_create_n_set_over_network(tmp_path):
    db = DatabaseManager(str(tmp_path / "mpps_net.db"))
    db.init()
    _insert_test_item(db)

    scp = MPPSSCP(db_manager=db, bind="127.0.0.1", port=31115)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run_server():
        server_task = asyncio.create_task(scp.serve())
        await asyncio.sleep(0.5)
        scu_result = await loop.run_in_executor(None, _run_scu, 31115, ACCESSION)
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass
        return scu_result

    try:
        create_status, set_status = loop.run_until_complete(_run_server())
    finally:
        loop.close()

    assert create_status == 0x0000, f"N-CREATE gagal: 0x{create_status:04X}"
    assert set_status == 0x0000, f"N-SET gagal: 0x{set_status:04X}"

    # Transisi status yang dijanjikan MPPS
    assert _worklist_status(db, ACCESSION) == "completed"
    assert _mpps_event_status(db, ACCESSION) == "COMPLETED"

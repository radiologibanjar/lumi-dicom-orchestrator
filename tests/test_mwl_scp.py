"""
Lumi DICOM — MWL SCP C-FIND Integration Test
Copyright © 2026 Lumi DICOM. All rights reserved.

Integration test: starts MWLSCP with a temp SQLite DB, inserts a worklist
item via DatabaseManager, then uses pynetdicom AE to associate and send a
C-FIND query. Asserts the response contains the correct patient data.
"""

import asyncio
import logging

from pydicom.dataset import Dataset
from pynetdicom import AE
from pynetdicom.sop_class import ModalityWorklistInformationFind

from lumi_dicom.db.manager import DatabaseManager
from lumi_dicom.dicom.mwl_scp import MWLSCP
from lumi_dicom.models.worklist import WorklistItem, WorklistStatus

logger = logging.getLogger("test-mwl-scp")

# ── Helpers ───────────────────────────────────────────────────────────────────


def _run_scu(port: int, patient_id: str) -> list[tuple[int, Dataset]]:
    """
    Run a DICOM C-FIND SCU against the MWL SCP.

    Returns a list of (status, dataset) tuples for all pending matches.
    """
    ae = AE(ae_title="TEST_SCU")
    ae.add_requested_context(ModalityWorklistInformationFind)

    assoc = ae.associate("127.0.0.1", port, ae_title="LUMI_DICOM")
    if not assoc.is_established:
        raise RuntimeError(
            f"Association failed: {assoc.acceptor.primitive}"
        )

    try:
        query = Dataset()
        query.PatientID = patient_id

        responses: list[tuple[int, Dataset]] = []
        for status, identifier in assoc.send_c_find(
            query, ModalityWorklistInformationFind
        ):
            if identifier is not None:
                responses.append((status.Status, identifier))
        return responses
    finally:
        assoc.release()


def _insert_test_item(
    db: DatabaseManager, procedure_code_sequence: str | None = None
) -> WorklistItem:
    """Insert a test worklist item and return it."""
    item = WorklistItem(
        source_id="test-c-find-001",
        accession_number="ACC20261016001",
        study_instance_uid="2.25.123456789012345678901234567890123456",
        patient_id="PAT001",
        patient_name="JOHN^DOE",
        patient_birth_date="19800101",
        patient_sex="M",
        scheduled_procedure_step_start_date="20261016",
        scheduled_procedure_step_start_time="080000",
        modality="CT",
        scheduled_station_aetitle="CT_STATION_1",
        procedure_description="CT Chest with Contrast",
        procedure_code_sequence=procedure_code_sequence,
        referring_physician_name="DR^SMITH",
        status=WorklistStatus.PENDING,
        source="simrs",
    )
    db.create_worklist_item(item)
    return item


# ── Test ──────────────────────────────────────────────────────────────────────


def test_mwl_scp_c_find(tmp_path, caplog):
    """
    Integration test: MWLSCP C-FIND round-trip.

    1. Start MWLSCP on a high port with a temp SQLite DB.
    2. Insert a worklist item via DatabaseManager.
    3. Use pynetdicom AE to associate and send C-FIND query.
    4. Assert the response contains the correct patient data.
    """
    caplog.set_level(logging.DEBUG, logger="lumi-dicom")

    # 1. Setup DB + SCP
    db_path = str(tmp_path / "test_mwl.db")
    db = DatabaseManager(db_path)
    db.init()

    item = _insert_test_item(db)

    port = 31112
    scp = MWLSCP(
        db_manager=db,
        ae_title="LUMI_DICOM",
        bind="127.0.0.1",
        port=port,
    )

    # 2. Start server in background asyncio task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run_server():
        server_task = asyncio.create_task(scp.serve())
        # Wait for server to bind
        await asyncio.sleep(0.5)

        # 3. Run SCU client (in executor so it doesn't block the loop)
        scu_result = await loop.run_in_executor(
            None, _run_scu, port, item.patient_id
        )

        # 4. Cancel server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

        return scu_result

    try:
        responses = loop.run_until_complete(_run_server())
    finally:
        loop.close()

    # 5. Assert responses
    assert len(responses) >= 1, "Expected at least one C-FIND match"

    # All returned items should have Pending status (0xFF00)
    for status, ds in responses:
        assert status == 0xFF00, f"Expected Pending (0xFF00), got 0x{status:04X}"

    # The first match should be our inserted item
    _, first_ds = responses[0]
    assert first_ds.PatientID == item.patient_id
    assert first_ds.PatientName == item.patient_name
    assert first_ds.AccessionNumber == item.accession_number
    assert first_ds.Modality == item.modality
    assert (
        first_ds.ScheduledProcedureStepStartDate
        == item.scheduled_procedure_step_start_date
    )
    assert first_ds.StudyInstanceUID == item.study_instance_uid


def test_mwl_scp_c_find_no_match(tmp_path):
    """
    Integration test: C-FIND with a PatientID that has no match
    should return an empty result set (no pending matches).
    """
    db_path = str(tmp_path / "test_mwl_nomatch.db")
    db = DatabaseManager(db_path)
    db.init()

    _insert_test_item(db)

    port = 31113
    scp = MWLSCP(
        db_manager=db,
        ae_title="LUMI_DICOM",
        bind="127.0.0.1",
        port=port,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run_server():
        server_task = asyncio.create_task(scp.serve())
        await asyncio.sleep(0.5)

        scu_result = await loop.run_in_executor(
            None, _run_scu, port, "NONEXISTENT_PID"
        )

        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

        return scu_result

    try:
        responses = loop.run_until_complete(_run_server())
    finally:
        loop.close()

    # No matches expected
    assert len(responses) == 0, "Expected zero matches for unknown PatientID"


def test_mwl_scp_c_find_with_procedure_code_sequence(tmp_path):
    """
    Regression: rows with a populated procedure_code_sequence must be
    servable over C-FIND.

    `WorklistItem.from_row` used to JSON-decode that column into a list,
    which violated the field's declared str type and made every reader of
    such a row — including this C-FIND path — raise ValidationError.
    """
    import json as _json

    db = DatabaseManager(str(tmp_path / "test_mwl_seq.db"))
    db.init()

    sequence = _json.dumps(
        [
            {
                "code_value": "RND1",
                "coding_scheme_designator": "LUMI",
                "code_meaning": "Random test",
            }
        ]
    )
    item = _insert_test_item(db, procedure_code_sequence=sequence)

    port = 31114
    scp = MWLSCP(
        db_manager=db,
        ae_title="LUMI_DICOM",
        bind="127.0.0.1",
        port=port,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run_server():
        server_task = asyncio.create_task(scp.serve())
        await asyncio.sleep(0.5)

        scu_result = await loop.run_in_executor(
            None, _run_scu, port, item.patient_id
        )

        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

        return scu_result

    try:
        responses = loop.run_until_complete(_run_server())
    finally:
        loop.close()

    assert len(responses) >= 1, "Expected at least one C-FIND match"

    status, ds = responses[0]
    assert status == 0xFF00, f"Expected Pending (0xFF00), got 0x{status:04X}"
    assert ds.PatientID == item.patient_id
    assert len(ds.ProcedureCodeSequence) == 1
    assert ds.ProcedureCodeSequence[0].CodeValue == "RND1"
    assert ds.ProcedureCodeSequence[0].CodingSchemeDesignator == "LUMI"
    assert ds.ProcedureCodeSequence[0].CodeMeaning == "Random test"

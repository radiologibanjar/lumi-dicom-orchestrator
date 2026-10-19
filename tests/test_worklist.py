"""
Lumi DICOM — Worklist Tests
Copyright © 2026 Lumi DICOM. All rights reserved.
"""

from lumi_dicom.db.manager import DatabaseManager
from lumi_dicom.models.worklist import (
    ProcedureCode,
    WorklistCreateRequest,
    WorklistItem,
    WorklistStatus,
)


class TestWorklistItem:
    """Test Lumi DICOM WorklistItem model."""

    def test_create_basic_item(self):
        item = WorklistItem(
            source_id="SIMRS-001",
            accession_number="ACC-001",
            patient_id="P001",
            patient_name="Patient^Test",
            scheduled_procedure_step_start_date="20261016",
            modality="CT",
        )
        assert item.status == WorklistStatus.PENDING
        assert item.source == "simrs"
        assert item.generate_uids() is None
        assert item.study_instance_uid is not None

    def test_status_lifecycle(self):
        item = WorklistItem(
            source_id="SIMRS-002",
            accession_number="ACC-002",
            patient_id="P002",
            patient_name="Doe^John",
            scheduled_procedure_step_start_date="20261016",
            modality="MR",
            status=WorklistStatus.IN_PROGRESS,
        )
        assert item.status == WorklistStatus.IN_PROGRESS

    def test_procedure_code_sequence(self):
        item = WorklistItem(
            source_id="SIMRS-003",
            accession_number="ACC-003",
            patient_id="P003",
            patient_name="Smith^Jane",
            scheduled_procedure_step_start_date="20261016",
            modality="CT",
            procedure_code_sequence='[{"code_value": "CT_HEAD"}]',
        )
        assert item.procedure_code_sequence is not None


class TestDatabaseManager:
    """Test Lumi DICOM DatabaseManager."""

    def test_init_and_crud(self, tmp_path):
        db = DatabaseManager(str(tmp_path / "test.db"))
        db.init()

        # Create
        item = WorklistItem(
            source_id="SIMRS-004",
            accession_number="ACC-004",
            patient_id="P004",
            patient_name="Test^Patient",
            scheduled_procedure_step_start_date="20261016",
            modality="CT",
            study_instance_uid="1.2.3.4.5",
        )
        item.generate_uids()
        item_id = db.create_worklist_item(item)
        assert item_id > 0

        # Read
        fetched = db.get_worklist_item(item_id)
        assert fetched is not None
        assert fetched.accession_number == "ACC-004"
        assert fetched.patient_id == "P004"

        # Upsert (update)
        item.source_id = "SIMRS-004"
        item.status = WorklistStatus.COMPLETED
        upsert_id, created = db.upsert_by_source_id(item)
        assert not created  # Updated, not created
        assert upsert_id == item_id

        # List
        items = db.list_worklist(status=WorklistStatus.COMPLETED)
        assert len(items) >= 1

        # Delete
        assert db.delete_worklist_item(item_id)
        assert db.get_worklist_item(item_id) is None

    def test_upsert_creates_new(self, tmp_path):
        db = DatabaseManager(str(tmp_path / "test.db"))
        db.init()

        item = WorklistItem(
            source_id="SIMRS-NEW",
            accession_number="ACC-NEW",
            patient_id="P005",
            patient_name="New^Patient",
            scheduled_procedure_step_start_date="20261016",
            modality="US",
        )
        item.generate_uids()
        item_id, created = db.upsert_by_source_id(item)
        assert created
        assert item_id > 0


class TestWorklistCreateRequest:
    """Test Lumi DICOM API request model."""

    def test_minimal_request(self):
        req = WorklistCreateRequest(
            accession_number="ACC-005",
            patient_id="P005",
            patient_name="Doe^Jane",
            scheduled_procedure_step_start_date="2026-10-16",
            modality="CT",
        )
        assert req.accession_number == "ACC-005"
        assert req.source == "simrs"

    def test_full_request(self):
        req = WorklistCreateRequest(
            accession_number="ACC-006",
            patient_id="P006",
            patient_name="Smith^Bob",
            scheduled_procedure_step_start_date="2026-10-16",
            modality="MR",
            patient_birth_date="1990-01-02",
            patient_sex="M",
            procedure_description="MRI Brain",
            procedure_code_sequence=[
                ProcedureCode(
                    code_value="MR_BRAIN",
                    coding_scheme_designator="LUMI",
                    code_meaning="MRI Brain",
                )
            ],
        )
        assert req.patient_sex == "M"
        assert req.modality == "MR"

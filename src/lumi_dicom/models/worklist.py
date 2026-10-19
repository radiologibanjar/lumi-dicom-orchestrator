"""
Lumi DICOM — Worklist Models
Copyright © 2026 Lumi DICOM. All rights reserved.

Pydantic models and enums for Lumi DICOM worklist items.
"""

import uuid
from enum import Enum

from pydantic import BaseModel, Field


class WorklistStatus(str, Enum):
    """Lumi DICOM worklist status lifecycle."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ProcedureCode(BaseModel):
    """A single entry in a DICOM Code Sequence."""
    code_value: str
    coding_scheme_designator: str
    code_meaning: str


class WorklistItem(BaseModel):
    """Canonical Lumi DICOM worklist item — source of truth for MWL."""

    # ── Identifiers ─────────────────────────────────────────────────────────
    source_id: str = Field(..., description="Unique ID dari SIMRS (idempotency)")
    accession_number: str = Field(..., description="DICOM AccessionNumber (0008,0050)")
    study_instance_uid: str | None = Field(None, description="DICOM StudyInstanceUID")
    requested_procedure_id: str | None = Field(None)

    # ── Patient ─────────────────────────────────────────────────────────────
    patient_id: str = Field(..., description="DICOM PatientID (0010,0020)")
    patient_name: str = Field(..., description="DICOM PatientName (0010,0010)")
    patient_birth_date: str | None = Field(None, description="YYYYMMDD")
    patient_sex: str | None = Field(None, description="M/F/O")
    patient_weight: str | None = Field(None, description="kg")

    # ── Scheduled Procedure Step ────────────────────────────────────────────
    scheduled_procedure_step_start_date: str = Field(..., description="YYYYMMDD")
    scheduled_procedure_step_start_time: str | None = Field(None, description="HHMMSS")
    modality: str = Field(..., description="DICOM Modality (0008,0060)")
    scheduled_station_aetitle: str | None = Field(None)

    # ── Procedure ──────────────────────────────────────────────────────────
    procedure_code: str | None = Field(None)
    procedure_description: str | None = Field(None)
    procedure_code_sequence: str | None = Field(
        None, description="JSON-encoded ProcedureCodeSequence"
    )

    # ── Physician & Study ──────────────────────────────────────────────────
    referring_physician_name: str | None = Field(None)
    study_description: str | None = Field(None)
    study_id: str | None = Field(None)

    # ── Lumi DICOM internal ────────────────────────────────────────────────
    status: WorklistStatus = Field(default=WorklistStatus.PENDING)
    source: str = Field(default="simrs", description="Source system")
    external_id: str | None = Field(None)

    # ── Tracking ───────────────────────────────────────────────────────────
    id: int | None = Field(None, description="Row ID (set by DB)")
    created_at: str | None = Field(None)
    updated_at: str | None = Field(None)

    @classmethod
    def from_row(cls, row) -> "WorklistItem":
        """Create WorklistItem from a sqlite3.Row.

        ``procedure_code_sequence`` stays a JSON-encoded string (its
        declared type) — decoding it to a list here used to make every
        read of a populated row fail pydantic validation. Consumers that
        need the structures (e.g. the MWL SCP) call ``json.loads``.
        """
        data = dict(row)
        if "status" in data and isinstance(data["status"], str):
            data["status"] = WorklistStatus(data["status"])
        return cls(**data)

    def generate_uids(self):
        """Generate StudyInstanceUID if not set.

        Produces a valid DICOM UID (digits and dots only) under the
        Lumi DICOM root 2.25.<bigint>, which is the UUID-derived OID
        arc that guarantees uniqueness without a registration authority.
        """
        if not self.study_instance_uid:
            # 2.25.<decimal UUID int> is the standard UUID-derived UID arc
            uid_int = uuid.uuid4().int
            self.study_instance_uid = f"2.25.{uid_int}"


# ── API Request/Response Models ──────────────────────────────────────────────

class WorklistCreateRequest(BaseModel):
    """Request body untuk POST /api/v1/worklist — dari SIMRS/FHIR."""

    # Wajib
    accession_number: str
    patient_id: str
    patient_name: str
    scheduled_procedure_step_start_date: str  # YYYYMMDD atau YYYY-MM-DD
    modality: str

    # Opsional
    source_id: str | None = None
    study_instance_uid: str | None = None
    requested_procedure_id: str | None = None
    patient_birth_date: str | None = None
    patient_sex: str | None = None
    patient_weight: str | None = None
    scheduled_procedure_step_start_time: str | None = None
    scheduled_station_aetitle: str | None = None
    procedure_code: str | None = None
    procedure_description: str | None = None
    procedure_code_sequence: list[ProcedureCode] | None = None
    referring_physician_name: str | None = None
    study_description: str | None = None
    study_id: str | None = None
    source: str = "simrs"
    external_id: str | None = None


class WorklistStatusUpdate(BaseModel):
    """Request body untuk PATCH /api/v1/worklist/{id}/status."""

    status: WorklistStatus


class WorklistResponse(BaseModel):
    """Response untuk single worklist item."""

    id: int
    accession_number: str
    study_instance_uid: str | None
    patient_id: str
    patient_name: str
    patient_birth_date: str | None
    patient_sex: str | None
    scheduled_procedure_step_start_date: str
    scheduled_procedure_step_start_time: str | None
    modality: str
    scheduled_station_aetitle: str | None
    procedure_description: str | None
    referring_physician_name: str | None
    status: str
    source: str
    created_at: str
    updated_at: str

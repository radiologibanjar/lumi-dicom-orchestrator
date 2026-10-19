"""
Lumi DICOM — API Routes
Copyright © 2026 Lumi DICOM. All rights reserved.

REST API endpoints untuk Lumi DICOM Orchestrator.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from lumi_dicom.db.manager import DatabaseManager
from lumi_dicom.models.worklist import (
    WorklistCreateRequest,
    WorklistItem,
    WorklistResponse,
    WorklistStatus,
    WorklistStatusUpdate,
)

logger = logging.getLogger("lumi-dicom")
router = APIRouter()


# ─── Dependencies ───────────────────────────────────────────────────────────

from fastapi import Request


def get_db(request: Request) -> DatabaseManager:
    """FastAPI dependency: return DatabaseManager from app.state."""
    return request.app.state.db_manager


# ─── Health ─────────────────────────────────────────────────────────────────

@router.get("/health", tags=["system"])
def health_check():
    """Lumi DICOM health check."""
    return {
        "status": "ok",
        "service": "lumi-dicom",
        "brand": "Lumi DICOM",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Worklist Endpoints ─────────────────────────────────────────────────────

@router.get("/api/v1/worklist", response_model=list[WorklistResponse], tags=["worklist"])
def list_worklist(
    db: Annotated[DatabaseManager, Depends(get_db)],
    status_filter: str | None = Query(None, alias="status"),
    modality: str | None = Query(None),
    station_ae: str | None = Query(None, alias="station"),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    patient_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List worklist items dengan filter opsional."""
    status_enum = None
    if status_filter:
        try:
            status_enum = WorklistStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status_filter}. "
                       f"Valid: pending, in_progress, completed, cancelled",
            )

    items = db.list_worklist(
        status=status_enum,
        modality=modality,
        station_ae=station_ae,
        date_from=date_from,
        date_to=date_to,
        patient_id=patient_id,
        limit=limit,
        offset=offset,
    )

    return [
        WorklistResponse(
            id=item.id,
            accession_number=item.accession_number,
            study_instance_uid=item.study_instance_uid,
            patient_id=item.patient_id,
            patient_name=item.patient_name,
            patient_birth_date=item.patient_birth_date,
            patient_sex=item.patient_sex,
            scheduled_procedure_step_start_date=item.scheduled_procedure_step_start_date,
            scheduled_procedure_step_start_time=item.scheduled_procedure_step_start_time,
            modality=item.modality,
            scheduled_station_aetitle=item.scheduled_station_aetitle,
            procedure_description=item.procedure_description,
            referring_physician_name=item.referring_physician_name,
            status=item.status.value,
            source=item.source,
            created_at=item.created_at or "",
            updated_at=item.updated_at or "",
        )
        for item in items
    ]


@router.post("/api/v1/worklist", response_model=WorklistResponse, status_code=201, tags=["worklist"])
def create_worklist(
    body: WorklistCreateRequest,
    db: Annotated[DatabaseManager, Depends(get_db)],
):
    """Buat worklist item baru dari order SIMRS/FHIR."""
    # Normalisasi tanggal: YYYY-MM-DD → YYYYMMDD
    date_str = body.scheduled_procedure_step_start_date.replace("-", "")

    # Generate source_id jika tidak ada
    source_id = body.source_id or f"{body.accession_number}-{body.patient_id}"

    # Build procedure_code_sequence JSON
    proc_seq_json = None
    if body.procedure_code_sequence:
        proc_seq_json = json.dumps([
            {
                "code_value": pc.code_value,
                "coding_scheme_designator": pc.coding_scheme_designator,
                "code_meaning": pc.code_meaning,
            }
            for pc in body.procedure_code_sequence
        ])

    item = WorklistItem(
        source_id=source_id,
        accession_number=body.accession_number,
        study_instance_uid=body.study_instance_uid,
        requested_procedure_id=body.requested_procedure_id,
        patient_id=body.patient_id,
        patient_name=body.patient_name,
        patient_birth_date=body.patient_birth_date.replace("-", "") if body.patient_birth_date else None,
        patient_sex=body.patient_sex,
        patient_weight=body.patient_weight,
        scheduled_procedure_step_start_date=date_str,
        scheduled_procedure_step_start_time=body.scheduled_procedure_step_start_time,
        modality=body.modality,
        scheduled_station_aetitle=body.scheduled_station_aetitle,
        procedure_code=body.procedure_code,
        procedure_description=body.procedure_description,
        procedure_code_sequence=proc_seq_json,
        referring_physician_name=body.referring_physician_name,
        study_description=body.study_description,
        study_id=body.study_id,
        status=WorklistStatus.PENDING,
        source=body.source,
        external_id=body.external_id,
    )
    item.generate_uids()

    item_id, created = db.upsert_by_source_id(item)

    # Re-fetch to get timestamps
    saved = db.get_worklist_item(item_id)

    logger.info(
        "Lumi DICOM worklist %s: accession=%s patient=%s modality=%s",
        "created" if created else "updated",
        saved.accession_number,
        saved.patient_id,
        saved.modality,
    )

    return WorklistResponse(
        id=saved.id,
        accession_number=saved.accession_number,
        study_instance_uid=saved.study_instance_uid,
        patient_id=saved.patient_id,
        patient_name=saved.patient_name,
        patient_birth_date=saved.patient_birth_date,
        patient_sex=saved.patient_sex,
        scheduled_procedure_step_start_date=saved.scheduled_procedure_step_start_date,
        scheduled_procedure_step_start_time=saved.scheduled_procedure_step_start_time,
        modality=saved.modality,
        scheduled_station_aetitle=saved.scheduled_station_aetitle,
        procedure_description=saved.procedure_description,
        referring_physician_name=saved.referring_physician_name,
        status=saved.status.value,
        source=saved.source,
        created_at=saved.created_at or "",
        updated_at=saved.updated_at or "",
    )


@router.get("/api/v1/worklist/{item_id}", response_model=WorklistResponse, tags=["worklist"])
def get_worklist_item(
    item_id: int,
    db: Annotated[DatabaseManager, Depends(get_db)],
):
    """Detail worklist item by ID."""
    item = db.get_worklist_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Worklist item not found")

    return WorklistResponse(
        id=item.id,
        accession_number=item.accession_number,
        study_instance_uid=item.study_instance_uid,
        patient_id=item.patient_id,
        patient_name=item.patient_name,
        patient_birth_date=item.patient_birth_date,
        patient_sex=item.patient_sex,
        scheduled_procedure_step_start_date=item.scheduled_procedure_step_start_date,
        scheduled_procedure_step_start_time=item.scheduled_procedure_step_start_time,
        modality=item.modality,
        scheduled_station_aetitle=item.scheduled_station_aetitle,
        procedure_description=item.procedure_description,
        referring_physician_name=item.referring_physician_name,
        status=item.status.value,
        source=item.source,
        created_at=item.created_at or "",
        updated_at=item.updated_at or "",
    )


@router.patch("/api/v1/worklist/{item_id}/status", response_model=WorklistResponse, tags=["worklist"])
def update_worklist_status(
    item_id: int,
    body: WorklistStatusUpdate,
    db: Annotated[DatabaseManager, Depends(get_db)],
):
    """Update status worklist item."""
    item = db.get_worklist_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Worklist item not found")

    success = db.update_status(item_id, body.status)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update status")

    updated = db.get_worklist_item(item_id)

    logger.info(
        "Lumi DICOM worklist %s: status → %s",
        updated.accession_number,
        updated.status.value,
    )

    return WorklistResponse(
        id=updated.id,
        accession_number=updated.accession_number,
        study_instance_uid=updated.study_instance_uid,
        patient_id=updated.patient_id,
        patient_name=updated.patient_name,
        patient_birth_date=updated.patient_birth_date,
        patient_sex=updated.patient_sex,
        scheduled_procedure_step_start_date=updated.scheduled_procedure_step_start_date,
        scheduled_procedure_step_start_time=updated.scheduled_procedure_step_start_time,
        modality=updated.modality,
        scheduled_station_aetitle=updated.scheduled_station_aetitle,
        procedure_description=updated.procedure_description,
        referring_physician_name=updated.referring_physician_name,
        status=updated.status.value,
        source=updated.source,
        created_at=updated.created_at or "",
        updated_at=updated.updated_at or "",
    )


@router.delete("/api/v1/worklist/{item_id}", tags=["worklist"])
def delete_worklist_item(
    item_id: int,
    db: Annotated[DatabaseManager, Depends(get_db)],
):
    """Hapus worklist item."""
    item = db.get_worklist_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Worklist item not found")

    db.delete_worklist_item(item_id)

    logger.info(
        "Lumi DICOM worklist deleted: accession=%s",
        item.accession_number,
    )

    return {"deleted": True, "accession_number": item.accession_number}


# ─── Modalitas Endpoints ────────────────────────────────────────────────────

@router.get("/api/v1/modalities", tags=["modalities"])
def list_modalities(
    db: Annotated[DatabaseManager, Depends(get_db)],
):
    """List registered modalities."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM modalities WHERE is_active = 1 ORDER BY ae_title"
        ).fetchall()
        return [dict(r) for r in rows]


# ─── Audit Endpoints ────────────────────────────────────────────────────────

@router.get("/api/v1/audit", tags=["audit"])
def list_audit(
    db: Annotated[DatabaseManager, Depends(get_db)],
    action: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """List audit log entries."""
    with db.connect() as conn:
        if action:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE action = ? ORDER BY timestamp DESC LIMIT ?",
                (action, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

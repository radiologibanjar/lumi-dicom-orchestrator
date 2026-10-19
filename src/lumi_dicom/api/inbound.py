"""
Lumi DICOM — Inbound API Endpoints
Copyright © 2026 Lumi DICOM. All rights reserved.

Endpoints for receiving HL7 v2 and FHIR R4 inbound messages
and mapping them to Lumi DICOM worklist items.
"""

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from lumi_dicom.db.manager import DatabaseManager
from lumi_dicom.inbound.fhir import FHIRError, map_fhir_to_worklist
from lumi_dicom.inbound.hl7 import parse_hl7_message
from lumi_dicom.models.worklist import (
    WorklistResponse,
)

logger = logging.getLogger("lumi-dicom")
router = APIRouter()


# ─── Dependencies ───────────────────────────────────────────────────────────

def get_db(request: Request) -> DatabaseManager:
    """FastAPI dependency: return DatabaseManager from app.state."""
    return request.app.state.db_manager


# ─── Health ─────────────────────────────────────────────────────────────────

@router.get("/api/v1/inbound/health", tags=["inbound"])
def inbound_health_check():
    """Health check for inbound module."""
    return {
        "status": "ok",
        "service": "lumi-dicom-inbound",
        "brand": "Lumi DICOM",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── HL7 Endpoint ───────────────────────────────────────────────────────────

@router.post(
    "/api/v1/inbound/hl7",
    response_model=WorklistResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["inbound"],
)
async def receive_hl7(
    request: Request,
    db: Annotated[DatabaseManager, Depends(get_db)],
):
    """Receive raw HL7 v2 ORM^O01 message dan simpan ke worklist.

    Body harus berupa raw HL7 message (text/plain).
    """
    # Read raw body as text
    body_bytes = await request.body()
    raw_message = body_bytes.decode("utf-8", errors="replace")

    if not raw_message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty HL7 message body",
        )

    # Parse HL7 message
    try:
        item = parse_hl7_message(raw_message)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"HL7 parse error: {e!s}",
        )
    except Exception as e:
        logger.exception("Lumi DICOM HL7 parse failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error parsing HL7: {e!s}",
        )

    # Store in database
    try:
        item_id, created = db.upsert_by_source_id(item)
    except Exception as e:
        logger.exception("Lumi DICOM HL7 database upsert failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e!s}",
        )

    # Re-fetch to get timestamps
    saved = db.get_worklist_item(item_id)

    logger.info(
        "Lumi DICOM HL7 worklist %s: accession=%s patient=%s modality=%s",
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


# ─── FHIR Endpoint ──────────────────────────────────────────────────────────

@router.post(
    "/api/v1/inbound/fhir",
    response_model=WorklistResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["inbound"],
)
def receive_fhir(
    data: dict,
    db: Annotated[DatabaseManager, Depends(get_db)],
):
    """Receive FHIR R4 JSON (ServiceRequest, ImagingStudy, atau Bundle)
    dan simpan ke worklist.
    """
    # Map FHIR to WorklistItem
    try:
        item = map_fhir_to_worklist(data)
    except FHIRError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"FHIR mapping error: {e!s}",
        )
    except Exception as e:
        logger.exception("Lumi DICOM FHIR mapping failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error mapping FHIR: {e!s}",
        )

    # Store in database
    try:
        item_id, created = db.upsert_by_source_id(item)
    except Exception as e:
        logger.exception("Lumi DICOM FHIR database upsert failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e!s}",
        )

    # Re-fetch to get timestamps
    saved = db.get_worklist_item(item_id)

    logger.info(
        "Lumi DICOM FHIR worklist %s: accession=%s patient=%s modality=%s",
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

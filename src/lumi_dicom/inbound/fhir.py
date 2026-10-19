"""
Lumi DICOM — FHIR R4 Inbound Mapper
Copyright © 2026 Lumi DICOM. All rights reserved.

Maps FHIR R4 resources (ServiceRequest, ImagingStudy, Bundle)
to Lumi DICOM WorklistItem model.
"""

import uuid
from datetime import datetime

from lumi_dicom.models.worklist import WorklistItem, WorklistStatus


class FHIRError(Exception):
    """Raised when FHIR data is missing required fields or is invalid."""


def _extract_patient_id(reference: str) -> str:
    """Extract patient ID from FHIR reference like 'Patient/xxx' → 'xxx'."""
    if not reference:
        raise FHIRError("Patient reference is required")
    parts = reference.split("/")
    if len(parts) == 2 and parts[0] == "Patient":
        return parts[1]
    # Fallback: return as-is if not a standard Patient/xxx reference
    return reference


def _extract_identifier_value(identifier: dict) -> str:
    """Extract accession number from FHIR Identifier.

    Returns the 'value' field directly — this is the accession number.
    System is not combined to keep the accession clean and match
    how SIMRS/HIS systems typically send it.
    """
    if "value" not in identifier:
        raise FHIRError("Identifier must have a 'value' field")
    return str(identifier["value"])


def _format_date(date_str: str) -> str:
    """Convert various date formats to YYYYMMDD."""
    if not date_str:
        raise FHIRError("Date field is required")
    
    # Try parsing different date formats
    formats = [
        "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601 with timezone
        "%Y-%m-%dT%H:%M:%S",     # ISO 8601 without timezone
        "%Y-%m-%d",              # YYYY-MM-DD
        "%Y%m%d",                # YYYYMMDD
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y%m%d")
        except ValueError:
            continue
    
    # If all formats fail, return as-is (assume already YYYYMMDD)
    return date_str


def _parse_service_request(resource: dict, patient_resource: dict | None = None) -> WorklistItem:
    """Parse a FHIR R4 ServiceRequest resource."""
    
    # Accession number from identifier
    identifiers = resource.get("identifier", [])
    if not identifiers:
        raise FHIRError("ServiceRequest must have at least one identifier for accession_number")
    accession_number = _extract_identifier_value(identifiers[0])
    
    # Patient ID from subject reference
    subject = resource.get("subject", {})
    patient_id = _extract_patient_id(subject.get("reference", ""))
    
    # Patient name from included Patient resource
    patient_name = "Unknown"
    if patient_resource:
        names = patient_resource.get("name", [])
        if names:
            name = names[0]
            given = " ".join(name.get("given", []))
            family = name.get("family", "")
            patient_name = f"{given} {family}".strip()
    
    # Modality from code.coding[0].code
    code = resource.get("code", {})
    codings = code.get("coding", [])
    if not codings:
        raise FHIRError("ServiceRequest.code must have at least one coding entry")
    modality = codings[0].get("code", "")
    if not modality:
        raise FHIRError("ServiceRequest.code.coding[0].code (modality) is required")
    
    # Procedure description from code.coding[0].display
    procedure_description = codings[0].get("display")
    
    # Scheduled procedure step start date/time from occurrenceDateTime
    occurrence = resource.get("occurrenceDateTime")
    if not occurrence:
        raise FHIRError("ServiceRequest.occurrenceDateTime is required")
    # Parse ISO datetime: 2026-10-16T09:00:00+07:00 → date + time
    dt = None
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(occurrence, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        scheduled_date = _format_date(occurrence)
        scheduled_time = None
    else:
        scheduled_date = dt.strftime("%Y%m%d")
        scheduled_time = dt.strftime("%H%M%S")
    
    # Referring physician name from requester.display
    requester = resource.get("requester", {})
    referring_physician = requester.get("display")
    
    # Extract source_id from ServiceRequest.id
    source_id = resource.get("id", str(uuid.uuid4()))
    
    return WorklistItem(
        source_id=source_id,
        accession_number=accession_number,
        patient_id=patient_id,
        patient_name=patient_name,
        scheduled_procedure_step_start_date=scheduled_date,
        scheduled_procedure_step_start_time=scheduled_time,
        modality=modality,
        procedure_description=procedure_description,
        referring_physician_name=referring_physician,
        source="fhir",
        status=WorklistStatus.PENDING,
    )


def _parse_imaging_study(resource: dict) -> WorklistItem:
    """Parse a FHIR R4 ImagingStudy resource."""
    
    # Accession number from identifier
    identifiers = resource.get("identifier", [])
    if not identifiers:
        raise FHIRError("ImagingStudy must have at least one identifier for accession_number")
    accession_number = _extract_identifier_value(identifiers[0])
    
    # Patient ID from subject reference
    subject = resource.get("subject", {})
    patient_id = _extract_patient_id(subject.get("reference", ""))
    
    # Patient name - ImagingStudy doesn't include Patient resource directly
    # Try to get from contained resources, otherwise use placeholder
    patient_name = "Unknown"
    contained = resource.get("contained", [])
    for res in contained:
        if res.get("resourceType") == "Patient":
            names = res.get("name", [])
            if names:
                name = names[0]
                given = " ".join(name.get("given", []))
                family = name.get("family", "")
                patient_name = f"{given} {family}".strip()
            break
    
    # Modality from modality[0].code
    modalities = resource.get("modality", [])
    if not modalities:
        raise FHIRError("ImagingStudy must have at least one modality entry")
    modality = modalities[0].get("code", "")
    if not modality:
        raise FHIRError("ImagingStudy.modality[0].code is required")
    
    # Scheduled procedure step start date from started or startDate
    started = resource.get("started")
    if started:
        scheduled_date = _format_date(started)
    else:
        # Fallback to today if not provided
        scheduled_date = datetime.now().strftime("%Y%m%d")
    
    # Study description
    study_description = resource.get("description")
    
    # Study instance UID from study UID
    study_uid = resource.get("uid")
    
    # Extract source_id
    source_id = resource.get("id", str(uuid.uuid4()))
    
    return WorklistItem(
        source_id=source_id,
        accession_number=accession_number,
        study_instance_uid=study_uid,
        patient_id=patient_id,
        patient_name=patient_name,
        scheduled_procedure_step_start_date=scheduled_date,
        modality=modality,
        study_description=study_description,
        source="fhir",
        status=WorklistStatus.PENDING,
    )


def _find_patient_in_bundle(entries: list) -> dict | None:
    """Find Patient resource in Bundle entries."""
    for entry in entries:
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            return resource
    return None


def map_fhir_to_worklist(data: dict) -> WorklistItem:
    """
    Map FHIR R4 JSON data to Lumi DICOM WorklistItem.
    
    Supports:
    - ServiceRequest (single resource)
    - ImagingStudy (single resource)
    - Bundle (with ServiceRequest/ImagingStudy + included Patient)
    
    Args:
        data: FHIR R4 JSON dictionary
        
    Returns:
        WorklistItem: Mapped worklist item
        
    Raises:
        FHIRError: If required fields are missing or data is invalid
        ValidationError: If WorklistItem validation fails
    """
    if not data:
        raise FHIRError("Input data is required")
    
    resource_type = data.get("resourceType")
    
    if not resource_type:
        raise FHIRError("Missing 'resourceType' field in FHIR data")
    
    if resource_type == "ServiceRequest":
        patient = None
        if "contained" in data:
            for res in data["contained"]:
                if res.get("resourceType") == "Patient":
                    patient = res
                    break
        return _parse_service_request(data, patient)
    
    elif resource_type == "ImagingStudy":
        return _parse_imaging_study(data)
    
    elif resource_type == "Bundle":
        entries = data.get("entry", [])
        if not entries:
            raise FHIRError("Bundle must contain at least one entry")
        
        # Find Patient resource first
        patient = _find_patient_in_bundle(entries)
        
        # Find ServiceRequest or ImagingStudy
        for entry in entries:
            resource = entry.get("resource", {})
            rt = resource.get("resourceType")
            if rt == "ServiceRequest":
                return _parse_service_request(resource, patient)
            elif rt == "ImagingStudy":
                return _parse_imaging_study(resource)
        
        raise FHIRError("Bundle must contain a ServiceRequest or ImagingStudy resource")
    
    else:
        raise FHIRError(f"Unsupported FHIR resourceType: {resource_type}. "
                       f"Supported: ServiceRequest, ImagingStudy, Bundle")

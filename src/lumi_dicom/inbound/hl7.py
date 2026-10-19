"""
HL7 v2 ORM^O01 Inbound Parser for Lumi DICOM Orchestrator.

Parses HL7 v2 pipe-delimited ORM^O01 (Order Entry) messages and maps them
to the WorklistItem model.

Supported segments: MSH, PID, ORC, OBR, PV1.
Handles both \\r and \\n segment delimiters and common escape sequences.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import ClassVar

from lumi_dicom.models.worklist import WorklistItem

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Map common DICOM modality codes to OBR.4 / OBR.7 description keywords
_MODALITY_KEYWORDS: dict[str, str] = {
    "CR": "DX",
    "CT": "CT",
    "MR": "MR",
    "NM": "NM",
    "US": "US",
    "XA": "XA",
    "DX": "DX",
    "MG": "MG",
    "PT": "PT",
    "RF": "RF",
    "OT": "OT",
}

# Modality fallback mapping from common OBR.4 text patterns
_MODALITY_FROM_TEXT: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(CT|CAT\s*SCAN|COMPUTED\s*TOMOGRAPHY)\b", re.IGNORECASE), "CT"),
    (re.compile(r"\b(MR|MRI|MAGNETIC\s*RESONANCE)\b", re.IGNORECASE), "MR"),
    (re.compile(r"\b(US|ULTRASOUND|SONOGR)\b", re.IGNORECASE), "US"),
    (re.compile(r"\b(NM|NUCLEAR\s*MEDICINE|PET)\b", re.IGNORECASE), "NM"),
    (re.compile(r"\b(XR|X-?RAY|RADIOGRAPH|FLUORO)\b", re.IGNORECASE), "DX"),
    (re.compile(r"\b(MG|MAMMOGR)\b", re.IGNORECASE), "MG"),
    (re.compile(r"\b(PT|PET)\b", re.IGNORECASE), "PT"),
    (re.compile(r"\b(DX|DIGITAL\s*RADIOGRAPHY|CR)\b", re.IGNORECASE), "DX"),
    (re.compile(r"\b(XA|ANGIOGR)\b", re.IGNORECASE), "XA"),
    (re.compile(r"\b(RF|FLUOROSCOPY)\b", re.IGNORECASE), "RF"),
    (re.compile(r"\b(OT|OTHER)\b", re.IGNORECASE), "OT"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_segments(raw: str) -> list[str]:
    """Split raw HL7 message into segment strings, handling both delimiters."""
    if not raw:
        return []
    # Normalise: replace both \r\n and \n with \r, then split on \r
    normalised = raw.replace("\r\n", "\r").replace("\n", "\r")
    segments = [seg.strip() for seg in normalised.split("\r") if seg.strip()]
    return segments


def _split_fields(segment: str) -> list[str]:
    """Split a segment into individual fields on the pipe delimiter."""
    if not segment:
        return []
    parts = segment.split("|")
    return parts


def _split_components(field: str) -> list[str]:
    """Split a field into components on the ^ delimiter."""
    if not field:
        return []
    return field.split("^")


def _unescape(value: str) -> str:
    """Decode HL7 escape sequences in a single value string."""
    if not value:
        return ""
    # \.br\  -> newline (also \E\ is sometimes used)
    result = value.replace("\\.br\\", "\n").replace("\\.BR\\", "\n")
    # \E\ -> escape character (leave as-is, or strip)
    result = re.sub(r"\\E\\", "", result)
    # \F\ -> field separator
    result = re.sub(r"\\F\\", "|", result)
    # \S\ -> component separator
    result = re.sub(r"\\S\\", "^", result)
    # \T\ -> sub-component separator
    result = re.sub(r"\\T\\", "&", result)
    # \R\ -> repetition separator
    result = re.sub(r"\\R\\", "~", result)
    # \Xdd..\ -> hex-encoded bytes (best-effort: decode as latin-1)
    result = re.sub(
        r"\\X([0-9A-Fa-f]{2})",
        lambda m: bytes([int(m.group(1), 16)]).decode("latin-1", errors="replace"),
        result,
    )
    # \Zdd..\ -> locally-defined escape (strip the wrapper)
    result = re.sub(r"\\Z[0-9A-Fa-f]{2}(?:[0-9A-Fa-f]{2})*\\", "", result)
    return result


def _format_patient_name(raw: str) -> str:
    """Normalise an HL7 XPN (extended person name) into a readable string.

    HL7 XPN format: Family^Given^Middle^Prefix^Suffix
    Returns "Given Middle Family" for readability.
    """
    if not raw:
        return ""
    comps = _split_components(raw)
    if len(comps) == 0:
        return ""
    # If the name is a single component with no carets, return as-is
    if len(comps) == 1:
        return _unescape(comps[0])
    family = _unescape(comps[0]) if len(comps) > 0 else ""
    given = _unescape(comps[1]) if len(comps) > 1 else ""
    middle = _unescape(comps[2]) if len(comps) > 2 else ""
    prefix = _unescape(comps[3]) if len(comps) > 3 else ""
    suffix = _unescape(comps[4]) if len(comps) > 4 else ""
    # Build "Given Middle Family" style
    parts = [p for p in (given, middle, family) if p]
    name = " ".join(parts)
    if prefix:
        name = f"{prefix} {name}"
    if suffix:
        name = f"{name}, {suffix}"
    return name.strip()


def _format_physician_name(raw: str) -> str:
    """Normalise an HL7 XCN/XPN (extended composite ID number and name) into a string."""
    if not raw:
        return ""
    comps = _split_components(raw)
    if len(comps) == 0:
        return ""
    # XCN: ID^Family^Given^Middle^Suffix^Prefix^Degree...
    # XPN: Family^Given^Middle^Prefix^Suffix
    if len(comps) == 1:
        return _unescape(comps[0])
    family = _unescape(comps[0]) if len(comps) > 0 else ""
    given = _unescape(comps[1]) if len(comps) > 1 else ""
    middle = _unescape(comps[2]) if len(comps) > 2 else ""
    prefix = _unescape(comps[3]) if len(comps) > 3 else ""
    suffix = _unescape(comps[4]) if len(comps) > 4 else ""
    # Name part
    name_parts = [p for p in (given, middle, family) if p]
    name = " ".join(name_parts)
    if prefix:
        name = f"{prefix} {name}"
    if suffix:
        name = f"{name}, {suffix}"
    return name.strip()


def _parse_hl7_date(value: str) -> date | None:
    """Parse an HL7 date (YYYYMMDD or YYYYMMDDHHMMSS) into a date."""
    if not value:
        return None
    # Try YYYYMMDD
    if len(value) >= 8:
        try:
            year = int(value[0:4])
            month = int(value[4:6])
            day = int(value[6:8])
            return date(year, month, day)
        except (ValueError, IndexError):
            pass
    # Try YYMMDD
    if len(value) >= 6:
        try:
            year = int(value[0:2])
            year = 2000 + year if year < 50 else 1900 + year
            month = int(value[2:4])
            day = int(value[4:6])
            return date(year, month, day)
        except (ValueError, IndexError):
            pass
    return None


def _parse_hl7_datetime(value: str) -> datetime | None:
    """Parse an HL7 datetime (YYYYMMDDHHMMSS or YYYYMMDD) into a datetime."""
    if not value:
        return None
    # Try YYYYMMDDHHMMSS
    if len(value) >= 14:
        try:
            year = int(value[0:4])
            month = int(value[4:6])
            day = int(value[6:8])
            hour = int(value[8:10])
            minute = int(value[10:12])
            second = int(value[12:14])
            return datetime(year, month, day, hour, minute, second)
        except (ValueError, IndexError):
            pass
    # Try YYYYMMDDHHMM
    if len(value) >= 12:
        try:
            year = int(value[0:4])
            month = int(value[4:6])
            day = int(value[6:8])
            hour = int(value[8:10])
            minute = int(value[10:12])
            return datetime(year, month, day, hour, minute, 0)
        except (ValueError, IndexError):
            pass
    # Try YYYYMMDD
    if len(value) >= 8:
        try:
            year = int(value[0:4])
            month = int(value[4:6])
            day = int(value[6:8])
            return datetime(year, month, day)
        except (ValueError, IndexError):
            pass
    return None


def _extract_modality(obr4: str = "", obr7: str = "") -> str:
    """Derive DICOM modality from OBR.4 (universal service ID) or OBR.7 (observation datetime)."""
    # OBR.4 is a CWE: code^text^coding-system^...
    comps = _split_components(obr4)
    code = ""
    text = ""
    if len(comps) >= 1:
        code = comps[0].strip().upper()
    if len(comps) >= 2:
        text = comps[1].strip()
    # Direct code lookup
    if code and code in _MODALITY_KEYWORDS:
        return _MODALITY_KEYWORDS[code]
    # Try to find a modality keyword anywhere in the code+text
    combined = f"{code} {text}".strip()
    for pattern, modality in _MODALITY_FROM_TEXT:
        if pattern.search(combined):
            return modality
    # OBR.7 is just a datetime; no modality info
    # Fallback: try to find modality in the whole OBR.4 text
    for pattern, modality in _MODALITY_FROM_TEXT:
        if pattern.search(obr4):
            return modality
    return "OT"


# ---------------------------------------------------------------------------
# HL7 Parser Class
# ---------------------------------------------------------------------------

class HL7Parser:
    """Parser for HL7 v2 ORM^O01 (Order Entry) messages.

    Usage::

        parser = HL7Parser()
        item = parser.parse(raw_message)
    """

    # HL7 segment names we care about
    SUPPORTED_SEGMENTS: ClassVar[set[str]] = {"MSH", "PID", "ORC", "OBR", "PV1"}

    def __init__(self) -> None:
        self._segments: dict[str, list[list[str]]] = {}
        self._raw: str = ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, raw: str) -> WorklistItem:
        """Parse a raw HL7 v2 message string into a WorklistItem.

        Parameters
        ----------
        raw : str
            The raw HL7 message text.

        Returns
        -------
        WorklistItem
            The populated worklist item.

        Raises
        ------
        ValueError
            If the message is empty or cannot be parsed.
        """
        if not raw or not raw.strip():
            raise ValueError("Empty HL7 message")

        self._raw = raw
        self._segments = self._segment_message(raw)

        return self._build_worklist_item()

    # ------------------------------------------------------------------
    # Internal parsing
    # ------------------------------------------------------------------

    def _segment_message(self, raw: str) -> dict[str, list[list[str]]]:
        """Split raw message into segments, grouped by segment type."""
        segments: dict[str, list[list[str]]] = {}
        segment_strings = _split_segments(raw)
        for seg_str in segment_strings:
            parts = _split_fields(seg_str)
            if not parts:
                continue
            seg_type = parts[0].upper()
            # Store all fields (including segment type as parts[0])
            segments.setdefault(seg_type, []).append(parts)
        return segments

    def _get_field(self, seg_type: str, field_index: int, occurrence: int = 0) -> str:
        """Get a specific field from a segment.

        Parameters
        ----------
        seg_type : str
            The segment type (e.g., "PID", "OBR").
        field_index : int
            The 0-based field index (0 = segment type, 1 = first field after type).
        occurrence : int
            Which occurrence of the segment to use (0 = first).

        Returns
        -------
        str
            The field value, or "" if not found.
        """
        seg_list = self._segments.get(seg_type, [])
        if occurrence >= len(seg_list):
            return ""
        fields = seg_list[occurrence]
        if field_index >= len(fields):
            return ""
        return fields[field_index]

    def _get_field_safe(self, seg_type: str, field_index: int, occurrence: int = 0) -> str:
        """Same as _get_field but returns empty string on any error."""
        try:
            return self._get_field(seg_type, field_index, occurrence)
        except Exception:  # noqa: BLE001 — accessor must never raise on bad input
            return ""

    # ------------------------------------------------------------------
    # Field extractors (using HL7 v2 field numbering)
    # ------------------------------------------------------------------

    def _pid_patient_id(self) -> str:
        """PID.3 - Patient ID (list of CX composite IDs)."""
        raw = self._get_field_safe("PID", 3)
        if not raw:
            return ""
        # PID.3 is a list of CX IDs separated by ~
        ids = raw.split("~")
        if ids:
            first = ids[0]
            comps = _split_components(first)
            # CX.1 = ID number
            if comps:
                return _unescape(comps[0])
        return ""

    def _pid_patient_name(self) -> str:
        """PID.5 - Patient Name (XPN)."""
        raw = self._get_field_safe("PID", 5)
        return _format_patient_name(raw)

    def _pid_birth_date(self) -> date | None:
        """PID.7 - Patient Birth Date (DT)."""
        raw = self._get_field_safe("PID", 7)
        return _parse_hl7_date(raw)

    def _pid_sex(self) -> str:
        """PID.8 - Patient Sex (IS)."""
        raw = self._get_field_safe("PID", 8)
        if raw:
            return _unescape(raw).upper()
        return ""

    def _pid_patient_weight(self) -> str | None:
        """PID.10 - Patient Weight (NM)."""
        raw = self._get_field_safe("PID", 10)
        return _unescape(raw) if raw else None

    def _orc_order_control(self) -> str:
        """ORC.1 - Order Control (ID)."""
        raw = self._get_field_safe("ORC", 1)
        return _unescape(raw) if raw else ""

    def _orc_placer_order_number(self) -> str:
        """ORC.2 - Placer Order Number (EI)."""
        raw = self._get_field_safe("ORC", 2)
        if not raw:
            return ""
        comps = _split_components(raw)
        if comps:
            return _unescape(comps[0])
        return ""

    def _orc_filler_order_number(self) -> str:
        """ORC.3 - Filler Order Number (EI)."""
        raw = self._get_field_safe("ORC", 3)
        if not raw:
            return ""
        comps = _split_components(raw)
        if comps:
            return _unescape(comps[0])
        return ""

    def _obr_accession_number(self) -> str:
        """OBR.2 (Placer) or OBR.3 (Filler) - Accession Number."""
        # OBR.2 = Placer order number
        raw2 = self._get_field_safe("OBR", 2)
        if raw2:
            comps = _split_components(raw2)
            if comps:
                accession = _unescape(comps[0])
                if accession:
                    return accession
        # OBR.3 = Filler order number
        raw3 = self._get_field_safe("OBR", 3)
        if raw3:
            comps = _split_components(raw3)
            if comps:
                accession = _unescape(comps[0])
                if accession:
                    return accession
        # Fallback to ORC.2 or ORC.3
        return self._orc_placer_order_number() or self._orc_filler_order_number()

    def _obr_universal_service_id(self) -> str:
        """OBR.4 - Universal Service ID (CWE)."""
        raw = self._get_field_safe("OBR", 4)
        return _unescape(raw) if raw else ""

    def _obr_study_description(self) -> str:
        """OBR.4.2 - Study Description (text component of CWE)."""
        raw = self._get_field_safe("OBR", 4)
        if not raw:
            return ""
        comps = _split_components(raw)
        if len(comps) >= 2:
            return _unescape(comps[1])
        if len(comps) == 1:
            return _unescape(comps[0])
        return ""

    def _obr_observation_datetime(self) -> datetime | None:
        """OBR.7 - Observation Date/Time (DTM)."""
        raw = self._get_field_safe("OBR", 7)
        return _parse_hl7_datetime(raw)

    def _obr_referring_physician(self) -> str:
        """OBR.16 - Referring Physician (XCN)."""
        raw = self._get_field_safe("OBR", 16)
        return _format_physician_name(raw)

    def _obr_scheduled_procedure_step_start_date(self) -> date | None:
        """OBR.27 - Scheduled Procedure Step Start Date/Time."""
        raw = self._get_field_safe("OBR", 27)
        if not raw:
            return None
        # OBR.27 is a TQ (Timing/Quantity) with components:
        # quantity^interval^duration^start^end^...
        comps = _split_components(raw)
        # The start date/time is in OBR.27.4 (4th component of TQ)
        if len(comps) >= 4:
            start = _unescape(comps[3])
            dt = _parse_hl7_datetime(start)
            if dt:
                return dt.date()
            d = _parse_hl7_date(start)
            if d:
                return d
        # Fallback: try OBR.7
        dt = self._obr_observation_datetime()
        if dt:
            return dt.date()
        return None

    def _pv1_patient_class(self) -> str:
        """PV1.2 - Patient Class (IS)."""
        raw = self._get_field_safe("PV1", 2)
        return _unescape(raw) if raw else ""

    def _pv1_assigned_patient_location(self) -> str:
        """PV1.3 - Assigned Patient Location (PL)."""
        raw = self._get_field_safe("PV1", 3)
        return _unescape(raw) if raw else ""

    def _pv1_attending_doctor(self) -> str:
        """PV1.7 - Attending Doctor (XCN)."""
        raw = self._get_field_safe("PV1", 7)
        return _format_physician_name(raw)

    def _pv1_visit_number(self) -> str:
        """PV1.19 - Visit Number (CX)."""
        raw = self._get_field_safe("PV1", 19)
        if not raw:
            return ""
        comps = _split_components(raw)
        if comps:
            return _unescape(comps[0])
        return ""

    def _extract_modality(self) -> str:
        """Derive modality from OBR.4."""
        obr4 = self._get_field_safe("OBR", 4)
        obr7 = self._get_field_safe("OBR", 7)
        return _extract_modality(obr4, obr7)

    def _extract_source_id(self) -> str:
        """Extract source ID from MSH.3 (sending application) or MSH.4 (sending facility)."""
        msh3 = self._get_field_safe("MSH", 3)
        msh4 = self._get_field_safe("MSH", 4)
        # Return sending facility as source_id, fallback to sending application
        if msh4:
            return _unescape(msh4)
        if msh3:
            return _unescape(msh3)
        return "HL7"

    def _extract_study_instance_uid(self) -> str:
        """Try to find Study Instance UID in OBR.31 (diagnostic service ID) or OBR.32."""
        # OBR.31 is a CWE list; sometimes contains study UID
        obr31 = self._get_field_safe("OBR", 31)
        if obr31:
            comps = _split_components(obr31)
            for comp in comps:
                val = _unescape(comp)
                # Study UIDs are long numeric strings with dots
                if len(val) > 20 and re.match(r"^\d+(\.\d+)+$", val):
                    return val
        # Try OBR.32 (principal result interpreter)
        obr32 = self._get_field_safe("OBR", 32)
        if obr32:
            comps = _split_components(obr32)
            for comp in comps:
                val = _unescape(comp)
                if len(val) > 20 and re.match(r"^\d+(\.\d+)+$", val):
                    return val
        return ""

    def _extract_requested_procedure_id(self) -> str:
        """OBR.4.1 - Requested Procedure ID (code component of CWE)."""
        raw = self._get_field_safe("OBR", 4)
        if not raw:
            return ""
        comps = _split_components(raw)
        if comps:
            return _unescape(comps[0])
        return ""

    def _extract_scheduled_station_aetitle(self) -> str:
        """Try to find scheduled station AE title from OBR or PV1."""
        # OBR.18 is Placer Field 2 (sometimes contains station info)
        obr18 = self._get_field_safe("OBR", 18)
        if obr18:
            val = _unescape(obr18)
            if re.match(r"^[A-Za-z0-9_.\-]+$", val):
                return val
        # OBR.20 is Filler Field 2
        obr20 = self._get_field_safe("OBR", 20)
        if obr20:
            val = _unescape(obr20)
            if re.match(r"^[A-Za-z0-9_.\-]+$", val):
                return val
        return ""

    def _extract_procedure_code(self) -> str:
        """OBR.4.1 - Procedure Code (first component of CWE)."""
        return self._extract_requested_procedure_id()

    def _extract_procedure_description(self) -> str:
        """OBR.4.2 - Procedure Description (second component of CWE)."""
        return self._obr_study_description()

    def _extract_procedure_code_sequence(self) -> str:
        """OBR.4 - full CWE as procedure code sequence."""
        raw = self._get_field_safe("OBR", 4)
        return _unescape(raw) if raw else ""

    def _extract_study_id(self) -> str:
        """OBR.4.1 or ORC.2 - Study ID."""
        obr4 = self._get_field_safe("OBR", 4)
        if obr4:
            comps = _split_components(obr4)
            if comps:
                val = _unescape(comps[0])
                if val:
                    return val
        return self._orc_placer_order_number()

    def _extract_status(self) -> str:
        """ORC.5 - Order Status (ID)."""
        raw = self._get_field_safe("ORC", 5)
        if raw:
            return _unescape(raw)
        return "SC"

    def _extract_external_id(self) -> str:
        """OBR.3 or ORC.3 - External ID (filler order number)."""
        return self._orc_filler_order_number()

    # ------------------------------------------------------------------
    # Build WorklistItem
    # ------------------------------------------------------------------

    # HL7 ORC.5 Order Status → Lumi DICOM WorklistStatus
    _HL7_STATUS_MAP: ClassVar[dict[str, str]] = {
        "SC": "pending",     # Scheduled → pending
        "CM": "completed",    # Completed
        "CA": "cancelled",   # Cancelled
        "RP": "pending",     # Requested/pending
        "IP": "in_progress", # In Progress
        "ER": "pending",     # Error (treat as pending)
    }

    def _build_worklist_item(self) -> WorklistItem:
        """Construct a WorklistItem from parsed segments.

        Converts date/datetime objects from HL7 fields into the string
        formats expected by WorklistItem, and maps HL7 order status codes
        to Lumi DICOM status values.
        """
        from datetime import date as date_cls
        from datetime import datetime as datetime_cls

        # ── Birth date: date → YYYYMMDD string ──────────────────────────
        birth_date = self._pid_birth_date()
        birth_date_str: str | None = None
        if isinstance(birth_date, date_cls):
            birth_date_str = birth_date.strftime("%Y%m%d")

        # ── Scheduled date: date → YYYYMMDD string ───────────────────────
        sched_date = self._obr_scheduled_procedure_step_start_date()
        sched_date_str: str | None = None
        if isinstance(sched_date, date_cls):
            sched_date_str = sched_date.strftime("%Y%m%d")
        # Fallback: use OBR.7 date part if OBR.27 missing
        if not sched_date_str:
            obs_dt = self._obr_observation_datetime()
            if isinstance(obs_dt, (datetime_cls, date_cls)):
                sched_date_str = obs_dt.strftime("%Y%m%d")

        # ── Scheduled time: datetime → HHMMSS string ─────────────────────
        sched_time_str: str | None = None
        obs_dt = self._obr_observation_datetime()
        if isinstance(obs_dt, (datetime_cls, date_cls)):
            sched_time_str = obs_dt.strftime("%H%M%S")

        # ── Status: HL7 ORC.5 → Lumi DICOM status ───────────────────────
        raw_status = self._extract_status()
        status = self._HL7_STATUS_MAP.get(raw_status.upper(), "pending")

        return WorklistItem(
            source_id=self._extract_source_id(),
            accession_number=self._obr_accession_number(),
            study_instance_uid=self._extract_study_instance_uid(),
            requested_procedure_id=self._extract_requested_procedure_id(),
            patient_id=self._pid_patient_id(),
            patient_name=self._pid_patient_name(),
            patient_birth_date=birth_date_str,
            patient_sex=self._pid_sex() or None,
            patient_weight=self._pid_patient_weight(),
            scheduled_procedure_step_start_date=sched_date_str or "",
            scheduled_procedure_step_start_time=sched_time_str,
            modality=self._extract_modality(),
            scheduled_station_aetitle=self._extract_scheduled_station_aetitle() or None,
            procedure_code=self._extract_procedure_code(),
            procedure_description=self._extract_procedure_description(),
            procedure_code_sequence=self._extract_procedure_code_sequence(),
            referring_physician_name=self._obr_referring_physician(),
            study_description=self._obr_study_description(),
            study_id=self._extract_study_id(),
            status=status,
            source="HL7",
            external_id=self._extract_external_id(),
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def parse_hl7_message(raw: str) -> WorklistItem:
    """Parse a raw HL7 v2 ORM^O01 message into a WorklistItem.

    This is a convenience wrapper around :class:`HL7Parser`.

    Parameters
    ----------
    raw : str
        The raw HL7 message text.

    Returns
    -------
    WorklistItem
        The populated worklist item.

    Examples
    --------
    >>> raw = "MSH|^~\\\\&|HIS|FAC|RIS|FAC|20240101120000||ORM^O01|MSG001|P|2.3|..."
    >>> item = parse_hl7_message(raw)
    >>> print(item.patient_name)
    """
    parser = HL7Parser()
    return parser.parse(raw)

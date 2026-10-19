"""
Lumi DICOM — MWL SCP (Service Class Provider)
Copyright © 2026 Lumi DICOM. All rights reserved.

DICOM Modality Worklist SCP — menjawab C-FIND dari modalitas.
Menggunakan pynetdicom untuk DICOM networking.
"""

import asyncio
import logging
import pathlib
import ssl

from pydicom.dataset import Dataset
from pynetdicom import AE, evt
from pynetdicom.sop_class import ModalityWorklistInformationFind, Verification

from lumi_dicom.db.manager import DatabaseManager
from lumi_dicom.models.worklist import WorklistItem

logger = logging.getLogger("lumi-dicom")


class MWLSCP:
    """
    Lumi DICOM MWL SCP.

    Menjawab C-FIND dari modalitas dengan worklist items dari SQLite.
    Filter: PatientID, PatientName, AccessionNumber, Modality,
            ScheduledProcedureStepStartDate, ScheduledStationAETitle.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        ae_title: str = "LUMI_DICOM",
        host: str = "0.0.0.0",
        port: int = 11112,
        bind: str = "127.0.0.1",
        allowed_aetitles: list[str] | None = None,
        max_associations: int = 20,
        max_results: int = 1024,
        tls_cert: str = "",
        tls_key: str = "",
    ):
        self.db = db_manager
        self.ae_title = ae_title
        self.host = host
        self.port = port
        self.bind = bind
        self.allowed_aetitles = allowed_aetitles or []
        self.max_associations = max_associations
        self.max_results = max_results
        self.tls_cert = tls_cert
        self.tls_key = tls_key

        self._ae: AE | None = None
        self._server = None
        self._ssl_context: ssl.SSLContext | None = None

    def _create_ssl_context(self) -> ssl.SSLContext | None:
        """
        Create SSL context for TLS encryption.

        Returns None if TLS is disabled or cert/key are not provided.
        Raises FileNotFoundError if cert or key files do not exist.
        """
        if not self.tls_cert or not self.tls_key:
            return None

        cert_path = pathlib.Path(self.tls_cert)
        key_path = pathlib.Path(self.tls_key)

        if not cert_path.is_file():
            raise FileNotFoundError(
                f"Lumi DICOM MWL SCP: TLS cert file not found: {self.tls_cert}"
            )
        if not key_path.is_file():
            raise FileNotFoundError(
                f"Lumi DICOM MWL SCP: TLS key file not found: {self.tls_key}"
            )

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile=str(cert_path),
            keyfile=str(key_path),
        )
        return context

    async def serve(self):
        """Start the Lumi DICOM MWL SCP server."""
        self._ae = AE(ae_title=self.ae_title)

        # Add SOP classes: Verification (C-ECHO) + MWL (C-FIND)
        self._ae.add_supported_context(Verification)
        self._ae.add_supported_context(ModalityWorklistInformationFind)

        # TLS setup
        self._ssl_context = self._create_ssl_context()

        if self._ssl_context is not None:
            logger.info("Lumi DICOM MWL SCP: TLS enabled (cert=%s)", self.tls_cert)
        else:
            logger.info("Lumi DICOM MWL SCP: TLS disabled — using plain DICOM")

        # Association handlers
        handlers = [
            (evt.EVT_C_FIND, self._handle_c_find),
            (evt.EVT_ESTABLISHED, self._handle_association_established),
            (evt.EVT_RELEASED, self._handle_association_released),
        ]

        logger.info(
            "Lumi DICOM MWL SCP listening on %s:%s (AE: %s)",
            self.bind, self.port, self.ae_title,
        )

        self._server = self._ae.start_server(
            (self.bind, self.port),
            block=False,
            evt_handlers=handlers,
            ssl_context=self._ssl_context,
        )

        # Keep alive
        while True:
            await asyncio.sleep(1)

    # ── Association Handlers ────────────────────────────────────────────────

    def _handle_association_established(self, event):
        """Callback when association is established."""
        client_ae = event.assoc.requestor.ae_title
        logger.info("Lumi DICOM MWL SCP: association from %s", client_ae)

        # Allow-list check
        if self.allowed_aetitles and client_ae not in self.allowed_aetitles:
            logger.warning(
                "Lumi DICOM MWL SCP: rejecting %s — not in allow-list",
                client_ae,
            )
            event.assoc.abort()

    def _handle_association_released(self, event):
        """Callback when association is released."""
        logger.debug("Lumi DICOM MWL SCP: association released")

    # ── C-FIND Handler ──────────────────────────────────────────────────────

    def _handle_c_find(self, event):
        """
        Handle C-FIND request dari modalitas.

        Yields (status, dataset) pairs. Status 0xFF00 = pending match,
        0x0000 = success (no more matches), 0xCxxx = error.
        """
        identifier: Dataset = event.identifier

        # Build SQL query from identifier filters
        sql, params = self._build_query(identifier)

        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        # Cap results
        if len(rows) > self.max_results:
            logger.warning(
                "Lumi DICOM MWL SCP: result set %d exceeds cap %d",
                len(rows), self.max_results,
            )
            yield (0xC000, None)  # Unable to Process
            return

        # Yield matches
        for row in rows:
            item = WorklistItem.from_row(row)
            ds = self._to_dicom_dataset(item)
            yield (0xFF00, ds)

        # Success terminator
        yield (0x0000, None)

    @staticmethod
    def _is_blank(value) -> bool:
        """Return True for values that mean 'no filter' in a DICOM query.

        In DICOM, an empty string or a single ``*`` wildcard in a query
        attribute means "match any" — it must NOT become a SQL equality
        filter, or the modality gets zero results back.
        """
        if value is None:
            return True
        text = str(value).strip()
        return text == "" or text == "*"

    def _build_query(self, identifier: Dataset) -> tuple[str, list]:
        """Build SQL query from DICOM C-FIND identifier.

        Empty or wildcard-valued attributes are skipped (treated as
        wildcards), which is what DICOM modalities expect.
        """
        conditions = ["status != 'cancelled'"]
        params: list = []

        # PatientID (0010,0020)
        if hasattr(identifier, "PatientID") and not self._is_blank(identifier.PatientID):
            conditions.append("patient_id = ?")
            params.append(str(identifier.PatientID))

        # PatientName (0010,0010) — supports leading/trailing wildcards
        if hasattr(identifier, "PatientName") and not self._is_blank(identifier.PatientName):
            raw_name = str(identifier.PatientName).strip()
            name_pattern = f"%{raw_name}%"
            if raw_name.startswith("*") or raw_name.endswith("*"):
                name_pattern = f"%{raw_name.strip('*')}%"
            conditions.append("patient_name LIKE ?")
            params.append(name_pattern)

        # AccessionNumber (0008,0050)
        if hasattr(identifier, "AccessionNumber") and not self._is_blank(identifier.AccessionNumber):
            conditions.append("accession_number = ?")
            params.append(str(identifier.AccessionNumber))

        # Modality (0008,0060)
        if hasattr(identifier, "Modality") and not self._is_blank(identifier.Modality):
            conditions.append("modality = ?")
            params.append(str(identifier.Modality))

        # ScheduledProcedureStepStartDate (0040,0002)
        if hasattr(identifier, "ScheduledProcedureStepStartDate") and not self._is_blank(
            identifier.ScheduledProcedureStepStartDate
        ):
            date_val = str(identifier.ScheduledProcedureStepStartDate).strip()
            if "-" in date_val:
                # Range: YYYYMMDD-YYYYMMDD (either side may be open)
                parts = date_val.split("-", 1)
                low, high = parts[0].strip(), parts[1].strip()
                if low and high:
                    conditions.append("scheduled_procedure_step_start_date BETWEEN ? AND ?")
                    params.extend([low, high])
                elif low:
                    conditions.append("scheduled_procedure_step_start_date >= ?")
                    params.append(low)
                elif high:
                    conditions.append("scheduled_procedure_step_start_date <= ?")
                    params.append(high)
                # "-" alone is a degenerate range — no filter
            else:
                conditions.append("scheduled_procedure_step_start_date = ?")
                params.append(date_val)

        # ScheduledStationAETitle (0040,0001)
        if hasattr(identifier, "ScheduledStationAETitle") and not self._is_blank(
            identifier.ScheduledStationAETitle
        ):
            conditions.append("scheduled_station_aetitle = ?")
            params.append(str(identifier.ScheduledStationAETitle))

        sql = f"SELECT * FROM worklist_items WHERE {' AND '.join(conditions)} "
        sql += "ORDER BY scheduled_procedure_step_start_date DESC, "
        sql += "scheduled_procedure_step_start_time DESC"

        return sql, params

    def _to_dicom_dataset(self, item: WorklistItem) -> Dataset:
        """Convert WorklistItem to DICOM Dataset for MWL response."""
        ds = Dataset()

        # Patient
        ds.PatientID = item.patient_id
        ds.PatientName = item.patient_name
        if item.patient_birth_date:
            ds.PatientBirthDate = item.patient_birth_date
        if item.patient_sex:
            ds.PatientSex = item.patient_sex
        if item.patient_weight:
            ds.PatientWeight = item.patient_weight

        # Study / Accession
        ds.StudyInstanceUID = item.study_instance_uid or ""
        ds.AccessionNumber = item.accession_number
        if item.requested_procedure_id:
            ds.RequestedProcedureID = item.requested_procedure_id

        # Scheduled Procedure Step
        ds.ScheduledProcedureStepStartDate = item.scheduled_procedure_step_start_date
        if item.scheduled_procedure_step_start_time:
            ds.ScheduledProcedureStepStartTime = item.scheduled_procedure_step_start_time
        ds.Modality = item.modality
        if item.scheduled_station_aetitle:
            ds.ScheduledStationAETitle = item.scheduled_station_aetitle

        # Procedure
        if item.procedure_code or item.procedure_code_sequence:
            ds.ProcedureCodeSequence = self._build_code_sequence(item)
        if item.procedure_description:
            ds.StudyDescription = item.procedure_description

        # Physician
        if item.referring_physician_name:
            ds.ReferringPhysicianName = item.referring_physician_name

        return ds

    def _build_code_sequence(self, item: WorklistItem) -> list[Dataset]:
        """Build DICOM Code Sequence from procedure_code_sequence JSON."""
        import json
        try:
            codes = json.loads(item.procedure_code_sequence) if item.procedure_code_sequence else []
        except (json.JSONDecodeError, TypeError):
            codes = []

        if not codes and item.procedure_code:
            codes = [{
                "code_value": item.procedure_code,
                "coding_scheme_designator": "LUMI",
                "code_meaning": item.procedure_description or item.procedure_code,
            }]

        seq = []
        for c in codes:
            ds = Dataset()
            ds.CodeValue = c.get("code_value", "")
            ds.CodingSchemeDesignator = c.get("coding_scheme_designator", "")
            ds.CodeMeaning = c.get("code_meaning", "")
            seq.append(ds)

        return seq

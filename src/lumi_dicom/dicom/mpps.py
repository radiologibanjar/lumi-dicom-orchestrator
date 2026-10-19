"""
Lumi DICOM — MPPS SCP (Modality Performed Procedure Step)
Copyright © 2026 Lumi DICOM. All rights reserved.

MPPS SCP — menerima N-CREATE dan N-SET dari modalitas.
Opsional, aktifkan di config.
"""

import asyncio
import logging
import pathlib
import ssl

from pynetdicom import AE, evt
from pynetdicom.sop_class import (
    ModalityPerformedProcedureStep,
    ModalityPerformedProcedureStepRetrieve,
)

from lumi_dicom.db.manager import DatabaseManager

logger = logging.getLogger("lumi-dicom")


class MPPSSCP:
    """
    Lumi DICOM MPPS SCP.

    Menerima MPPS N-CREATE (mulai prosedur) dan N-SET (selesai prosedur)
    dari modalitas. Update status worklist item terkait.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        ae_title: str = "LUMI_MPPS",
        host: str = "0.0.0.0",
        port: int = 11113,
        bind: str = "127.0.0.1",
        max_associations: int = 10,
        tls_cert: str = "",
        tls_key: str = "",
    ):
        self.db = db_manager
        self.ae_title = ae_title
        self.host = host
        self.port = port
        self.bind = bind
        self.max_associations = max_associations
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
                f"Lumi DICOM MPPS SCP: TLS cert file not found: {self.tls_cert}"
            )
        if not key_path.is_file():
            raise FileNotFoundError(
                f"Lumi DICOM MPPS SCP: TLS key file not found: {self.tls_key}"
            )

        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile=str(cert_path),
            keyfile=str(key_path),
        )
        return context

    async def serve(self):
        """Start the Lumi DICOM MPPS SCP server."""
        self._ae = AE(ae_title=self.ae_title)

        # Add MPPS SOP classes
        self._ae.add_supported_context(ModalityPerformedProcedureStep)
        self._ae.add_supported_context(ModalityPerformedProcedureStepRetrieve)

        # TLS setup
        self._ssl_context = self._create_ssl_context()

        if self._ssl_context is not None:
            logger.info("Lumi DICOM MPPS SCP: TLS enabled (cert=%s)", self.tls_cert)
        else:
            logger.info("Lumi DICOM MPPS SCP: TLS disabled — using plain DICOM")

        handlers = [
            (evt.EVT_N_CREATE, self._handle_n_create),
            (evt.EVT_N_SET, self._handle_n_set),
        ]

        logger.info(
            "Lumi DICOM MPPS SCP listening on %s:%s (AE: %s)",
            self.bind, self.port, self.ae_title,
        )

        self._server = self._ae.start_server(
            (self.bind, self.port),
            block=False,
            evt_handlers=handlers,
            ssl_context=self._ssl_context,
        )

        while True:
            await asyncio.sleep(1)

    # ── N-CREATE Handler ────────────────────────────────────────────────────

    def _handle_n_create(self, event):
        """Handle N-CREATE — modalitas memulai prosedur."""
        # pynetdicom 2.x: event.dataset hanya untuk C-STORE;
        # N-CREATE memakai property `attribute_list`.
        ds = event.attribute_list
        logger.info(
            "Lumi DICOM MPPS N-CREATE: accession=%s modality=%s",
            getattr(ds, "AccessionNumber", "?"),
            getattr(ds, "Modality", "?"),
        )

        # Store MPPS event
        accession = getattr(ds, "AccessionNumber", "")
        with self.db.connect() as conn:
            # Find worklist item
            item = conn.execute(
                "SELECT id FROM worklist_items WHERE accession_number = ?",
                (accession,),
            ).fetchone()

            if item:
                conn.execute(
                    """
                    INSERT INTO mpps_events (
                        worklist_item_id, mpps_sop_instance_uid,
                        performed_station_ae_title, mpps_status
                    ) VALUES (?, ?, ?, 'IN PROGRESS')
                    """,
                    (
                        item["id"],
                        getattr(ds, "SOPInstanceUID", ""),
                        getattr(ds, "PerformedStationAETitle", ""),
                    ),
                )
                # Update worklist status → in_progress
                conn.execute(
                    "UPDATE worklist_items SET status = 'in_progress', "
                    "updated_at = datetime('now') WHERE id = ?",
                    (item["id"],),
                )
                conn.commit()

        return 0x0000, ds

    # ── N-SET Handler ───────────────────────────────────────────────────────

    def _handle_n_set(self, event):
        """Handle N-SET — modalitas menyelesaikan prosedur."""
        # pynetdicom 2.x: N-SET memakai property `modification_list`.
        ds = event.modification_list
        logger.info(
            "Lumi DICOM MPPS N-SET: accession=%s",
            getattr(ds, "AccessionNumber", "?"),
        )

        accession = getattr(ds, "AccessionNumber", "")
        with self.db.connect() as conn:
            item = conn.execute(
                "SELECT id FROM worklist_items WHERE accession_number = ?",
                (accession,),
            ).fetchone()

            if item:
                conn.execute(
                    "UPDATE mpps_events SET mpps_status = 'COMPLETED', "
                    "updated_at = datetime('now') "
                    "WHERE worklist_item_id = ?",
                    (item["id"],),
                )
                conn.execute(
                    "UPDATE worklist_items SET status = 'completed', "
                    "updated_at = datetime('now') WHERE id = ?",
                    (item["id"],),
                )
                conn.commit()

        return 0x0000, ds

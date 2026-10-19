"""
Lumi DICOM — Image Router Worker
Copyright © 2026 Lumi DICOM. All rights reserved.

Worker untuk routing DICOM images antar AE.
Opsional, aktifkan di config.
"""

import asyncio
import logging

from pydicom.dataset import Dataset
from pynetdicom import AE, evt
from pynetdicom.sop_class import (
    CTImageStorage,
    MRImageStorage,
    Verification,
)

from lumi_dicom.db.manager import DatabaseManager

logger = logging.getLogger("lumi-dicom")


class ImageRouter:
    """
    Lumi DICOM Image Router.

    Menerima C-STORE dari modalitas source, lalu forward ke destination AE.
    Queue-based dengan retry logic.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        source_ae: str = "LUMI_ROUTE",
        destinations: list[dict] | None = None,
        host: str = "0.0.0.0",
        port: int = 11114,
        bind: str = "127.0.0.1",
    ):
        self.db = db_manager
        self.source_ae = source_ae
        self.destinations = destinations or []
        self.host = host
        self.port = port
        self.bind = bind

        self._ae: AE | None = None
        self._server = None

    async def serve(self):
        """Start the Lumi DICOM Image Router server."""
        self._ae = AE(ae_title=self.source_ae)

        # Add storage SOP classes
        self._ae.add_supported_context(Verification)
        self._ae.add_supported_context(CTImageStorage)
        self._ae.add_supported_context(MRImageStorage)

        handlers = [
            (evt.EVT_C_STORE, self._handle_c_store),
        ]

        logger.info(
            "Lumi DICOM Image Router listening on %s:%s (AE: %s)",
            self.bind, self.port, self.source_ae,
        )

        self._server = self._ae.start_server(
            (self.bind, self.port),
            block=False,
            evt_handlers=handlers,
        )

        while True:
            await asyncio.sleep(1)

    def _handle_c_store(self, event):
        """Handle C-STORE — forward ke destination AE."""
        ds = event.dataset
        sop_uid = getattr(ds, "SOPInstanceUID", "unknown")

        logger.info(
            "Lumi DICOM Image Router: C-STORE received (SOP: %s)",
            sop_uid,
        )

        # Log transfer job
        with self.db.connect() as conn:
            for dest in self.destinations:
                conn.execute(
                    """
                    INSERT INTO image_transfer_jobs (
                        sop_instance_uid, source_ae, destination_ae, status
                    ) VALUES (?, ?, ?, 'pending')
                    """,
                    (sop_uid, self.source_ae, dest.get("ae_title", "")),
                )
            conn.commit()

        # Forward ke destinations (async via asyncio.create_task)
        for dest in self.destinations:
            asyncio.create_task(self._forward_image(ds, dest))

        return 0x0000

    async def _forward_image(self, ds: Dataset, destination: dict):
        """Forward image ke destination AE."""
        from pynetdicom import AE as ClientAE

        ae = ClientAE()
        dest_ae = destination.get("ae_title", "UNKNOWN")
        dest_host = destination.get("host", "127.0.0.1")
        dest_port = destination.get("port", 11112)

        logger.info(
            "Lumi DICOM Image Router: forwarding to %s@%s:%s",
            dest_ae, dest_host, dest_port,
        )

        try:
            assoc = ae.associate(dest_host, dest_port, ae_title=dest_ae)
            if assoc.is_established:
                status = assoc.send_c_store(ds)
                logger.info(
                    "Lumi DICOM Image Router: forwarded to %s (status: 0x%04x)",
                    dest_ae, status.Status,
                )
                assoc.release()
            else:
                logger.error(
                    "Lumi DICOM Image Router: association to %s failed",
                    dest_ae,
                )
        except Exception as e:  # noqa: BLE001 — forward errors are logged, never fatal
            logger.error(
                "Lumi DICOM Image Router: forward to %s failed: %s",
                dest_ae, e,
            )

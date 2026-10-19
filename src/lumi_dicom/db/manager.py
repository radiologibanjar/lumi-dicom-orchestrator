"""
Lumi DICOM — Database Manager
Copyright © 2026 Lumi DICOM. All rights reserved.

SQLite database manager for Lumi DICOM Orchestrator.
Handles connections, migrations, and all CRUD operations.
"""

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from lumi_dicom.db.schema import SCHEMA_SQL
from lumi_dicom.models.worklist import WorklistItem, WorklistStatus

logger = logging.getLogger("lumi-dicom")


class DatabaseManager:
    """Lumi DICOM database manager — SQLite with WAL mode."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._connection: sqlite3.Connection | None = None

    def init(self):
        """Initialize database — create tables, set WAL mode."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        conn.close()
        logger.info("Lumi DICOM database initialized at %s", self.db_path)

    @contextmanager
    def connect(self):
        """Context manager for SQLite connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
        finally:
            conn.close()

    # ── Worklist CRUD ───────────────────────────────────────────────────────

    def create_worklist_item(self, item: WorklistItem) -> int:
        """Insert a new worklist item. Returns the row id."""
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO worklist_items (
                    source_id, accession_number, study_instance_uid,
                    requested_procedure_id, patient_id, patient_name,
                    patient_birth_date, patient_sex, patient_weight,
                    scheduled_procedure_step_start_date,
                    scheduled_procedure_step_start_time, modality,
                    scheduled_station_aetitle, procedure_code,
                    procedure_description, procedure_code_sequence,
                    referring_physician_name, study_description, study_id,
                    status, source, external_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.source_id, item.accession_number,
                    item.study_instance_uid, item.requested_procedure_id,
                    item.patient_id, item.patient_name,
                    item.patient_birth_date, item.patient_sex,
                    item.patient_weight,
                    item.scheduled_procedure_step_start_date,
                    item.scheduled_procedure_step_start_time,
                    item.modality, item.scheduled_station_aetitle,
                    item.procedure_code, item.procedure_description,
                    item.procedure_code_sequence,
                    item.referring_physician_name,
                    item.study_description, item.study_id,
                    item.status.value, item.source, item.external_id,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_worklist_item(self, item_id: int) -> WorklistItem | None:
        """Fetch worklist item by id."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM worklist_items WHERE id = ?", (item_id,)
            ).fetchone()
            return WorklistItem.from_row(row) if row else None

    def get_by_accession(self, accession_number: str) -> WorklistItem | None:
        """Fetch worklist item by accession number."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM worklist_items WHERE accession_number = ?",
                (accession_number,),
            ).fetchone()
            return WorklistItem.from_row(row) if row else None

    def list_worklist(
        self,
        status: WorklistStatus | None = None,
        modality: str | None = None,
        station_ae: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        patient_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[WorklistItem]:
        """List worklist items with optional filters."""
        conditions = ["1=1"]
        params: list = []

        if status:
            conditions.append("status = ?")
            params.append(status.value)
        if modality:
            conditions.append("modality = ?")
            params.append(modality)
        if station_ae:
            conditions.append("scheduled_station_aetitle = ?")
            params.append(station_ae)
        if date_from:
            conditions.append("scheduled_procedure_step_start_date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("scheduled_procedure_step_start_date <= ?")
            params.append(date_to)
        if patient_id:
            conditions.append("patient_id = ?")
            params.append(patient_id)

        params.extend([limit, offset])

        sql = f"SELECT * FROM worklist_items WHERE {' AND '.join(conditions)} "
        sql += "ORDER BY scheduled_procedure_step_start_date DESC, "
        sql += "scheduled_procedure_step_start_time DESC LIMIT ? OFFSET ?"

        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [WorklistItem.from_row(r) for r in rows]

    def update_status(
        self, item_id: int, new_status: WorklistStatus
    ) -> bool:
        """Update worklist item status."""
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE worklist_items
                SET status = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (new_status.value, item_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_worklist_item(self, item_id: int) -> bool:
        """Delete worklist item by id."""
        with self.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM worklist_items WHERE id = ?", (item_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def upsert_by_source_id(self, item: WorklistItem) -> tuple[int, bool]:
        """
        Upsert worklist item keyed on source_id.
        Returns (id, created) — created=True if inserted, False if updated.
        """
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM worklist_items WHERE source_id = ?",
                (item.source_id,),
            ).fetchone()

            if existing:
                item_id = existing["id"]
                conn.execute(
                    """
                    UPDATE worklist_items SET
                        accession_number=?, study_instance_uid=?,
                        requested_procedure_id=?, patient_id=?,
                        patient_name=?, patient_birth_date=?,
                        patient_sex=?, patient_weight=?,
                        scheduled_procedure_step_start_date=?,
                        scheduled_procedure_step_start_time=?,
                        modality=?, scheduled_station_aetitle=?,
                        procedure_code=?, procedure_description=?,
                        procedure_code_sequence=?, referring_physician_name=?,
                        study_description=?, study_id=?, status=?,
                        source=?, external_id=?, updated_at=datetime('now')
                    WHERE id=?
                    """,
                    (
                        item.accession_number, item.study_instance_uid,
                        item.requested_procedure_id, item.patient_id,
                        item.patient_name, item.patient_birth_date,
                        item.patient_sex, item.patient_weight,
                        item.scheduled_procedure_step_start_date,
                        item.scheduled_procedure_step_start_time,
                        item.modality, item.scheduled_station_aetitle,
                        item.procedure_code, item.procedure_description,
                        item.procedure_code_sequence,
                        item.referring_physician_name,
                        item.study_description, item.study_id,
                        item.status.value, item.source, item.external_id,
                        item_id,
                    ),
                )
                conn.commit()
                return item_id, False

            # Insert new
            cursor = conn.execute(
                """
                INSERT INTO worklist_items (
                    source_id, accession_number, study_instance_uid,
                    requested_procedure_id, patient_id, patient_name,
                    patient_birth_date, patient_sex, patient_weight,
                    scheduled_procedure_step_start_date,
                    scheduled_procedure_step_start_time, modality,
                    scheduled_station_aetitle, procedure_code,
                    procedure_description, procedure_code_sequence,
                    referring_physician_name, study_description, study_id,
                    status, source, external_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.source_id, item.accession_number,
                    item.study_instance_uid, item.requested_procedure_id,
                    item.patient_id, item.patient_name,
                    item.patient_birth_date, item.patient_sex,
                    item.patient_weight,
                    item.scheduled_procedure_step_start_date,
                    item.scheduled_procedure_step_start_time,
                    item.modality, item.scheduled_station_aetitle,
                    item.procedure_code, item.procedure_description,
                    item.procedure_code_sequence,
                    item.referring_physician_name,
                    item.study_description, item.study_id,
                    item.status.value, item.source, item.external_id,
                ),
            )
            conn.commit()
            return cursor.lastrowid, True

# src/lumi_dicom/db/

## Responsibility
Persistence layer — DDL SQLite (`schema.sql`) dan Data Access Object `DatabaseManager` untuk semua operasi baca/tulis.

## Design
- `schema.py`: memuat `schema.sql` sekali saat import menjadi konstanta `SCHEMA_SQL` (bukan migrasi berversi — hanya `CREATE TABLE IF NOT EXISTS`, idempoten, tanpa skema versioning).
- `DatabaseManager` (Repository/DAO):
  - `init()` — DDL sekali di startup + `PRAGMA journal_mode=WAL` dan `foreign_keys=ON`.
  - `connect()` — contextmanager yang membuka **koneksi baru per pemanggilan** (aman untuk pola multi-task asyncio: API + SCP); `row_factory = sqlite3.Row`.
  - CRUD worklist: `create_worklist_item`, `get_worklist_item`, `get_by_accession`, `list_worklist` (WHERE dinamis: status/modality/station/date range/patient + LIMIT/OFFSET, urut date-time DESC), `update_status`, `delete_worklist_item`.
  - `upsert_by_source_id(item) -> (id, created)` — kunci idempotensi untuk semua jalur inbound (SELECT by `source_id` → UPDATE seluruh kolom, atau INSERT).
- Tabel (dari `schema.sql`): `worklist_items` (utama, CHECK status & patient_sex, UNIQUE `source_id`/`accession_number`/`study_instance_uid`), `modalities`, `mpps_events`, `image_transfer_jobs`, `audit_log`; 9 indeks pemulus query worklist/audit/transfer.
- Akses tabel non-worklist (`modalities`, `audit_log`, `mpps_events`, `image_transfer_jobs`) dilakukan **langsung dengan SQL inline** dari pemanggil (routes, mpps, image_router), tidak lewat DAO.

## Flow
1. `__main__.run_orchestrator` → `DatabaseManager(db_path).init()` sebelum service lain hidup.
2. Writer: `api/routes`, `api/inbound` (upsert), `dicom/mpps` (UPDATE status), `workers/image_router` (INSERT job).
3. Reader: `dicom/mwl_scp` (query C-FIND), `api/routes` (list/detail/audit/modalities).

## Integration
- **Dikonsumsi oleh**: `api.routes`, `api.inbound`, `dicom.mwl_scp`, `dicom.mpps`, `workers.image_router`, `__main__`, `scripts/init_db.py`.
- **Bergantung pada**: `db.schema.SCHEMA_SQL`, `models.worklist.WorklistItem`/`WorklistStatus`.
- **Lokasi DB**: `database.path` (default `worklist.db` di root repo; Docker: `/data/worklist.db` via `LUMI_DICOM_DATABASE__PATH`).
- **Diuji oleh**: `tests/test_worklist.py::TestDatabaseManager` (CRUD dasar).

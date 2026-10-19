# src/lumi_dicom/models/

## Responsibility
Domain model dan skema API (pydantic v2) — kontrak tunggal antara inbound parser, REST API, lapisan DB, dan pemetaan DICOM.

## Design
- `WorklistStatus(str, Enum)`: `pending → in_progress → completed | cancelled` — identik dengan CHECK constraint di `schema.sql` (kontrak dipelihara di dua tempat).
- `WorklistItem` — agregat kanonik, field selaras tag DICOM (`patient_id` = 0010,0020, `scheduled_..._date` = YYYYMMDD, dst):
  - `from_row(sqlite3.Row)`: koersi `status` string → enum; **mendecode JSON `procedure_code_sequence`** lalu `cls(**data)`.
  - `generate_uids()`: `StudyInstanceUID` kosong → `2.25.<int uuid4>` (arc OID turunan UUID, tanpa registrasi).
  - Tipe `procedure_code_sequence: Optional[str]` (JSON-encoded) — lihat Known Issues.
- `ProcedureCode` — entri Code Sequence (value/scheme/meaning).
- Skema API: `WorklistCreateRequest` (body POST; wajib accession/patient/date/modality), `WorklistStatusUpdate` (body PATCH), `WorklistResponse` (respons datar; `status` sebagai `str`).

## Flow
- Inbound: parser `inbound.*` atau `api/routes.create_worklist` → `WorklistItem` → `DatabaseManager.upsert_by_source_id` (menyimpan `status.value`) → `WorklistResponse`.
- Outbound: `from_row` membaca baris → `mwl_scp._to_dicom_dataset` / handler API.
- `WorklistItem.from_row` dipakai di `db.manager` dan `dicom/mwl_scp`.

## Integration
- **Dikonsumsi oleh**: `db.manager`, `api.routes`, `api.inbound`, `inbound.hl7`, `inbound.fhir`, `dicom.mwl_scp`, `tests/*`.
- **Bergantung pada**: `pydantic` (`BaseModel`, `Field`), stdlib `json`/`uuid`/`enum`.

## Known Issues
- **Bug**: `from_row` mengubah `procedure_code_sequence` JSON menjadi `list`, tetapi field bertipe `Optional[str]` → pydantic v2 melempar `ValidationError` untuk SEMUA pembacaan (`get_worklist_item`, `list_worklist`, C-FIND) begitu kolom itu terisi. Terverifikasi empiris. Perbaikan paling kecil: decode-ke-list saja dihapus, atau field dinaikkan tipe `list[dict] | str` dengan adapter saat menyimpan.
- Duplikasi validasi panjang field wajib antara `WorklistItem` dan `WorklistCreateRequest` (kandidat shared schema).

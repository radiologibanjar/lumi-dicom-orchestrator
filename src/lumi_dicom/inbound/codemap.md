# src/lumi_dicom/inbound/

## Responsibility
Adapter format inbound — memparse HL7 v2 (ORM^O01) dan FHIR R4 menjadi domain object `WorklistItem` kanonik. Murni parser, tanpa akses database.

## Design
- **HL7 (`hl7.py`, ~630 baris)**: kelas `HL7Parser` dengan pipeline: `_split_segments` → `_split_fields`/`_split_components` (pemisah `|`/`~`/`^`) → `_unescape` (escaping HL7 `\F\`, `\S\`, dll) → extractor per segmen (`_pid_*` untuk pasien, `_orc_*` order, `_obr_*` prosedur/aksesi, `_pv1_*` kunjungan) → `_build_worklist_item()`. Pemetaan tanggal/datetimes (`_parse_hl7_date`, `_parse_hl7_datetime`), format nama (`_format_patient_name` → pola DICOM `SURNAME^GIVEN`), inferensi modality dari OBR-4/OBR-7 (`_extract_modality`), derivation `source_id`/UID. Fasad modul: `parse_hl7_message(raw) -> WorklistItem`.
- **FHIR (`fhir.py`)**: exception `FHIRError` + dispatcher `map_fhir_to_worklist(data)` pada `resourceType` (ServiceRequest / ImagingStudy / Bundle). Helper: `_parse_service_request` (kunjungan patient reference + identifier), `_parse_imaging_study` (modality/UID dari series), `_find_patient_in_bundle`, `_format_date`, `_extract_identifier_value`.

## Flow
1. `api/inbound.py` menerima raw text (HL7) atau JSON dict (FHIR).
2. Parser melempar `ValueError`/`FHIRError` → endpoint memetakan ke HTTP 422; error tak terduga → 500.
3. Hasil `WorklistItem` (status default `pending`, `source` diset sesuai format) dikirim ke `DatabaseManager.upsert_by_source_id()` — idempoten berdasarkan `source_id` hasil turunan parser.

## Integration
- **Dikonsumsi oleh**: `api/inbound.py` (`POST /api/v1/inbound/hl7`, `POST /api/v1/inbound/fhir`).
- **Bergantung pada**: `models.worklist` (`WorklistItem`, `WorklistStatus`) saja — tidak menyentuh SQLite.
- `inbound/__init__.py` hanya docstring (tanpa re-export).
- **Uji**: tidak ada test khusus parser di `tests/` (cakupan celah).

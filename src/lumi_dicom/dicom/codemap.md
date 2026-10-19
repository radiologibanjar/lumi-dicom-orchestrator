# src/lumi_dicom/dicom/

## Responsibility
Service Class Provider DICOM — `MWLSCP` menjawab C-FIND Modality Worklist, `MPPSSCP` menerima N-CREATE/N-SET Modality Performed Procedure Step.

## Design
- Pola: satu kelas per layanan, satu `pynetdicom.AE` per kelas, `start_server(block=False, evt_handlers=[...])` lalu loop `await asyncio.sleep(1)` sebagai keep-alive inside asyncio task.
- **`MWLSCP`**:
  - Handler: `EVT_C_FIND` (`_handle_c_find`), `EVT_ESTABLISHED` (logging + allow-list `allowed_aetitles` → `assoc.abort()` bila ditolak), `EVT_RELEASED`.
  - `_build_query(identifier)` menerjemahkan atribut C-FIND → SQL parametrised: `PatientID`, `PatientName` (LIKE wildcard), `AccessionNumber`, `Modality`, `ScheduledProcedureStepStartDate` (eksak atau rentang `YYYYMMDD-YYYYMMDD` dengan sisi terbuka), `ScheduledStationAETitle`; selalu `status != 'cancelled'`; wildcard `""`/`*` dilewatkan via `_is_blank` (semantik DICOM "match any"). Urutkan date/time DESC.
  - `_to_dicom_dataset(item)` memetakan `WorklistItem` → `Dataset`, termasuk `ProcedureCodeSequence` dari JSON (`_build_code_sequence`, fallback ke `procedure_code`).
  - Capping `max_results` → bila terlampaui: status `0xC000` (Unable to Process); per baris `0xFF00` (pending); terminator `0x0000`.
  - TLS opsional via `_create_ssl_context()` (cert/key PEM; `FileNotFoundError` bila path tak ada).
- **`MPPSSCP`**: handler `EVT_N_CREATE` → cari worklist by `AccessionNumber` → INSERT `mpps_events` (status `IN PROGRESS`) + UPDATE status worklist → `in_progress`; `EVT_N_SET` → UPDATE `mpps_events` → `COMPLETED` + worklist → `completed`. Keduanya commit transaksi lokal.

## Flow
1. `__main__.run_orchestrator` membuat `asyncio.create_task(mwl_scp.serve())` bila `mwl_scp.enabled` (idem MPPS).
2. AE listen `(bind, port)` → asosiasi masuk → allow-list check → C-FIND → query SQLite via `db.connect()` → yield dataset per baris.
3. Modalitas menerima worklist; MPPS mengembalikan status progres ke orchestrator.

## Integration
- **Bergantung pada**: `db.manager.DatabaseManager` (koneksi per-query), `models.worklist.WorklistItem.from_row`.
- **Dikonfigurasi**: kunci `mwl_scp.*` dan `mpps.*` di `config/default.yaml` (AE title, port 11112/11113, bind, allowed_aetitles, max_associations, max_results, tls).
- **Diuji oleh**: `tests/test_mwl_scp.py` (C-FIND match & no-match lewat SCU pynetdicom nyata).
- **Konsumen**: modalitas (C-FIND), `scripts/smoke_scu.py`.

## Known Issues
- `__main__` tidak pernah meneruskan `tls_cert`/`tls_key` ke `MWLSCP`/`MPPSSCP` → blok `mwl_scp.tls` / `mpps.tls` di `default.yaml` **mati total**.
- `WorklistItem.from_row` melempar `ValidationError` bila `procedure_code_sequence` terisi → C-FIND pada baris tersebut gagal (lihat `models/codemap.md`).
- `host` di config tidak dipakai (yang dipakai `bind`); `max_associations` disimpan tapi tidak dibatasi oleh AE.

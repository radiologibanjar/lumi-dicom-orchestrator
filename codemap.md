# Repository Atlas: Lumi DICOM Orchestrator

## Project Responsibility
Orkestrator DICOM radiologi berbahasa Python: menerima order dari SIMRS lewat REST API (FHIR-compatible) dan HL7 v2, menyimpannya sebagai worklist di SQLite (source of truth lokal), lalu menyajikannya ke modalitas lewat DICOM MWL C-FIND (pynetdicom). MPPS dan image routing tersedia sebagai layanan opsional.

Stack: **FastAPI + uvicorn** (API :8765), **pynetdicom + pydicom** (MWL SCP :11112, MPPS :11113, image route :11114), **SQLite WAL** (worklist.db), **pydantic v2**, konfigurasi YAML + env `LUMI_DICOM_<SECTION>__<KEY>`.

## System Entry Points
- `src/lumi_dicom/__main__.py` — composition root: `lumi-dicom start --config config/default.yaml` → load config → init DB → jalankan FastAPI (uvicorn) + task SCP paralel dalam satu event loop, shutdown via SIGINT/SIGTERM.
- `pyproject.toml` — `[project.scripts] lumi-dicom = "lumi_dicom.__main__:main"`; layout `src/`; dev extra (pytest, ruff).
- `config/default.yaml` — konfigurasi semua komponen (lihat [config/codemap.md](config/codemap.md)).
- `Dockerfile` / `docker-compose.yml` — image `python:3.12-slim`, expose 8765 + 11112, volume `/data`.
- `.github/workflows/ci.yml` — CI: Python 3.12, `ruff check src/ tests/`, `pytest --cov`, build/push image ke GHCR.

## Data & Control Flow (end-to-end)
```
SIMRS ──POST /api/v1/worklist──┐
SIMRS ──POST /api/v1/inbound/hl7──┤→ inbound parsers (hl7/fhir) ─┐
MediRad ──scripts/medirad_connector.py──┘                        ├→ WorklistItem
                                                                  ↓
                                        DatabaseManager.upsert_by_source_id (SQLite, idempoten)
                                                                  ↓
Modalitas ──C-FIND──> MWLSCP._handle_c_find → SQL (status != cancelled) → Dataset per baris
Modalitas ──N-CREATE/N-SET──> MPPSSCP → mpps_events + status worklist in_progress/completed
Modalitas ──C-STORE──> ImageRouter → image_transfer_jobs + forward ke destination AE
SIMRS/dashboard ──GET /api/v1/worklist──> UI monitoring (route `/`) & /docs
```
Status lifecycle: `pending → in_progress → completed | cancelled` (enum pydantic == CHECK constraint DB).

## Repository Directory Map (Aggregated)
| Directory | Responsibility Summary | Detailed Map |
|-----------|------------------------|--------------|
| `src/lumi_dicom/` | Composition root: CLI, config loader (YAML+env), dashboard `/`, docs `/docs`. | [map](src/lumi_dicom/codemap.md) |
| `src/lumi_dicom/api/` | FastAPI app factory, API-key middleware, route worklist/modalities/audit, endpoint inbound. | [map](src/lumi_dicom/api/codemap.md) |
| `src/lumi_dicom/inbound/` | Parser murni HL7 v2 ORM^O01 dan FHIR R4 → `WorklistItem`. | [map](src/lumi_dicom/inbound/codemap.md) |
| `src/lumi_dicom/dicom/` | SCP: MWL C-FIND (query builder → SQL) dan MPPS N-CREATE/N-SET. | [map](src/lumi_dicom/dicom/codemap.md) |
| `src/lumi_dicom/workers/` | ImageRouter: C-STORE masuk → log job → forward ke AE tujuan. | [map](src/lumi_dicom/workers/codemap.md) |
| `src/lumi_dicom/db/` | `schema.sql` (DDL) + `DatabaseManager` DAO SQLite WAL. | [map](src/lumi_dicom/db/codemap.md) |
| `src/lumi_dicom/models/` | Skema pydantic domain + API (`WorklistItem`, request/response). | [map](src/lumi_dicom/models/codemap.md) |
| `config/` | `default.yaml` (semua section + env override) & `medirad.env` (kredensial adapter). | [map](config/codemap.md) |
| `scripts/` | init_db, generate_tls_cert, smoke_scu, medirad_connector. | [map](scripts/codemap.md) |
| `tests/` | 22 test: C-FIND MWL via SCU nyata + CRUD worklist + API layer/regresi (**di luar cakupan codemap**) | — |
| `.github/` | CI (ruff + pytest di Python 3.12), release ke GHCR, dependabot, PR template. | — |

## Verification Status (2026-10-19, setelah perbaikan)
- `pytest` → **22 passed** (7 warning deprecation pydicom v4).
- `ruff check src/ tests/` → **All checks passed** (0 error) — paritas dengan gate CI.
- Python 3.12 (setara CI): `create_app()` boots, `POST /api/v1/worklist` + `procedure_code_sequence` → 201, dashboard feed 200.
- Docker (`python:3.12-slim`): build OK, container boot, `/health` 200, `/dashboard/api/worklist` 200.

## Known Issues — SEMUA SUDAH DIPERBAIKI (2026-10-19)
1. ~~`api/server.py` — `Request` tidak di-import~~ → **FIXED**: `Request` di-import; terverifikasi di Python 3.12 & container.
2. ~~`api/routes.py` — `import json` tidak ada~~ → **FIXED**: `import json` ditambahkan; POST dengan `procedure_code_sequence` → 201.
3. ~~`models/worklist.py::from_row` mendecode JSON ke `list`~~ → **FIXED**: field tetap `str`; terverifikasi via C-FIND regresi + round-trip API. `mwl_scp._to_dicom_dataset` juga diperbaiki: CodeSequence dibangun jika `procedure_code` **atau** `procedure_code_sequence` terisi.
4. ~~`Dockerfile` tidak menyalin `config/`~~ → **FIXED**: `COPY config/ ./config/` ditambahkan; container boot sukses.
5. ~~TLS mati + `load_settings` dead code~~ → **FIXED**: helper `_resolve_tls()` meneruskan cert/key ke `MWLSCP`/`MPPSSCP` saat `tls.enabled`; `load_settings` membaca section top-level + memetakan `tls` → `tls_cert`/`tls_key`; `APIConfig.api_keys` ditambahkan.
6. ~~`config/medirad.env` berisi kredensial~~ → **FIXED**: nilai diganti placeholder, `config/medirad.env.example` dibuat, `.gitignore` menolak `config/*.env` + `certs/*.pem`. **Token JWT lama wajib di-rotasi di server MediRad.**
7. **(baru, dari ruff)** `inbound/fhir.py` typo `FHIREError` → `NameError` (422 jadi 500) → **FIXED**.
8. **Dashboard UI** JS meng-hardcode `X-API-Key: lumi-dicom-dev-key` ke `/api/v1/worklist` (patah bila `api_keys` diganti) → **FIXED**: endpoint `/dashboard/api/worklist` (tanpa API key, handler `list_worklist` bersama) + JS memakainya; `/api/v1/*` tetap terproteksi key.
9. **(baru) Dashboard JS syntax error sejak awal** — `DASHBOARD_HTML` string Python non-raw: `\n` di regex `csvEscape` dan `\r\n`/`\uFEFF` di `exportCSV` di-parse Python jadi karakter literal → JS gagal parse total → UI selalu stuck "Menghubungkan.../Memuat..." (penyebab asli keluhan dashboard). **FIXED**: escape digandakan (`\\n`, `\\r\\n`, `\\uFEFF`); terverifikasi `node --check` = valid + semua 18 `getElementById` ada di DOM. Test regresi `test_dashboard_js_is_valid_syntax` ditambahkan.

## Sisa perhatian (di luar cakupan fix, belum dikerjakan)
- Cakupan test masih tipis di luar API/MWL: parser HL7/FHIR, MPPS SCP, ImageRouter, medirad_connector belum punya test sendiri.
- `lumi-dicom-dev-key` di `config/default.yaml` masih key dev default — ganti saat deploy produksi.
- Repo belum `git init` (CI/workflow `.github/` belum pernah berjalan); inisialisasi + commit pertama disarankan agar `.gitignore` efektif.

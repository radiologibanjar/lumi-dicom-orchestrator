# src/lumi_dicom/api/

## Responsibility
Transport layer HTTP — app factory FastAPI, autentikasi API key, resource route REST (worklist/modalities/audit/health), dan endpoint masuk (inbound) HL7/FHIR.

## Design
- `server.create_app(db_manager, config)` adalah composition root web-layer: lifespan logging → `app.state.db_manager` + `app.state.api_keys` (dependency injection ala FastAPI) → CORS → `routes.router` + `inbound.router` → middleware API key → router dashboard (`lumi_dicom.dashboard`) dan docs (`lumi_dicom.docs`). Swagger bawaan dimatikan (`docs_url=None`), diganti route `/docs` custom.
- **Auth dua lapis**: `LumiAPIKeyMiddleware` (BaseHTTPMiddleware) menegakkan header `X-API-Key` pada semua path prefixed `/api/v1/` (401 bila hilang/salah); `auth.get_api_key` adalah dependency per-route (import tapi jarang dipakai); `auth.APIKeyAuth` helper class reusable (validasi/tambah/hapus key).
- `routes.py`: `APIRouter` + `Depends(get_db)` yang membaca `app.state.db_manager`. Filter worklist dikonstruksi dinamis → `DatabaseManager.list_worklist(...)`.
- `inbound.py`: `APIRouter` terpisah — baca raw body (`await request.body()`) untuk HL7, JSON dict untuk FHIR; error parser dipetakan ke 422, error DB ke 500.

## Flow
1. `__main__.run_orchestrator` → `create_app()` → `uvicorn.Server.serve()` sebagai asyncio task.
2. Request `/api/v1/*` → middleware cek API key → route handler → `Depends(get_db)` → `DatabaseManager` → response pydantic (`WorklistResponse`).
3. `POST /api/v1/worklist`: `WorklistCreateRequest` → normalisasi tanggal `YYYY-MM-DD` → `json.dumps(procedure_code_sequence)` → `WorklistItem` + `generate_uids()` → `db.upsert_by_source_id()` (idempoten pada `source_id`) → re-fetch → respons.
4. `POST /api/v1/inbound/hl7|fhir`: payload → `parse_hl7_message` / `map_fhir_to_worklist` → `db.upsert_by_source_id()` → respons.
5. `PATCH /api/v1/worklist/{id}/status` → `db.update_status()` (enum `WorklistStatus` divalidasi, 400 untuk nilai tak dikenal).

## Integration
- **Dipakai oleh**: `lumi_dicom.__main__` (`create_app`), yang juga memasang dashboard/docs router.
- **Bergantung pada**: `db.manager.DatabaseManager`, `models.worklist`, `inbound.hl7`, `inbound.fhir`, `config` (kunci `api.cors_origins`, `api.api_keys`).
- **Endpoint**: `GET /health`, `/api/v1/worklist` (GET/POST), `/api/v1/worklist/{id}` (GET/DELETE), `/api/v1/worklist/{id}/status` (PATCH), `/api/v1/modalities`, `/api/v1/audit`, `/api/v1/inbound/health|hl7|fhir`.

## Known Issues
- `server.py`: `Request` dipakai sebagai anotasi di `LumiAPIKeyMiddleware.dispatch` tetapi **tidak di-import**. Pada Python ≤3.13 (evaluasi anotasi eager) `create_app()` melempar `NameError` — lokal hanya lolos karena venv Python 3.14 (PEP 649). Docker/CI memakai 3.12.
- `routes.py`: `json.dumps` dipakai (baris ~127) tetapi **`import json` tidak ada** → `NameError` saat body POST punya `procedure_code_sequence`.
- Duplikasi mapping dict → `WorklistResponse` di 4 handler (kandidat refactor).

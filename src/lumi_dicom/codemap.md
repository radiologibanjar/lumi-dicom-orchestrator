# src/lumi_dicom/

## Responsibility
Akar paket `lumi_dicom` — composition root: konstanta identitas, CLI entry (`__main__`), loader konfigurasi, router UI dashboard dan dokumentasi.

## Design
- `__init__.py`: `__version__`/`__brand__`/`__copyright__` + re-export publik `Settings`, `DatabaseManager`, `WorklistItem`, `WorklistStatus`.
- `__main__.py` (composition root, ~190 baris):
  - `main()` — argparse subcommand `start --config <yaml>` → `load_config()` → `logging.basicConfig` (logger name `lumi-dicom`) → `asyncio.run(run_orchestrator(cfg))`.
  - `load_config()` — YAML → merge section `lumi_dicom:` ke top-level → **walk rekursif override env `LUMI_DICOM_<SECTION>__<KEY>`** dengan separator `__` dan `_parse_env_value` (bool/int/list koma/str).
  - `run_orchestrator()` — urutan start: `DatabaseManager.init()` → `create_app()` + `uvicorn.Server` → task opsional `MWLSCP` / `MPPSSCP` / `ImageRouter` (per kunci `*.enabled`) → tunggu `stop_event` (SIGINT/SIGTERM; fallback `signal.signal` di Windows) → `task.cancel()` semua → `gather`.
- `config.py` — dataclass `Settings` + `load_settings()` (**dead code**, lihat Known Issues); tidak dipakai runtime.
- `dashboard.py` (~850 baris) — `create_dashboard_router()` mengembalikan router dengan route `/`: HTML SPA monitoring worklist (fetch ke `/api/v1/worklist`).
- `docs.py` (~540 baris) — `create_docs_router()` route `/docs`: dokumentasi/OpenAPI custom menggantikan Swagger bawaan yang dimatikan di `server.py`.

## Flow
`lumi-dicom start` (entry `[project.scripts]`) → `load_config(config/default.yaml)` + env override → `run_orchestrator` → semua service hidup paralel dalam satu event loop → Ctrl+C → shutdown berantai.

## Integration
- **Entry point**: `pyproject.toml [project.scripts] lumi-dicom = "lumi_dicom.__main__:main"`; juga `python -m lumi_dicom`.
- **Memanggil**: `api.server.create_app`, `db.manager.DatabaseManager`, `dicom.mwl_scp.MWLSCP`, `dicom.mpps.MPPSSCP`, `workers.image_router.ImageRouter`.
- **Dipasang di Docker**: `ENTRYPOINT ["lumi-dicom"]`, `CMD ["start","--config","config/default.yaml"]`.

## Known Issues
- `config.load_settings()` membaca section dari `raw["lumi_dicom"]` padahal section komponen ada di top-level → selalu jatuh ke default; plus kunci `tls:` tak dikenal dataclass. Saat ini tidak dipanggil siapa pun.
- `__main__` tidak meneruskan blok `tls.*` ke SCP → TLS tak pernah aktif walau dikonfigurasi.
- Runtime lokal (Python 3.14) menyembunyikan `NameError` anotasi `Request` di `api/server.py` yang akan meledak di Python 3.10–3.13 (lihat `api/codemap.md`).

# scripts/

## Responsibility
Perkakas dev/ops mandiri — tidak diimpor oleh aplikasi, tidak ikut image Docker (`Dockerfile` hanya menyalin `src/` + `pyproject.toml` + `README.md`).

## Design / Flow
| Script | Peran | Pemakaian |
|---|---|---|
| `init_db.py` | Init skema SQLite (`DatabaseManager.init()`), menyisipkan `src/` ke `sys.path` | `python scripts/init_db.py --db worklist.db` |
| `generate_tls_cert.py` | Self-signed cert TLS via `openssl req -x509 -newkey rsa:2048` → `cert.pem`/`key.pem` | `python scripts/generate_tls_cert.py --output-dir certs --days 365` (dev saja) |
| `smoke_scu.py` | SCU C-FIND nyata ke `127.0.0.1:11112` sebagai `MODALITY_CT01`, cetak match (Accession/Patient/Modality/Station) | jalankan saat orchestrator hidup — verifikasi end-to-end MWL |
| `medirad_connector.py` | Adapter polling eksternal: `_load_config` baca `config/medirad.env` → `get_medirad_token` → `get_order_radiologi` → `transform_order` (MediRad → payload worklist) → `forward_to_lumi` (POST `/api/v1/worklist` + header `X-API-Key`) | `python scripts/medirad_connector.py --once` atau loop `FETCH_INTERVAL_MINUTES` |

## Integration
- `medirad_connector.py` adalah satu-satunya konsumen `config/medirad.env`; memanggil API in-process (port 8765) sehingga butuh orchestrator berjalan.
- `smoke_scu.py` adalah pasangan verifikasi `tests/test_mwl_scp.py` untuk mode manual.
- `generate_tls_cert.py` menghasilkan artefak ke `certs/` yang dirujuk konfigurasi `mwl_scp.tls.*` (yang saat ini belum ter-wire oleh runtime).

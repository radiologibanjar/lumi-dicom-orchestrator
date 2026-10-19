# config/

## Responsibility
Konfigurasi runtime — YAML utama aplikasi dan kredensial adapter eksternal (opsional).

## Design
### `default.yaml`
Dibaca oleh `lumi_dicom.__main__.load_config` (bukan `config.load_settings`). Section:
| Section | Kunci utama | Default |
|---|---|---|
| `lumi_dicom` | `name`, `version`, `environment` | 0.1.0 / development |
| `database` | `path`, `wal_mode`, `auto_vacuum` | `worklist.db` |
| `api` | `host`, `port`, `cors_origins`, `api_keys` | `0.0.0.0:8765`, key `lumi-dicom-dev-key` |
| `mwl_scp` | `enabled`, `ae_title`, `port`, `bind`, `allowed_aetitles`, `max_associations`, `max_results`, `tls{enabled,cert_file,key_file}` | true, `LUMI_DICOM`, 11112 |
| `mpps` | `enabled`, `ae_title`, `port`, `bind`, `tls` | false, 11113 |
| `image_route` | `enabled`, `source_ae`, `host/port/bind`, `destinations[]` | false, 11114 |
| `logging` | `level`, `format`, `date_format` | INFO |

**Override env**: `LUMI_DICOM_<SECTION>__<KEY>` (separator `__`), tipe diparse otomatis (bool/int/list koma). Dipakai `Dockerfile` dan `docker-compose.yml`, mis. `LUMI_DICOM_DATABASE__PATH`, `LUMI_DICOM_MWL_SCP__BIND`.

### `medirad.env`
Konsumsi **hanya** oleh `scripts/medirad_connector.py` (shell-style KEY=VALUE): `MEDIRAD_TOKEN`, `MEDIRAD_BASE_URL`, `LUMI_DICOM_URL`, `LUMI_DICOM_API_KEY`, `FETCH_INTERVAL_MINUTES`.

## Flow
`lumi-dicom start --config config/default.yaml` → merge `lumi_dicom:` ke top-level → walk env override → dict konfigurasi → service dibaca per kunci.

## Integration
- Dirujuk: `Dockerfile` (CMD `--config config/default.yaml`), README, `scripts/medirad_connector.py`.
- **Catatan keamanan**: `medirad.env` berisi token JWT + API key yang ter-commit ke repo — seharusnya di-ignore dan di-rotasi.
- **Catatan kerja**: `Dockerfile` tidak pernah `COPY config/` → image gagal start dengan `FileNotFoundError` pada config; blok `mwl_scp.tls` diabaikan runtime; `lumi_dicom.config.load_settings` mengabaikan semua section top-level (dead code).

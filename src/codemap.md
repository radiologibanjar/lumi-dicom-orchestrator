# src/

## Responsibility
Layout sumber paket — satu paket Python `lumi_dicom` sesuai setuptools `where = ["src"]`, `include = ["lumi_dicom*"]` di `pyproject.toml`.

## Structure
| Path | Peran | Peta detail |
|------|-------|-------------|
| `lumi_dicom/` | Paket inti (composition root, config, dashboard, docs) | [lumi_dicom/codemap.md](lumi_dicom/codemap.md) |
| `lumi_dicom/api/` | Transport HTTP FastAPI + auth + route | [api/codemap.md](lumi_dicom/api/codemap.md) |
| `lumi_dicom/inbound/` | Parser HL7 v2 & FHIR R4 | [inbound/codemap.md](lumi_dicom/inbound/codemap.md) |
| `lumi_dicom/dicom/` | SCP DICOM (MWL C-FIND, MPPS) | [dicom/codemap.md](lumi_dicom/dicom/codemap.md) |
| `lumi_dicom/workers/` | Image Router (C-STORE forward) | [workers/codemap.md](lumi_dicom/workers/codemap.md) |
| `lumi_dicom/db/` | DDL + DAO SQLite | [db/codemap.md](lumi_dicom/db/codemap.md) |
| `lumi_dicom/models/` | Skema pydantic domain/API | [models/codemap.md](lumi_dicom/models/codemap.md) |
| `lumi_dicom.egg-info/` | Artefak build `pip install -e .` (generated, di-ignore) | — |

## Design
- Jalur import tanpa install didukung oleh `__main__.py` yang menyisipkan `src/` ke `sys.path` (dipakai scripts/dev).
- Konvensi project: docstring header copyright Lumi DICOM, separator comment antar grup import, logger `lumi-dicom`, prefix env `LUMI_DICOM_`.

## Integration
Dibangun oleh `pyproject.toml`; image Docker hanya menyalin `src/` + `pyproject.toml` + `README.md`.

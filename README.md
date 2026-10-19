# Lumi DICOM Orchestrator

> **Lumi DICOM** — Orchestrator DICOM radiologi. Menerima order dari SIMRS via
> REST API (FHIR-compatible), menyimpan worklist di SQLite, dan menyajikannya
> ke modalitas lewat DICOM MWL C-FIND (SCP).

## Arsitektur

```
┌──────────────┐     ┌──────────────────────────────────────────────┐
│   SIMRS /    │     │         Lumi DICOM Orchestrator              │
│  FHIR API    │────▶│                                              │
└──────────────┘     │  ┌────────────┐    ┌───────────────────────┐  │
                     │  │  Inbound   │    │   SQLite Worklist     │  │
┌──────────────┐     │  │  FastAPI   │───▶│   (source of truth)   │  │
│   HL7 v2     │────▶│  │  /api/v1   │    └───────────┬───────────┘  │
└──────────────┘     │  └────────────┘                │              │
                     │                                ▼              │
                     │                    ┌───────────────────────┐  │
                     │                    │    MWL SCP (C-FIND)   │  │
                     │                    │   pynetdicom :11112  │  │
                     │                    └───────────┬───────────┘  │
                     │                                │              │
                     │                    ┌───────────▼───────────┐  │
                     │                    │  Modalitas CT/MR/etc  │  │
                     │                    │  C-FIND MWL           │  │
                     │                    └───────────────────────┘  │
                     │                                              │
                     │  ┌────────────────────────────────────────┐  │
                     │  │  MPPS (opsional)  │  Image Route (ops)  │  │
                     │  └────────────────────────────────────────┘  │
                     └──────────────────────────────────────────────┘
```

## Komponen

| Layer | Deskripsi |
|-------|-----------|
| **Inbound API** | FastAPI REST — terima order FHIR dari SIMRS, validasi, normalisasi |
| **SQLite** | Buffer worklist — source of truth lokal |
| **MWL SCP** | pynetdicom SCP — sajikan worklist ke modalitas via C-FIND |
| **MPPS** | (Opsional) Terima N-CREATE/N-SET dari modalitas |
| **Image Route** | (Opsional) Route DICOM images antar AE |

## Instalasi

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

## Menjalankan

```bash
# Development
lumi-dicom start --config config/default.yaml

# Atau langsung
python -m lumi_dicom start --config config/default.yaml
```

## Konfigurasi

Lihat `config/default.yaml`. Semua nilai bisa dioverride via environment variable
dengan prefix `LUMI_DICOM_`, contoh: `LUMI_DICOM_DICOM_PORT=11112`.

## Endpoints API

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/health` | Health check |
| GET | `/` | Dashboard UI (monitoring worklist) |
| GET | `/api/v1/worklist` | List worklist (dengan filter) |
| POST | `/api/v1/worklist` | Buat worklist item dari order SIMRS |
| GET | `/api/v1/worklist/{id}` | Detail worklist item |
| PATCH | `/api/v1/worklist/{id}/status` | Update status (pending/in_progress/completed/cancelled) |
| DELETE | `/api/v1/worklist/{id}` | Hapus worklist item |
| GET | `/api/v1/modalities` | List registered modalities |
| GET | `/api/v1/audit` | Audit log |

## Inbound Parsers

| Format | Module | Deskripsi |
|--------|--------|-----------|
| HL7 v2 ORM^O01 | `lumi_dicom.inbound.hl7` | Parse HL7 v2 pipe-delimited messages |
| FHIR R4 | `lumi_dicom.inbound.fhir` | Map FHIR ServiceRequest/ImagingStudy ke worklist |

## Docker

```bash
# Build & run
docker-compose up -d

# View logs
docker-compose logs -f lumi-dicom

# Stop
docker-compose down
```

## Windows .exe (PyInstaller)

Executable one-file untuk Windows tanpa instalasi Python.
Definisi build ada di `lumi-dicom.spec` (lokal & CI memakai spec yang sama).

```bash
pip install -e ".[dev]"
pyinstaller lumi-dicom.spec          # hasil: dist\lumi-dicom.exe

dist\lumi-dicom.exe start --config config\default.yaml
```

- `schema.sql` dibundel otomatis ke dalam exe (via `datas` di spec).
- Override port dsb. via env var `LUMI_DICOM_*` bila tabrak server lain, contoh:
  `LUMI_DICOM_API__PORT=18770 LUMI_DICOM_MWL_SCP__PORT=31116`.
- Rilis otomatis: setiap tag `v*` membangun `lumi-dicom.exe` di CI
  (`windows-latest`) dan melampirkannya ke GitHub Release.

## Identitas Visual Lumi DICOM

Setiap file kode Python dalam project ini menggunakan:

- **Docstring header** dengan copyright Lumi DICOM
- **Import grouping** dengan comment separator ala Lumi DICOM
- **Konvensi naming** `snake_case` untuk fungsi/variabel, `PascalCase` untuk class
- **Konfigurasi** via environment variable prefix `LUMI_DICOM_`
- **Logging** dengan logger name `lumi-dicom`

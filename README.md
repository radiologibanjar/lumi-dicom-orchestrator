# Lumi DICOM Orchestrator

> **Lumi DICOM** — Orchestrator worklist radiologi. Menjembatani sistem rumah sakit
> (SIMRS / HIS) dengan modalitas pencitraan (CT, MR, US, DX, ...): order dari sistem
> apa pun diterima lewat REST API / HL7 v2 / FHIR R4, disimpan sebagai worklist,
> lalu disajikan ke modalitas lewat protokol standar **DICOM MWL C-FIND** —
> plus monitoring dashboard **realtime**.

---

## Lumi Ini Apa?

Di radiologi modern, **worklist** (daftar pemeriksaan yang menunggu) harus sampai ke
modalitas (CT/MR/US) tanpa ketik ulang. Standarnya adalah **DICOM Modality Worklist
(MWL)** — modalitas mengambil daftar tersebut lewat protokol C-FIND dari satu server.

Lumi DICOM adalah server tersebut, sekaligus jembatan datanya:

```
 SIMRS / HIS / aplikasi apa pun          Lumi DICOM              Modalitas
 ─────────────────────────────     ──────────────────────     ─────────────
 Order radiologi (REST/HL7/FHIR) ─▶ Worklist SQLite  ◀─C-FIND─ CT / MR / US
                                     (source of truth)
 Status pemeriksaan (MPPS)       ◀── Update otomatis  ◀─N-CREATE/N-SET─┘
                                     Dashboard web realtime (WebSocket)
```

**Intinya:** sistem Anda menulis order ke Lumi (sekali, lewat API yang umum),
seluruh modalitas di jaringan hospital information membaca worklist yang sama
lewat DICOM standar — tanpa integrasi per-modality, tanpa input manual.

- **Terima order** dari sumber apa pun: REST API (JSON), HL7 v2 ORM^O01, atau FHIR R4 ServiceRequest.
- **Menyajikan worklist** ke modalitas via DICOM MWL SCP (C-FIND) — standar, universal.
- **Menerima status pemeriksaan** dari modalitas via DICOM MPPS (N-CREATE/N-SET, opsional).
- **Monitoring realtime** lewat dashboard web: perubahan worklist muncul dalam hitungan detik.

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
┌──────────────┐     │                    ┌───────────────────────┐  │
│  Klien REST  │────▶│                    │    MWL SCP (C-FIND)   │  │
│ (connector,  │     │                    │   pynetdicom :11112  │  │
│  tester, dll)│     │                    └───────────┬───────────┘  │
└──────────────┘     │                                │              │
                     │                                ▼              │
                     │                    ┌───────────────────────┐  │
                     │                    │  Modalitas CT/MR/etc  │  │
                     │                    │  C-FIND MWL           │  │
                     │                    └───────────┬───────────┘  │
                     │                                │ N-CREATE/N-SET
                     │                    ┌───────────▼───────────┐  │
                     │                    │  MPPS SCP (opsional)  │  │
                     │                    │        :11113         │  │
                     │                    └───────────────────────┘  │
                     └──────────────────────────────────────────────┘
```

| Komponen | Peran |
|----------|-------|
| **Inbound API** | FastAPI REST — terima order (JSON/HL7/FHIR), validasi, normalisasi |
| **SQLite Worklist** | Buffer & source of truth lokal (WAL mode, aman concurrent) |
| **MWL SCP** | pynetdicom SCP — sajikan worklist ke modalitas via C-FIND |
| **MPPS SCP** | *(opsional)* Terima status pemeriksaan dari modalitas (N-CREATE/N-SET) |
| **Image Route** | *(opsional)* Route DICOM images antar AE |
| **Dashboard** | Web UI realtime (WebSocket push) untuk monitoring worklist |

## Alur Kerja

1. **Order masuk** — SIMRS/klien mengirim order radiologi ke Lumi:
   `POST /api/v1/worklist` (REST), `POST /api/v1/inbound/hl7` (HL7 v2 ORM),
   atau `POST /api/v1/inbound/fhir` (FHIR ServiceRequest).
   Item tersimpan dengan status `pending`.
2. **Modalitas mengambil worklist** — modalitas (CT/MR/US) dikonfigurasi untuk
   query MWL ke Lumi (`LUMI_DICOM:11112`). Setiap C-FIND mendapat item
   `pending`/`in_progress` sesuai filter tanggal & modality.
3. **Pemeriksaan berjalan** — saat modalitas memulai/menyelesaikan pemeriksaan,
   ia mengirim **MPPS** (bila diaktifkan): `N-CREATE` → status `in_progress`,
   `N-SET` (completed) → status `completed`. Update otomatis + ter-audit.
4. **Monitoring** — dashboard web (`http://<host>:8765/`) menampilkan worklist
   **realtime**: setiap perubahan dari penulis mana pun (API, MPPS, klien eksternal)
   muncul dalam ~1–3 detik via WebSocket.

## Fitur

- **REST API lengkap** — CRUD worklist, filter (tanggal, status, modality, station AE, patient), pagination, update status.
- **DICOM MWL SCP** — C-FIND standar; mendukung `CodeSequence` prosedur (multi-kode), allow-list AE Title modalitas, batas asosiasi/hasil.
- **DICOM MPPS SCP** — N-CREATE & N-SET (pending → in_progress → completed), teruji dengan integrasi jaringan nyata.
- **Inbound HL7 v2** — parse ORM^O01 pipe-delimited → worklist.
- **Inbound FHIR R4** — map ServiceRequest/ImagingStudy → worklist.
- **Dashboard web realtime** — WebSocket push (`/dashboard/ws`) + auto-refresh fallback; filter tanggal default hari ini; export CSV.
- **Audit log** — setiap perubahan status tercatat.
- **Autentikasi API key** — header `X-API-Key` untuk semua endpoint `/api/v1/*`; multi-key.
- **TLS opsional** — HTTPS dan enkripsi DICOM communication (sertifikat PEM).
- **Konfigurasi fleksibel** — YAML + override environment variable `LUMI_DICOM_*`.
- **Distribusi** — pip, Docker (GHCR), atau Windows `.exe` satu file (PyInstaller).

## Instalasi

### 1. pip (semua platform)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Docker

```bash
docker-compose up -d          # build & run
docker-compose logs -f lumi-dicom
docker-compose down
```

### 3. Windows .exe (tanpa Python)

Executable one-file; definisi build di `lumi-dicom.spec` (lokal & CI sama):

```bash
pip install -e ".[dev]"
pyinstaller lumi-dicom.spec          # hasil: dist\lumi-dicom.exe
dist\lumi-dicom.exe start --config config\default.yaml
```

- `schema.sql` dibundel otomatis ke dalam exe.
- Bila port tabrak, override via env: `LUMI_DICOM_API__PORT=18770 LUMI_DICOM_MWL_SCP__PORT=31116`.
- Setiap tag `v*` di CI membangun `lumi-dicom.exe` otomatis (`windows-latest`)
  dan melampirkannya ke GitHub Release.

## Menjalankan

```bash
lumi-dicom start --config config/default.yaml
# atau
python -m lumi_dicom start --config config/default.yaml
```

Layanan yang hidup: API + dashboard di `:8765`, MWL SCP di `:11112`,
MPPS SCP di `:11113` (saat `mpps.enabled: true`).

## Konfigurasi

File utama: `config/default.yaml`. Semua nilai bisa dioverride via environment
variable dengan prefix `LUMI_DICOM_` (kunci nested dengan `__`), contoh:
`LUMI_DICOM_API__PORT=18770`, `LUMI_DICOM_MWL_SCP__AE_TITLE=MYAE`.

| Layanan | Port default | AE Title | Keterangan |
|---------|--------------|----------|------------|
| API + Dashboard | 8765 | — | FastAPI; dashboard di `/` |
| MWL SCP | 11112 | `LUMI_DICOM` | C-FIND untuk modalitas (default aktif) |
| MPPS SCP | 11113 | `LUMI_MPPS` | N-CREATE/N-SET (default **nonaktif**) |
| Image Route | 11114 | `LUMI_ROUTE` | Routing gambar (default nonaktif) |

**API key** (wajib ganti di production) ada di `api.api_keys` pada `default.yaml`
(development: `lumi-dicom-dev-key`). Kirim sebagai header `X-API-Key`.

## Cara Mengintegrasikan Sistem Anda

### 1. REST API — kirim order (paling umum)

```bash
curl -X POST http://localhost:8765/api/v1/worklist \
  -H "X-API-Key: lumi-dicom-dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "accession_number": "R261000825",
    "patient_id": "452702",
    "patient_name": "Tn. Enceng Sunarya",
    "patient_birth_date": "19510712",
    "patient_sex": "M",
    "scheduled_procedure_step_start_date": "20261019",
    "modality": "CT",
    "procedure_description": "CT Thorax kontras",
    "source": "simrs"
  }'
```

Wajib: `accession_number`, `patient_id`, `patient_name`,
`scheduled_procedure_step_start_date` (YYYYMMDD atau YYYY-MM-DD), `modality`.
Sisanya opsional (`study_instance_uid` dibuat otomatis bila kosong).
Respons: `201` + objek worklist.

### 2. HL7 v2 ORM^O01

```bash
curl -X POST http://localhost:8765/api/v1/inbound/hl7 \
  -H "X-API-Key: lumi-dicom-dev-key" \
  -H "Content-Type: text/plain" \
  --data-binary @pesan_orm_o01.hl7
```

### 3. FHIR R4 ServiceRequest

```bash
curl -X POST http://localhost:8765/api/v1/inbound/fhir \
  -H "X-API-Key: lumi-dicom-dev-key" \
  -H "Content-Type: application/fhir+json" \
  -d @servicerequest.json
```

### 4. Modalitas (CT/MR/US) — koneksi DICOM

Di modality worklist settings modalitas, arahkan ke:

- **MWL Server host/IP**: alamat server Lumi, **port** `11112`
- **AE Title server**: `LUMI_DICOM` (sesuai `mwl_scp.ae_title`)

Modalitas akan C-FIND otomatis; item muncul sesuai tanggal pemeriksaan.
Untuk membatasi modalitas yang boleh query, isi `mwl_scp.allowed_aetitles`.

### 5. MPPS — status pemeriksaan (opsional)

Aktifkan `mpps.enabled: true` + restart. Modalitas dikonfigurasi mengirim
MPPS N-CREATE/N-SET ke `LUMI_MPPS:11113`. Status worklist ter-update otomatis:
`pending → in_progress → completed`.

### Contoh klien: Connector MediRad (tester)

> `scripts/medirad_connector.py` adalah **contoh klien / tester** yang menunjukkan
> cara sistem eksternal terhubung ke Lumi — **bukan bagian inti Lumi**.
> Ia berdiri sendiri: membaca order dari API MediRadi (SIMRS eksternal), lalu
> meneruskannya ke Lumi lewat `POST /api/v1/worklist` (cara yang sama seperti
> SIMRS Anda nanti).
>
> Berkas `config/medirad.env` berisi **kredensial klien tersebut** (token MediRad
> + URL Lumi + API key) dan **tidak dibagikan** ke repo. Template yang tersedia:
> `config/medirad.env.example`. Penggantian/rotasi token MediRad sepenuhnya
> tanggung jawab pemilik akun MediRad.

```bash
# Sekali jalan (tanggal hari ini)
python scripts/medirad_connector.py --once

# Loop terus-menerus (interval FETCH_INTERVAL_MINUTES, default 5 menit)
python scripts/medirad_connector.py --loop
```

Connector menyaring order tanpa `NoRadiologi` valid (tidak bisa jadi worklist)
dan mengisi fallback wajar untuk field kosong.

## Endpoints API

Semua `/api/v1/*` butuh header `X-API-Key` (kecuali dicatat lain).

| Method | Path | Deskripsi |
|--------|------|-----------|
| GET | `/health` | Health check (tanpa API key) |
| GET | `/` | Dashboard UI (tanpa API key) |
| GET | `/dashboard/api/worklist` | Feed worklist untuk dashboard (tanpa API key) |
| WS | `/dashboard/ws` | Realtime push — pesan `{"type":"refresh"}` saat data berubah |
| GET | `/docs` | Swagger UI / OpenAPI |
| GET | `/api/v1/worklist` | List worklist (filter: status, modality, station, tanggal, patient; limit/offset) |
| POST | `/api/v1/worklist` | Buat worklist item dari order |
| GET | `/api/v1/worklist/{id}` | Detail worklist item |
| PATCH | `/api/v1/worklist/{id}/status` | Update status (`pending`/`in_progress`/`completed`/`cancelled`) |
| DELETE | `/api/v1/worklist/{id}` | Hapus worklist item |
| POST | `/api/v1/inbound/hl7` | Terima HL7 v2 ORM^O01 → worklist |
| POST | `/api/v1/inbound/fhir` | Terima FHIR R4 ServiceRequest → worklist |
| GET | `/api/v1/modalities` | List registered modalities |
| GET | `/api/v1/audit` | Audit log |

## Dashboard Realtime

Buka `http://<host>:8765/` — tanpa login (read-only; API `/api/v1/*` tetap terproteksi).

- **Realtime**: WebSocket `/dashboard/ws`; server memantau perubahan worklist
  (~2 detik) dan mendorong refresh ke semua browser terbuka — mencakup perubahan
  dari API, MPPS, maupun klien eksternal yang menulis langsung.
- **Fallback**: auto-refresh 30 detik bila WebSocket putus (toggle di UI).
- Filter tanggal default = **hari ini**; tombol Reset juga mengisi hari ini.
- Ringkasan status, filter (tanggal/status/modality/station/patient), export CSV.

## Inbound Parsers

| Format | Module | Deskripsi |
|--------|--------|-----------|
| HL7 v2 ORM^O01 | `lumi_dicom.inbound.hl7` | Parse HL7 v2 pipe-delimited messages |
| FHIR R4 | `lumi_dicom.inbound.fhir` | Map FHIR ServiceRequest/ImagingStudy ke worklist |

## Keamanan

- **API key**: semua endpoint `/api/v1/*` wajib `X-API-Key`; daftar key di
  `api.api_keys` (multi-key memudahkan rotasi). **Ganti key dev di production.**
- **Dashboard** tidak butuh API key (monitoring lokal) — jangan exposal port
  `8765` ke jaringan publik tanpa proxy/auth tambahan.
- **DICOM allow-list**: `mwl_scp.allowed_aetitles` membatasi modalitas yang
  boleh query worklist.
- **TLS**: opsional untuk HTTPS API dan enkripsi DICOM (MWL/MPPS).
- **Kredensial pihak ketiga** (mis. token SIMRS/MediRad milik klien) tidak
  menjadi bagian repo — simpan di file env lokal (lihat `*.env.example`).
- **Audit log** mencatat setiap perubahan status worklist.

## Testing & Development

```bash
pip install -e ".[dev]"
pytest -q          # 29 test: unit + integrasi jaringan (MWL/MPPS/API/dashboard)
ruff check src/ tests/ scripts/
```

Test mencakup integrasi DICOM jaringan nyata (C-FIND & MPPS N-CREATE/N-SET
antar proses) dan validasi sintaks JS dashboard.

## CI/CD & Rilis

| Workflow | Trigger | Isi |
|----------|---------|-----|
| **CI** | push/PR ke `main` | Ruff + pytest (Python 3.12) |
| **Release** | tag `v*` | Docker image → GHCR + GitHub Release + `lumi-dicom.exe` (zip: exe + config + README) |

```bash
git tag v0.1.0 && git push origin v0.1.0   # memicu rilis penuh
```

## Identitas Visual Lumi DICOM

Setiap file kode Python dalam project ini menggunakan:

- **Docstring header** dengan copyright Lumi DICOM
- **Import grouping** dengan comment separator ala Lumi DICOM
- **Konvensi naming** `snake_case` untuk fungsi/variabel, `PascalCase` untuk class
- **Konfigurasi** via environment variable prefix `LUMI_DICOM_`
- **Logging** dengan logger name `lumi-dicom`

© 2026 Lumi DICOM. All rights reserved.

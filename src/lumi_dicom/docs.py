"""
Lumi DICOM — API Documentation
Copyright © 2026 Lumi DICOM. All rights reserved.

Full API documentation sebagai HTML page di /docs.
"""

from fastapi.responses import HTMLResponse

DOCS_HTML = """\
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lumi DICOM — API Documentation</title>
    <style>
        :root {
            --lumi-bg: #0a0e17;
            --lumi-card: #111827;
            --lumi-border: #1f2937;
            --lumi-text: #e5e7eb;
            --lumi-muted: #9ca3af;
            --lumi-accent: #6366f1;
            --lumi-success: #10b981;
            --lumi-warning: #f59e0b;
            --lumi-error: #ef4444;
            --lumi-info: #3b82f6;
            --lumi-code-bg: #1e293b;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--lumi-bg);
            color: var(--lumi-text);
            line-height: 1.6;
        }
        .lumi-header {
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
            padding: 1.5rem 2rem;
            border-bottom: 1px solid var(--lumi-border);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .lumi-header h1 { font-size: 1.5rem; color: #fff; }
        .lumi-header h1 span { color: var(--lumi-accent); }
        .lumi-header p { color: var(--lumi-muted); font-size: 0.875rem; margin-top: 0.25rem; }
        .lumi-nav {
            background: var(--lumi-card);
            border-bottom: 1px solid var(--lumi-border);
            padding: 0.75rem 2rem;
            display: flex;
            gap: 1.5rem;
            font-size: 0.875rem;
        }
        .lumi-nav a { color: var(--lumi-muted); text-decoration: none; }
        .lumi-nav a:hover { color: var(--lumi-accent); }
        .lumi-container { max-width: 1000px; margin: 0 auto; padding: 2rem; }
        .lumi-section { margin-bottom: 2.5rem; }
        .lumi-section h2 {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--lumi-border);
        }
        .lumi-section h3 {
            font-size: 1rem;
            font-weight: 600;
            margin: 1.25rem 0 0.5rem;
            color: var(--lumi-accent);
        }
        .lumi-card {
            background: var(--lumi-card);
            border: 1px solid var(--lumi-border);
            border-radius: 8px;
            padding: 1.25rem;
            margin-bottom: 1rem;
        }
        .lumi-card h4 { font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem; }
        .lumi-card p { color: var(--lumi-muted); font-size: 0.875rem; }
        .lumi-endpoint {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            background: var(--lumi-card);
            border: 1px solid var(--lumi-border);
            border-radius: 6px;
            margin-bottom: 0.5rem;
        }
        .lumi-method {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            min-width: 60px;
            text-align: center;
        }
        .lumi-method.get { background: rgba(59,130,246,0.15); color: var(--lumi-info); }
        .lumi-method.post { background: rgba(16,185,129,0.15); color: var(--lumi-success); }
        .lumi-method.patch { background: rgba(245,158,11,0.15); color: var(--lumi-warning); }
        .lumi-method.delete { background: rgba(239,68,68,0.15); color: var(--lumi-error); }
        .lumi-path { font-family: 'Consolas', monospace; font-size: 0.875rem; }
        .lumi-desc { color: var(--lumi-muted); font-size: 0.8rem; margin-left: auto; }
        .lumi-code {
            background: var(--lumi-code-bg);
            border: 1px solid var(--lumi-border);
            border-radius: 6px;
            padding: 1rem;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.8rem;
            overflow-x: auto;
            margin: 0.5rem 0;
            white-space: pre-wrap;
            word-break: break-all;
        }
        .lumi-code .key { color: #93c5fd; }
        .lumi-code .str { color: #86efac; }
        .lumi-code .num { color: #fca5a5; }
        .lumi-code .bool { color: #fcd34d; }
        .lumi-code .null { color: #9ca3af; }
        .lumi-badge {
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 500;
        }
        .lumi-badge.required { background: rgba(239,68,68,0.15); color: var(--lumi-error); }
        .lumi-badge.optional { background: rgba(107,114,128,0.15); color: var(--lumi-muted); }
        .lumi-badge.header { background: rgba(99,102,241,0.15); color: var(--lumi-accent); }
        .lumi-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
        .lumi-table th, .lumi-table td {
            padding: 0.5rem 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--lumi-border);
        }
        .lumi-table th { color: var(--lumi-muted); font-weight: 500; }
        .lumi-table td { color: var(--lumi-text); }
        .lumi-note {
            background: rgba(99,102,241,0.08);
            border-left: 3px solid var(--lumi-accent);
            padding: 0.75rem 1rem;
            border-radius: 0 6px 6px 0;
            margin: 0.75rem 0;
            font-size: 0.85rem;
        }
        .lumi-note.warning { border-left-color: var(--lumi-warning); background: rgba(245,158,11,0.08); }
        .lumi-note.success { border-left-color: var(--lumi-success); background: rgba(16,185,129,0.08); }
        .lumi-footer {
            text-align: center;
            padding: 2rem;
            color: var(--lumi-muted);
            font-size: 0.75rem;
            border-top: 1px solid var(--lumi-border);
        }
        .lumi-tabs { display: flex; gap: 0.5rem; margin-bottom: 1rem; flex-wrap: wrap; }
        .lumi-tab {
            padding: 0.4rem 1rem;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
            border: 1px solid var(--lumi-border);
            background: var(--lumi-card);
            color: var(--lumi-muted);
        }
        .lumi-tab.active { background: var(--lumi-accent); color: #fff; border-color: var(--lumi-accent); }
        .lumi-tab-content { display: none; }
        .lumi-tab-content.active { display: block; }
    </style>
</head>
<body>
    <div class="lumi-header">
        <h1>Lumi <span>DICOM</span> — API Documentation</h1>
        <p>Orchestrator DICOM radiologi: menerima order dari SIMRS, menyimpan di SQLite, sajikan ke modalitas via DICOM MWL C-FIND.</p>
    </div>

    <div class="lumi-nav">
        <a href="/">← Dashboard</a>
        <a href="/docs">Documentation</a>
        <a href="/health">Health Check</a>
        <a href="/openapi.json">OpenAPI (JSON)</a>
    </div>

    <div class="lumi-container">

        <!-- ═══ Overview ═══ -->
        <div class="lumi-section">
            <h2>Overview</h2>
            <div class="lumi-card">
                <p><strong>Lumi DICOM Orchestrator</strong> adalah sistem pengatur alur DICOM di radiologi. Menerima order dari SIMRS via REST API (FHIR/HL7), menyimpan di SQLite, dan menyajikan ke modalitas (CT/MR/USG) lewat DICOM MWL C-FIND.</p>
            </div>
            <div class="lumi-card">
                <h4>Base URL</h4>
                <div class="lumi-code">http://localhost:8765</div>
            </div>
            <div class="lumi-card">
                <h4>DICOM MWL SCP</h4>
                <div class="lumi-code">AE Title: LUMI_DICOM
Host: 127.0.0.1
Port: 11112</div>
            </div>
        </div>

        <!-- ═══ Authentication ═══ -->
        <div class="lumi-section">
            <h2>Authentication</h2>
            <div class="lumi-note warning">
                <strong>Semua endpoint /api/v1/*</strong> memerlukan API key. Gunakan header:
                <div class="lumi-code">X-API-Key: lumi-dicom-dev-key</div>
            </div>
            <div class="lumi-card">
                <h4>Default API Key (development)</h4>
                <div class="lumi-code">lumi-dicom-dev-key</div>
                <p>Untuk production, ubah di <code>config/default.yaml</code> → <code>api.api_keys</code></p>
            </div>
            <div class="lumi-card">
                <h4>Contoh Request</h4>
                <div class="lumi-code">curl -H "X-API-Key: lumi-dicom-dev-key" \\
  http://localhost:8765/api/v1/worklist</div>
            </div>
        </div>

        <!-- ═══ Endpoints ═══ -->
        <div class="lumi-section">
            <h2>Endpoints</h2>

            <!-- Health -->
            <h3>System</h3>
            <div class="lumi-endpoint">
                <span class="lumi-method get">GET</span>
                <span class="lumi-path">/health</span>
                <span class="lumi-desc">Health check (no auth)</span>
            </div>
            <div class="lumi-code">Response:
{
  "status": "ok",
  "service": "lumi-dicom",
  "brand": "Lumi DICOM",
  "timestamp": "2026-10-18T11:19:36.449904"
}</div>

            <!-- Worklist -->
            <h3>Worklist</h3>
            <div class="lumi-endpoint">
                <span class="lumi-method get">GET</span>
                <span class="lumi-path">/api/v1/worklist</span>
                <span class="lumi-desc">List worklist (with filters)</span>
            </div>
            <div class="lumi-card">
                <h4>Query Parameters</h4>
                <table class="lumi-table">
                    <tr><th>Param</th><th>Type</th><th>Deskripsi</th></tr>
                    <tr><td>status</td><td>string</td><td>Filter: pending, in_progress, completed, cancelled</td></tr>
                    <tr><td>modality</td><td>string</td><td>Filter: CT, MR, US, DX, dll</td></tr>
                    <tr><td>station</td><td>string</td><td>Filter by ScheduledStationAETitle</td></tr>
                    <tr><td>date_from</td><td>string</td><td>Filter tanggal mulai (YYYYMMDD)</td></tr>
                    <tr><td>date_to</td><td>string</td><td>Filter tanggal akhir (YYYYMMDD)</td></tr>
                    <tr><td>patient_id</td><td>string</td><td>Filter by PatientID</td></tr>
                    <tr><td>limit</td><td>int</td><td>Max results (default 100, max 1000)</td></tr>
                    <tr><td>offset</td><td>int</td><td>Pagination offset</td></tr>
                </table>
            </div>
            <div class="lumi-code">Contoh:
curl -H "X-API-Key: lumi-dicom-dev-key" \\
  "http://localhost:8765/api/v1/worklist?status=pending&modality=CT"</div>

            <div class="lumi-endpoint">
                <span class="lumi-method post">POST</span>
                <span class="lumi-path">/api/v1/worklist</span>
                <span class="lumi-desc">Buat worklist item (dari SIMRS)</span>
            </div>
            <div class="lumi-card">
                <h4>Request Body</h4>
                <table class="lumi-table">
                    <tr><th>Field</th><th>Type</th><th>Required</th><th>Deskripsi</th></tr>
                    <tr><td>accession_number</td><td>string</td><td><span class="lumi-badge required">Wajib</span></td><td>Accession Number (unik)</td></tr>
                    <tr><td>patient_id</td><td>string</td><td><span class="lumi-badge required">Wajib</span></td><td>Patient ID</td></tr>
                    <tr><td>patient_name</td><td>string</td><td><span class="lumi-badge required">Wajib</span></td><td>Patient Name (format: Family^Given)</td></tr>
                    <tr><td>scheduled_procedure_step_start_date</td><td>string</td><td><span class="lumi-badge required">Wajib</span></td><td>Tanggal (YYYYMMDD atau YYYY-MM-DD)</td></tr>
                    <tr><td>modality</td><td>string</td><td><span class="lumi-badge required">Wajib</span></td><td>Modalitas: CT, MR, US, DX, dll</td></tr>
                    <tr><td>source_id</td><td>string</td><td><span class="lumi-badge optional">Opsional</span></td><td>ID unik dari SIMRS (untuk idempotency)</td></tr>
                    <tr><td>study_instance_uid</td><td>string</td><td><span class="lumi-badge optional">Opsional</span></td><td>Study Instance UID (auto-generate jika kosong)</td></tr>
                    <tr><td>patient_birth_date</td><td>string</td><td><span class="lumi-badge optional">Opsional</span></td><td>Tanggal lahir (YYYYMMDD)</td></tr>
                    <tr><td>patient_sex</td><td>string</td><td><span class="lumi-badge optional">Opsional</span></td><td>M/F/O</td></tr>
                    <tr><td>scheduled_procedure_step_start_time</td><td>string</td><td><span class="lumi-badge optional">Opsional</span></td><td>Jam (HHMMSS)</td></tr>
                    <tr><td>scheduled_station_aetitle</td><td>string</td><td><span class="lumi-badge optional">Opsional</span></td><td>AE Title modalitas tujuan</td></tr>
                    <tr><td>procedure_code</td><td>string</td><td><span class="lumi-badge optional">Opsional</span></td><td>Kode prosedur</td></tr>
                    <tr><td>procedure_description</td><td>string</td><td><span class="lumi-badge optional">Opsional</span></td><td>Deskripsi prosedur</td></tr>
                    <tr><td>referring_physician_name</td><td>string</td><td><span class="lumi-badge optional">Opsional</span></td><td>Dokter perujuk</td></tr>
                    <tr><td>source</td><td>string</td><td><span class="lumi-badge optional">Opsional</span></td><td>Default: "simrs"</td></tr>
                </table>
            </div>
            <div class="lumi-code">Contoh:
curl -X POST http://localhost:8765/api/v1/worklist \\
  -H "X-API-Key: lumi-dicom-dev-key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "accession_number": "ACC-2026-0001",
    "patient_id": "P001",
    "patient_name": "Santoso^Dewi",
    "patient_birth_date": "1985-03-15",
    "patient_sex": "F",
    "scheduled_procedure_step_start_date": "2026-10-18",
    "scheduled_procedure_step_start_time": "083000",
    "modality": "CT",
    "scheduled_station_aetitle": "CT01",
    "procedure_description": "CT Abdomen contrast",
    "referring_physician_name": "dr. Andi^Wijaya",
    "source": "simrs"
  }'</div>

            <div class="lumi-endpoint">
                <span class="lumi-method get">GET</span>
                <span class="lumi-path">/api/v1/worklist/{id}</span>
                <span class="lumi-desc">Detail worklist item</span>
            </div>

            <div class="lumi-endpoint">
                <span class="lumi-method patch">PATCH</span>
                <span class="lumi-path">/api/v1/worklist/{id}/status</span>
                <span class="lumi-desc">Update status</span>
            </div>
            <div class="lumi-code">Contoh:
curl -X PATCH http://localhost:8765/api/v1/worklist/1/status \\
  -H "X-API-Key: lumi-dicom-dev-key" \\
  -H "Content-Type: application/json" \\
  -d '{"status": "completed"}'</div>

            <div class="lumi-endpoint">
                <span class="lumi-method delete">DELETE</span>
                <span class="lumi-path">/api/v1/worklist/{id}</span>
                <span class="lumi-desc">Hapus worklist item</span>
            </div>

            <!-- Inbound -->
            <h3>Inbound Parsers</h3>
            <div class="lumi-endpoint">
                <span class="lumi-method post">POST</span>
                <span class="lumi-path">/api/v1/inbound/hl7</span>
                <span class="lumi-desc">Parse HL7 v2 ORM^O01 message</span>
            </div>
            <div class="lumi-card">
                <h4>Request</h4>
                <p>Content-Type: <code>text/plain</code> — body berisi raw HL7 message</p>
            </div>
            <div class="lumi-code">Contoh:
curl -X POST http://localhost:8765/api/v1/inbound/hl7 \\
  -H "X-API-Key: lumi-dicom-dev-key" \\
  -H "Content-Type: text/plain" \\
  -d 'MSH|^~&|SIMRS|LUMI|HIS|20261018083000||ORM^O01|MSG002|P|2.5
PID|1||P002||Wijaya^Budi||19781120|M
ORC|NW|ORD002|ACC002
OBR|1|ORD002|ACC002|MR_BRAIN^MRI Brain^MR|||20261018100000|||||||||dr. Sari^Putri'</div>

            <div class="lumi-endpoint">
                <span class="lumi-method post">POST</span>
                <span class="lumi-path">/api/v1/inbound/fhir</span>
                <span class="lumi-desc">Map FHIR R4 ServiceRequest/ImagingStudy</span>
            </div>
            <div class="lumi-card">
                <h4>Request</h4>
                <p>Content-Type: <code>application/json</code> — body berisi FHIR R4 JSON</p>
            </div>
            <div class="lumi-code">Contoh:
curl -X POST http://localhost:8765/api/v1/inbound/fhir \\
  -H "X-API-Key: lumi-dicom-dev-key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "resourceType": "ServiceRequest",
    "id": "sr-003",
    "status": "active",
    "intent": "order",
    "subject": {"reference": "Patient/P003"},
    "code": {"coding": [{"code": "US_ABD", "display": "USG Abdomen"}]},
    "occurrenceDateTime": "2026-10-18T11:00:00+07:00",
    "requester": {"display": "dr. Rina^Kusuma"},
    "identifier": [{"value": "ACC-2026-0003"}]
  }'</div>

            <div class="lumi-endpoint">
                <span class="lumi-method get">GET</span>
                <span class="lumi-path">/api/v1/inbound/health</span>
                <span class="lumi-desc">Inbound module health check</span>
            </div>

            <!-- Modalities -->
            <h3>Modalities</h3>
            <div class="lumi-endpoint">
                <span class="lumi-method get">GET</span>
                <span class="lumi-path">/api/v1/modalities</span>
                <span class="lumi-desc">List registered modalities</span>
            </div>

            <!-- Audit -->
            <h3>Audit</h3>
            <div class="lumi-endpoint">
                <span class="lumi-method get">GET</span>
                <span class="lumi-path">/api/v1/audit</span>
                <span class="lumi-desc">Audit log</span>
            </div>
            <div class="lumi-code">Query params: action (string), limit (int, default 50)</div>
        </div>

        <!-- ═══ MediRad (SIMRS Bridge) ═══ -->
        <div class="lumi-section">
            <h2>MediRad — SIMRS Bridge</h2>
            <div class="lumi-card">
                <h4>Web Service RSU Kota Banjar</h4>
                <p>MediRad menjembatani SIMRS ke PACS. Endpoint untuk order radiologi:</p>
                <div class="lumi-code">Base URL: http://172.16.2.2/BridgingRadiologi

# Alur autentikasi:
1. GET /gettoken?username=xxx&password=xxx →  dapat x-token
2. POST /getorderrad  (header: x-token, body: tglAwal, tglAkhir, noCM?, nama?, noRadiology?)
   →  List Order Radiologi

# Endpoint lain:
   POST /gethasilpemeriksaan   → List hasil pemeriksaan
   GET  /gettindakanrad         → Daftar nama tindakan radiologi
   POST /getruanganinstalasi   → Daftar ruangan rajal/ranap/IGD
   GET  /getpasien             → Data pasien
   POST /simpanhasilpemeriksaan → Simpan hasil ke SIMRS</div>
            </div>
            <div class="lumi-card">
                <h4>Connector Otomatis</h4>
                <p>Script <code>scripts/medirad_connector.py</code> fetch order dari MediRad dan forward ke Lumi DICOM:</p>
                <div class="lumi-code">cd C:\\Users\\hntin\\Desktop\\lumi-dicom-orchestrator
.venv\\Scripts\\python scripts\\medirad_connector.py                    # sekali fetch
.venv\\Scripts\\python scripts\\medirad_connector.py --loop             # periodic (5 menit)
.venv\\Scripts\\python scripts\\medirad_connector.py \\
    --start-date 2026-10-01 --end-date 2026-10-19</div>
            </div>
        </div>

        <!-- ═══ Konfigurasi Modalitas ═══ -->
        <div class="lumi-section">
            <h2>Konfigurasi Modalitas</h2>
            <div class="lumi-note">
                <strong>Untuk vendor/teknik modalitas:</strong> Lumi DICOM menerima koneksi C-ECHO (verification) dan C-FIND (modality worklist) dari perangkat imaging.
            </div>
            <div class="lumi-card">
                <h4>Parameter Koneksi</h4>
                <table class="lumi-table">
                    <tr><th>Parameter</th><th>Nilai</th><th>Keterangan</th></tr>
                    <tr><td>SCP IP Address</td><td><code>172.16.8.60</code></td><td>IP host Lumi DICOM (yes — gunakan IP LAN host, bukan 127.0.0.1)</td></tr>
                    <tr><td>SCP Port</td><td><code>11112</code></td><td>Port DICOM MWL SCP</td></tr>
                    <tr><td>SCP AE Title</td><td><code>LUMI_DICOM</code></td><td>AE Title Lumi DICOM (case-sensitive)</td></tr>
                    <tr><td>Modalitas AE Title</td><td><code>RADMAX</code></td><td>AE Title perangkat</td></tr>
                    <tr><td>Protocol</td><td>DICOM DIMSE (non-TLS)</td><td>Pastikan non-TLS jika SCP belum pakai TLS</td></tr>
                    <tr><td>Called AE</td><td><code>LUMI_DICOM</code></td><td>Saat connect, gunakan sebagai Called AE Title</td></tr>
                    <tr><td>Calling AE</td><td><code>RADMAX</code></td><td>AE Title perangkat sebagai Calling AE</td></tr>
                </table>
            </div>
            <div class="lumi-card">
                <h4>Langkah Verifikasi C-ECHO</h4>
                <ol style="color: var(--lumi-muted); font-size: 0.875rem; padding-left: 1.2rem;">
                    <li>Pastikan modalitas sudah di-add di Lumi DICOM via <code>POST /api/v1/modalities</code> (atau via dashboard).</li>
                    <li>Isi parameter SCP di modalitas: IP <code>172.16.8.60</code>, Port <code>11112</code>, AE Title <code>LUMI_DICOM</code>.</li>
                    <li>Jalankan <strong>C-ECHO</strong> (verification test) dari modalitas.</li>
                    <li>Harusnya dapat status <strong>"Success" / 0x0000</strong>.</li>
                </ol>
            </div>
            <div class="lumi-card">
                <h4>Langkah Query MWL (C-FIND)</h4>
                <ol style="color: var(--lumi-muted); font-size: 0.875rem; padding-left: 1.2rem;">
                    <li>Pastikan ada worklist item untuk tanggal/modalitas yang diquery.</li>
                    <li>Isi parameter query di modalitas (PatientID, AccessionNumber, Modality, dll).</li>
                    <li>Kosongkan field untuk wildcard (match any).</li>
                    <li>Jalankan <strong>C-FIND</strong> — modalitas harusnya menerima list worklist.</li>
                </ol>
            </div>
            <div class="lumi-note warning">
                <strong>Troubleshooting:</strong> Jika C-ECHO gagal, pastikan:
                <ul style="margin-top: 0.5rem; padding-left: 1.2rem;">
                    <li>IP host Lumi DICOM yang diisi modalitas adalah <code>172.16.8.60</code> (bukan 127.0.0.1).</li>
                    <li>Port 11112 tidak di-blok firewall.</li>
                    <li>AE Title Lumi DICOM persis <code>LUMI_DICOM</code> (case-sensitive).</li>
                </ul>
            </div>
        </div>

        <!-- ═══ DICOM MWL SCP ═══ -->
        <div class="lumi-section">
            <h2>DICOM MWL SCP</h2>
            <div class="lumi-card">
                <h4>Konfigurasi DICOM</h4>
                <table class="lumi-table">
                    <tr><th>Parameter</th><th>Nilai</th></tr>
                    <tr><td>AE Title</td><td>LUMI_DICOM</td></tr>
                    <tr><td>Host</td><td>127.0.0.1</td></tr>
                    <tr><td>Port</td><td>11112</td></tr>
                    <tr><td>SOP Class</td><td>Modality Worklist Information Find</td></tr>
                    <tr><td>Query/Retrieve Level</td><td>WORKLIST</td></tr>
                </table>
            </div>
            <div class="lumi-card">
                <h4>Filter yang didukung modalitas</h4>
                <table class="lumi-table">
                    <tr><th>DICOM Tag</th><th>Keyword</th><th>Deskripsi</th></tr>
                    <tr><td>(0010,0020)</td><td>PatientID</td><td>Filter by Patient ID</td></tr>
                    <tr><td>(0010,0010)</td><td>PatientName</td><td>Filter by Patient Name (wildcard)</td></tr>
                    <tr><td>(0008,0050)</td><td>AccessionNumber</td><td>Filter by Accession Number</td></tr>
                    <tr><td>(0008,0060)</td><td>Modality</td><td>Filter by Modality (CT, MR, dll)</td></tr>
                    <tr><td>(0040,0002)</td><td>ScheduledProcedureStepStartDate</td><td>Filter by date (YYYYMMDD atau range)</td></tr>
                    <tr><td>(0040,0001)</td><td>ScheduledStationAETitle</td><td>Filter by Station AE Title</td></tr>
                </table>
            </div>
            <div class="lumi-note">
                <strong>Catatan:</strong> Modalitas mengirim C-FIND query ke <code>127.0.0.1:11112</code> dengan AE Title <code>LUMI_DICOM</code>. Kosongkan field untuk wildcard (match any).
            </div>
        </div>

        <!-- ═══ Status Workflow ═══ -->
        <div class="lumi-section">
            <h2>Status Workflow</h2>
            <div class="lumi-card">
                <table class="lumi-table">
                    <tr><th>Status</th><th>Deskripsi</th></tr>
                    <tr><td><code>pending</code></td><td>Order diterima, menunggu di-scan</td></tr>
                    <tr><td><code>in_progress</code></td><td>Sedang di-scan (MPPS IN PROGRESS)</td></tr>
                    <tr><td><code>completed</code></td><td>Scan selesai (MPPS COMPLETED)</td></tr>
                    <tr><td><code>cancelled</code></td><td>Order dibatalkan</td></tr>
                </table>
            </div>
        </div>

        <!-- ═══ Error Codes ═══ -->
        <div class="lumi-section">
            <h2>Error Codes</h2>
            <div class="lumi-card">
                <table class="lumi-table">
                    <tr><th>HTTP</th><th>Deskripsi</th></tr>
                    <tr><td>200</td><td>OK</td></tr>
                    <tr><td>201</td><td>Created</td></tr>
                    <tr><td>400</td><td>Bad Request — parameter tidak valid</td></tr>
                    <tr><td>401</td><td>Unauthorized — API key tidak ada/invalid</td></tr>
                    <tr><td>404</td><td>Not Found — resource tidak ditemukan</td></tr>
                    <tr><td>422</td><td>Validation Error — field tidak valid</td></tr>
                    <tr><td>500</td><td>Internal Server Error</td></tr>
                </table>
            </div>
        </div>

    </div>

    <div class="lumi-footer">
        Lumi DICOM Orchestrator — Copyright © 2026 Lumi DICOM. All rights reserved.
    </div>
</body>
</html>
"""


def create_docs_router():
    """Create FastAPI router for /docs endpoint."""
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/docs", response_class=HTMLResponse, tags=["docs"])
    def docs():
        """Lumi DICOM API Documentation."""
        return DOCS_HTML

    return router

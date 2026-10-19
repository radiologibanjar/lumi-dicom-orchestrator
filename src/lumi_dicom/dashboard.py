"""
Lumi DICOM — Web UI Dashboard
Copyright © 2026 Lumi DICOM. All rights reserved.

Lightweight HTML dashboard untuk monitoring Lumi DICOM Orchestrator worklist.
"""

import asyncio
import logging

from fastapi.responses import HTMLResponse

logger = logging.getLogger("lumi-dicom")

# ─── Dashboard HTML Template ─────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lumi DICOM — Dashboard</title>
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
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--lumi-bg);
            color: var(--lumi-text);
            min-height: 100vh;
        }

        /* Header */
        .lumi-header {
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
            padding: 1rem 2rem;
            border-bottom: 1px solid var(--lumi-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.75rem;
        }

        .lumi-brand {
            font-size: 1.5rem;
            font-weight: 700;
            color: #fff;
            letter-spacing: -0.5px;
        }

        .lumi-brand span {
            color: var(--lumi-accent);
        }

        .lumi-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            color: var(--lumi-muted);
        }

        .lumi-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--lumi-success);
            animation: pulse 2s infinite;
            flex-shrink: 0;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        /* Main */
        .lumi-main {
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }

        /* Stats Grid */
        .lumi-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .lumi-stat-card {
            background: var(--lumi-card);
            border: 1px solid var(--lumi-border);
            border-radius: 12px;
            padding: 1.25rem;
            cursor: pointer;
            transition: border-color 0.2s, transform 0.15s, box-shadow 0.2s;
            user-select: none;
        }

        .lumi-stat-card:hover {
            border-color: var(--lumi-accent);
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.15);
        }

        .lumi-stat-card.active {
            border-color: var(--lumi-accent);
            background: rgba(99, 102, 241, 0.12);
            box-shadow: 0 0 0 1px var(--lumi-accent) inset;
        }

        .lumi-stat-card .label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--lumi-muted);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .lumi-stat-card .label .hint {
            font-size: 0.625rem;
            color: var(--lumi-accent);
            text-transform: none;
            letter-spacing: 0;
            opacity: 0;
            transition: opacity 0.2s;
        }

        .lumi-stat-card:hover .label .hint,
        .lumi-stat-card.active .label .hint { opacity: 1; }

        .lumi-stat-card .value {
            font-size: 2rem;
            font-weight: 700;
        }

        .lumi-stat-card.pending .value { color: var(--lumi-warning); }
        .lumi-stat-card.in_progress .value { color: var(--lumi-info); }
        .lumi-stat-card.completed .value { color: var(--lumi-success); }
        .lumi-stat-card.cancelled .value { color: var(--lumi-error); }

        /* Filter Bar */
        .lumi-filter-bar {
            background: var(--lumi-card);
            border: 1px solid var(--lumi-border);
            border-radius: 12px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            display: flex;
            flex-wrap: wrap;
            align-items: flex-end;
            gap: 0.75rem;
        }

        .lumi-field {
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
        }

        .lumi-field label {
            font-size: 0.6875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--lumi-muted);
        }

        .lumi-input, .lumi-select {
            background: var(--lumi-bg);
            border: 1px solid var(--lumi-border);
            border-radius: 8px;
            padding: 0.5rem 0.75rem;
            color: var(--lumi-text);
            font-size: 0.875rem;
            font-family: inherit;
            transition: border-color 0.2s;
            color-scheme: dark;
        }

        .lumi-input:focus, .lumi-select:focus {
            outline: none;
            border-color: var(--lumi-accent);
        }

        .lumi-input::placeholder { color: var(--lumi-muted); }

        .lumi-filter-actions {
            display: flex;
            gap: 0.5rem;
            margin-left: auto;
            flex-wrap: wrap;
        }

        .lumi-btn {
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: opacity 0.2s, background 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 0.4rem;
        }

        .lumi-btn:hover { opacity: 0.9; }
        .lumi-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .lumi-btn-primary { background: var(--lumi-accent); color: #fff; }
        .lumi-btn-ghost {
            background: transparent;
            color: var(--lumi-muted);
            border: 1px solid var(--lumi-border);
        }
        .lumi-btn-ghost:hover { border-color: var(--lumi-accent); color: var(--lumi-accent); opacity: 1; }

        .lumi-btn-export { background: var(--lumi-success); color: #fff; }

        /* Auto-refresh toggle */
        .lumi-toggle {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.8125rem;
            color: var(--lumi-muted);
            cursor: pointer;
            user-select: none;
            padding: 0.5rem 0.75rem;
            border: 1px solid var(--lumi-border);
            border-radius: 8px;
            background: var(--lumi-bg);
        }

        .lumi-toggle input { display: none; }

        .lumi-toggle .track {
            width: 32px;
            height: 18px;
            border-radius: 9999px;
            background: var(--lumi-border);
            position: relative;
            transition: background 0.2s;
            flex-shrink: 0;
        }

        .lumi-toggle .track::after {
            content: '';
            position: absolute;
            top: 2px;
            left: 2px;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #fff;
            transition: transform 0.2s;
        }

        .lumi-toggle input:checked + .track { background: var(--lumi-success); }
        .lumi-toggle input:checked + .track::after { transform: translateX(14px); }

        /* Quick status filters */
        .lumi-filters {
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }

        .lumi-filter {
            background: var(--lumi-card);
            border: 1px solid var(--lumi-border);
            border-radius: 8px;
            padding: 0.5rem 1rem;
            color: var(--lumi-text);
            font-size: 0.875rem;
            font-family: inherit;
            cursor: pointer;
            transition: border-color 0.2s;
        }

        .lumi-filter:hover, .lumi-filter.active {
            border-color: var(--lumi-accent);
        }

        .lumi-filter.active {
            background: rgba(99, 102, 241, 0.15);
            color: var(--lumi-accent);
        }

        /* Table */
        .lumi-table-container {
            background: var(--lumi-card);
            border: 1px solid var(--lumi-border);
            border-radius: 12px;
            overflow: hidden;
        }

        .lumi-table-scroll { overflow-x: auto; }

        .lumi-table-header {
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--lumi-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .lumi-table-header h2 {
            font-size: 1.125rem;
            font-weight: 600;
        }

        .lumi-table-header .count {
            font-size: 0.8125rem;
            color: var(--lumi-muted);
            font-weight: 400;
            margin-left: 0.5rem;
        }

        .lumi-table-actions {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .lumi-refresh-btn {
            background: var(--lumi-accent);
            color: #fff;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            font-family: inherit;
            transition: opacity 0.2s;
        }

        .lumi-refresh-btn:hover { opacity: 0.9; }
        .lumi-refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .lumi-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
            min-width: 860px;
        }

        .lumi-table th {
            text-align: left;
            padding: 0.75rem 1rem;
            color: var(--lumi-muted);
            font-weight: 500;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--lumi-border);
            white-space: nowrap;
        }

        .lumi-table td {
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--lumi-border);
        }

        .lumi-table tbody tr { cursor: pointer; transition: background 0.15s; }
        .lumi-table tbody tr:hover td { background: rgba(99, 102, 241, 0.05); }
        .lumi-table tr:last-child td { border-bottom: none; }

        /* Status Badge */
        .lumi-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
            white-space: nowrap;
        }

        .lumi-badge.pending { background: rgba(245, 158, 11, 0.15); color: var(--lumi-warning); }
        .lumi-badge.in_progress { background: rgba(59, 130, 246, 0.15); color: var(--lumi-info); }
        .lumi-badge.completed { background: rgba(16, 185, 129, 0.15); color: var(--lumi-success); }
        .lumi-badge.cancelled { background: rgba(239, 68, 68, 0.15); color: var(--lumi-error); }

        /* Empty State */
        .lumi-empty {
            text-align: center;
            padding: 3rem;
            color: var(--lumi-muted);
        }

        /* Detail Modal */
        .lumi-modal-backdrop {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.65);
            z-index: 100;
            align-items: center;
            justify-content: center;
            padding: 1rem;
            backdrop-filter: blur(2px);
        }

        .lumi-modal-backdrop.open { display: flex; }

        .lumi-modal {
            background: var(--lumi-card);
            border: 1px solid var(--lumi-border);
            border-radius: 16px;
            width: 100%;
            max-width: 640px;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            animation: lumi-modal-in 0.2s ease-out;
        }

        @keyframes lumi-modal-in {
            from { opacity: 0; transform: translateY(12px) scale(0.98); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        .lumi-modal-header {
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--lumi-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
        }

        .lumi-modal-header h3 {
            font-size: 1.125rem;
            font-weight: 600;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .lumi-modal-close {
            background: transparent;
            border: none;
            color: var(--lumi-muted);
            font-size: 1.5rem;
            line-height: 1;
            cursor: pointer;
            padding: 0.25rem;
            border-radius: 6px;
            flex-shrink: 0;
            transition: color 0.2s, background 0.2s;
        }

        .lumi-modal-close:hover { color: #fff; background: rgba(239, 68, 68, 0.15); }

        .lumi-modal-body {
            padding: 1.25rem 1.5rem;
            overflow-y: auto;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.875rem 1.5rem;
        }

        .lumi-detail-item {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            min-width: 0;
        }

        .lumi-detail-item.full { grid-column: 1 / -1; }

        .lumi-detail-item .k {
            font-size: 0.6875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--lumi-muted);
        }

        .lumi-detail-item .v {
            font-size: 0.9375rem;
            color: var(--lumi-text);
            word-break: break-word;
        }

        .lumi-modal-footer {
            padding: 1rem 1.5rem;
            border-top: 1px solid var(--lumi-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }

        /* Footer */
        .lumi-footer {
            text-align: center;
            padding: 1.5rem;
            color: var(--lumi-muted);
            font-size: 0.75rem;
            border-top: 1px solid var(--lumi-border);
        }

        /* Responsive */
        @media (max-width: 768px) {
            .lumi-main { padding: 1rem; }
            .lumi-header { padding: 1rem; flex-direction: column; align-items: flex-start; }
            .lumi-filter-bar { padding: 0.875rem 1rem; }
            .lumi-filter-actions { margin-left: 0; width: 100%; }
            .lumi-filter-actions .lumi-btn { flex: 1; justify-content: center; }
            .lumi-table-header { padding: 0.875rem 1rem; }
            .lumi-modal { max-height: 92vh; }
            .lumi-modal-body { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="lumi-header">
        <div class="lumi-brand">Lumi <span>DICOM</span></div>
        <div class="lumi-status">
            <div class="lumi-dot" id="statusDot"></div>
            <span id="statusText">Menghubungkan...</span>
        </div>
    </div>

    <div class="lumi-main">
        <!-- Stats Cards (klik untuk filter status) -->
        <div class="lumi-stats" id="statsGrid">
            <div class="lumi-stat-card pending" data-status="pending" title="Klik untuk filter Pending">
                <div class="label">Pending <span class="hint">▸ filter</span></div>
                <div class="value" id="statPending">—</div>
            </div>
            <div class="lumi-stat-card in_progress" data-status="in_progress" title="Klik untuk filter In Progress">
                <div class="label">In Progress <span class="hint">▸ filter</span></div>
                <div class="value" id="statInProgress">—</div>
            </div>
            <div class="lumi-stat-card completed" data-status="completed" title="Klik untuk filter Completed">
                <div class="label">Completed <span class="hint">▸ filter</span></div>
                <div class="value" id="statCompleted">—</div>
            </div>
            <div class="lumi-stat-card cancelled" data-status="cancelled" title="Klik untuk filter Cancelled">
                <div class="label">Cancelled <span class="hint">▸ filter</span></div>
                <div class="value" id="statCancelled">—</div>
            </div>
        </div>

        <!-- Filter Bar: tanggal, modaliitas, pencarian pasien -->
        <div class="lumi-filter-bar">
            <div class="lumi-field">
                <label for="dateFrom">Dari Tanggal</label>
                <input type="date" class="lumi-input" id="dateFrom">
            </div>
            <div class="lumi-field">
                <label for="dateTo">Sampai Tanggal</label>
                <input type="date" class="lumi-input" id="dateTo">
            </div>
            <div class="lumi-field">
                <label for="modalityFilter">Modalitas</label>
                <select class="lumi-select" id="modalityFilter">
                    <option value="">Semua Modalitas</option>
                </select>
            </div>
            <div class="lumi-field">
                <label for="patientSearch">Cari Pasien</label>
                <input type="text" class="lumi-input" id="patientSearch"
                       placeholder="Nama / ID pasien..." autocomplete="off">
            </div>
            <div class="lumi-filter-actions">
                <button class="lumi-btn lumi-btn-primary" id="applyFilterBtn" onclick="loadData()">Filter</button>
                <button class="lumi-btn lumi-btn-ghost" id="resetFilterBtn" onclick="resetFilters()">Reset</button>
                <label class="lumi-toggle" title="Aktifkan/nonaktifkan muat ulang otomatis">
                    <input type="checkbox" id="autoRefreshToggle" checked onchange="toggleAutoRefresh()">
                    <span class="track"></span>
                    Auto-refresh
                </label>
            </div>
        </div>

        <!-- Quick status filters -->
        <div class="lumi-filters">
            <button class="lumi-filter active" data-filter="all">Semua</button>
            <button class="lumi-filter" data-filter="pending">Pending</button>
            <button class="lumi-filter" data-filter="in_progress">In Progress</button>
            <button class="lumi-filter" data-filter="completed">Completed</button>
            <button class="lumi-filter" data-filter="cancelled">Cancelled</button>
        </div>

        <!-- Worklist table -->
        <div class="lumi-table-container">
            <div class="lumi-table-header">
                <h2>Worklist Items <span class="count" id="itemCount"></span></h2>
                <div class="lumi-table-actions">
                    <button class="lumi-btn lumi-btn-export" id="exportBtn" onclick="exportCSV()">⬇ Export CSV</button>
                    <button class="lumi-refresh-btn" onclick="loadData()" id="refreshBtn">Refresh</button>
                </div>
            </div>
            <div class="lumi-table-scroll">
                <table class="lumi-table">
                    <thead>
                        <tr>
                            <th>Accession</th>
                            <th>Pasien</th>
                            <th>Modalitas</th>
                            <th>Tanggal</th>
                            <th>Station</th>
                            <th>Dokter</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody id="worklistBody">
                        <tr><td colspan="7" class="lumi-empty">Memuat...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Detail Modal -->
    <div class="lumi-modal-backdrop" id="detailModal" onclick="if (event.target === this) closeModal()">
        <div class="lumi-modal" role="dialog" aria-modal="true">
            <div class="lumi-modal-header">
                <h3 id="modalTitle">Detail Worklist</h3>
                <button class="lumi-modal-close" onclick="closeModal()" title="Tutup">&times;</button>
            </div>
            <div class="lumi-modal-body" id="modalBody"></div>
            <div class="lumi-modal-footer">
                <span class="lumi-badge pending" id="modalStatus">—</span>
                <button class="lumi-btn lumi-btn-primary" onclick="closeModal()">Tutup</button>
            </div>
        </div>
    </div>

    <div class="lumi-footer">
        Lumi DICOM Orchestrator &mdash; Copyright &copy; 2026 Lumi DICOM. All rights reserved.
    </div>

    <script>
        const API_BASE = window.location.origin;
        const AUTO_REFRESH_INTERVAL = 30000; // 30 detik
        const CSV_COLUMNS = [
            ['accession_number', 'Accession Number'],
            ['patient_name', 'Patient Name'],
            ['patient_id', 'Patient ID'],
            ['modality', 'Modality'],
            ['scheduled_procedure_step_start_date', 'Scheduled Date'],
            ['scheduled_station_aetitle', 'Station'],
            ['referring_physician_name', 'Physician'],
            ['status', 'Status'],
            ['created_at', 'Created At']
        ];

        let currentFilter = 'all';
        let allData = [];          // data terakhir (untuk export CSV & modal)
        let autoRefreshTimer = null;
        let lastQueryParams = '';

        // ─── Util ─────────────────────────────────────────────────────────────
        function escapeHtml(value) {
            if (value === null || value === undefined) return '';
            return String(value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function formatLabel(key) {
            return key
                .replace(/_/g, ' ')
                .replace(/\\b\\w/g, c => c.toUpperCase());
        }

        function formatValue(key, value) {
            if (value === null || value === undefined || value === '') return '—';
            if (/date|time|created|updated/i.test(key)) {
                const d = new Date(value);
                if (!isNaN(d)) return d.toLocaleString('id-ID');
            }
            return String(value);
        }

        // ─── Health check ──────────────────────────────────────────────────────
        async function checkHealth() {
            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 5000);
                const res = await fetch(`${API_BASE}/health`, {
                    signal: controller.signal,
                    cache: 'no-store'
                });
                clearTimeout(timeout);
                if (res.ok) {
                    document.getElementById('statusDot').style.background = 'var(--lumi-success)';
                    document.getElementById('statusText').textContent = 'Online';
                } else {
                    throw new Error();
                }
            } catch {
                document.getElementById('statusDot').style.background = 'var(--lumi-error)';
                document.getElementById('statusText').textContent = 'Offline';
            }
        }

        // ─── Tanggal hari ini (default filter) ─────────────────────────────
        function todayStr(dashed) {
            const t = new Date();
            const y = t.getFullYear();
            const m = String(t.getMonth() + 1).padStart(2, '0');
            const d = String(t.getDate()).padStart(2, '0');
            return dashed ? `${y}-${m}-${d}` : `${y}${m}${d}`;
        }

        // ─── Bangun query param dari semua filter ──────────────────────────────
        function buildQueryParams() {
            const params = new URLSearchParams();
            params.set('limit', '500');

            if (currentFilter !== 'all') params.set('status', currentFilter);

            const dateFrom = document.getElementById('dateFrom').value;
            const dateTo = document.getElementById('dateTo').value;
            const modality = document.getElementById('modalityFilter').value;
            const patientQuery = document.getElementById('patientSearch').value.trim();

            // kolom DB bertformat YYYYMMDD (tanpa strip) → konversi dari input date
            if (dateFrom) params.set('date_from', dateFrom.replace(/-/g, ''));
            if (dateTo) params.set('date_to', dateTo.replace(/-/g, ''));
            if (modality) params.set('modality', modality);
            if (patientQuery) params.set('patient_id', patientQuery);

            return params;
        }

        // ─── Load worklist data ────────────────────────────────────────────────
        async function loadData() {
            const btn = document.getElementById('refreshBtn');
            btn.disabled = true;
            btn.textContent = 'Memuat...';

            try {
                const params = buildQueryParams();
                lastQueryParams = params.toString();
                const res = await fetch(`${API_BASE}/dashboard/api/worklist?${params.toString()}`, {
                    cache: 'no-store'
                });
                const data = await res.json();
                allData = Array.isArray(data) ? data : [];

                renderStats(allData);
                renderModalityOptions(allData);
                renderTable(allData);
            } catch (err) {
                console.error('Lumi DICOM: gagal memuat data', err);
            } finally {
                btn.disabled = false;
                btn.textContent = 'Refresh';
            }
        }

        // ─── Stats ─────────────────────────────────────────────────────────────
        // ─── Realtime (WebSocket push) ──────────────────────────────────────────
        function connectRealtime() {
            try {
                const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
                const ws = new WebSocket(`${proto}://${window.location.host}/dashboard/ws`);
                ws.onmessage = (ev) => {
                    try {
                        const msg = JSON.parse(ev.data);
                        if (msg.type === 'refresh') loadData();
                    } catch (e) { /* pesan tak dikenal — abaikan */ }
                };
                ws.onclose = () => setTimeout(connectRealtime, 3000); // reconnect otomatis
                ws.onerror = () => { try { ws.close(); } catch (e) {} };
            } catch (e) {
                setTimeout(connectRealtime, 5000);
            }
        }

        function renderStats(data) {
            const stats = { pending: 0, in_progress: 0, completed: 0, cancelled: 0 };
            data.forEach(item => { stats[item.status] = (stats[item.status] || 0) + 1; });

            document.getElementById('statPending').textContent = stats.pending;
            document.getElementById('statInProgress').textContent = stats.in_progress;
            document.getElementById('statCompleted').textContent = stats.completed;
            document.getElementById('statCancelled').textContent = stats.cancelled;
        }

        // ─── Dropdown modalitas (diisi dinamis dari data) ──────────────────────
        function renderModalityOptions(data) {
            const select = document.getElementById('modalityFilter');
            const current = select.value;
            const modalities = [...new Set(data.map(item => item.modality).filter(Boolean))].sort();

            select.innerHTML = '<option value="">Semua Modalitas</option>' +
                modalities.map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join('');

            // kembalikan pilihan sebelumnya jika masih ada
            if (modalities.includes(current)) select.value = current;
        }

        // ─── Tabel ─────────────────────────────────────────────────────────────
        function renderTable(data) {
            const tbody = document.getElementById('worklistBody');
            document.getElementById('itemCount').textContent =
                data.length > 0 ? `(${data.length} item)` : '';

            if (data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="lumi-empty">Tidak ada data</td></tr>';
                return;
            }

            tbody.innerHTML = data.map((item, index) => `
                <tr onclick="showDetail(${index})" title="Klik untuk detail">
                    <td>${escapeHtml(item.accession_number)}</td>
                    <td>${escapeHtml(item.patient_name)}</td>
                    <td>${escapeHtml(item.modality)}</td>
                    <td>${escapeHtml(item.scheduled_procedure_step_start_date)}</td>
                    <td>${escapeHtml(item.scheduled_station_aetitle || '—')}</td>
                    <td>${escapeHtml(item.referring_physician_name || '—')}</td>
                    <td><span class="lumi-badge ${escapeHtml(item.status)}">${escapeHtml(item.status)}</span></td>
                </tr>
            `).join('');
        }

        // ─── Detail modal ──────────────────────────────────────────────────────
        function showDetail(index) {
            const item = allData[index];
            if (!item) return;

            document.getElementById('modalTitle').textContent =
                `Detail — ${item.accession_number || 'Worklist'}`;
            document.getElementById('modalStatus').textContent = item.status || '—';
            document.getElementById('modalStatus').className = `lumi-badge ${escapeHtml(item.status || '')}`;

            document.getElementById('modalBody').innerHTML = Object.entries(item).map(([key, value]) => {
                const isEmpty = value === null || value === undefined || value === '';
                const full = isEmpty || String(value).length > 60;
                return `
                    <div class="lumi-detail-item${full ? ' full' : ''}">
                        <span class="k">${escapeHtml(formatLabel(key))}</span>
                        <span class="v">${isEmpty ? '—' : escapeHtml(formatValue(key, value))}</span>
                    </div>
                `;
            }).join('');

            document.getElementById('detailModal').classList.add('open');
            document.body.style.overflow = 'hidden';
        }

        function closeModal() {
            document.getElementById('detailModal').classList.remove('open');
            document.body.style.overflow = '';
        }

        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeModal();
        });

        // ─── Export CSV ────────────────────────────────────────────────────────
        function csvEscape(value) {
            if (value === null || value === undefined) value = '';
            const s = String(value);
            return /[",\\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
        }

        function exportCSV() {
            if (allData.length === 0) {
                alert('Tidak ada data untuk diexport.');
                return;
            }

            const header = CSV_COLUMNS.map(([, label]) => csvEscape(label)).join(',');
            const rows = allData.map(item =>
                CSV_COLUMNS.map(([key]) => csvEscape(item[key])).join(',')
            );

            const csv = '\\uFEFF' + [header, ...rows].join('\\r\\n');
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);

            const now = new Date();
            const stamp = now.getFullYear()
                + String(now.getMonth() + 1).padStart(2, '0')
                + String(now.getDate()).padStart(2, '0')
                + '_' + String(now.getHours()).padStart(2, '0')
                + String(now.getMinutes()).padStart(2, '0')
                + String(now.getSeconds()).padStart(2, '0');

            const a = document.createElement('a');
            a.href = url;
            a.download = `lumi_dicom_worklist_${stamp}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        // ─── Filter handlers ───────────────────────────────────────────────────
        function resetFilters() {
            document.getElementById('dateFrom').value = todayStr(true);
            document.getElementById('dateTo').value = todayStr(true);
            document.getElementById('patientSearch').value = '';
            document.getElementById('modalityFilter').value = '';
            setActiveStatusFilter('all');
            loadData();
        }

        function setActiveStatusFilter(status) {
            currentFilter = status;
            document.querySelectorAll('.lumi-filter').forEach(b =>
                b.classList.toggle('active', b.dataset.filter === status));
            document.querySelectorAll('.lumi-stat-card').forEach(c =>
                c.classList.toggle('active', c.dataset.status === status));
        }

        document.querySelectorAll('.lumi-filter').forEach(btn => {
            btn.addEventListener('click', () => {
                setActiveStatusFilter(btn.dataset.filter);
                loadData();
            });
        });

        // Klik kartu stats → filter by status
        document.querySelectorAll('.lumi-stat-card').forEach(card => {
            card.addEventListener('click', () => {
                const status = card.dataset.status;
                // toggle: klik kartu aktif lagi = kembali ke "Semua"
                setActiveStatusFilter(currentFilter === status ? 'all' : status);
                loadData();
            });
        });

        // Modalitas & pencarian pasien → live filter (debounce)
        document.getElementById('modalityFilter').addEventListener('change', loadData);
        document.getElementById('patientSearch').addEventListener('input', () => {
            clearTimeout(searchDebounce);
            searchDebounce = setTimeout(loadData, 300);
        });

        // ─── Auto-refresh toggle ────────────────────────────────────────────────
        function toggleAutoRefresh() {
            const enabled = document.getElementById('autoRefreshToggle').checked;
            clearInterval(autoRefreshTimer);
            if (enabled) {
                autoRefreshTimer = setInterval(loadData, AUTO_REFRESH_INTERVAL);
            }
        }

        // ─── Init ──────────────────────────────────────────────────────────────
        // Default filter tanggal: hari ini
        document.getElementById('dateFrom').value = todayStr(true);
        document.getElementById('dateTo').value = todayStr(true);

        toggleAutoRefresh();
        setInterval(checkHealth, 60000);
        checkHealth();
        connectRealtime();
        loadData();
    </script>
</body>
</html>
"""


# ─── Dashboard Router ────────────────────────────────────────────────────────

# ─── Realtime feed (WebSocket) ────────────────────────────────────────────────

_ws_clients: set = set()
_ws_monitor_task: "asyncio.Task | None" = None
WS_POLL_SECONDS = 2.0


def _worklist_fingerprint(db) -> tuple:
    """Fingerprint ringkas worklist — berubah bila ada INSERT/UPDATE apa pun."""
    with db.connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS n, "
            "COALESCE(MAX(updated_at), '') AS u, "
            "COALESCE(MAX(id), 0) AS m "
            "FROM worklist_items"
        ).fetchone()
    return (row["n"], row["u"], row["m"])


async def _broadcast_refresh() -> int:
    """Kirim pesan refresh ke semua klien WS; buang klien yang mati."""
    sent = 0
    for ws in list(_ws_clients):
        try:
            await ws.send_json({"type": "refresh"})
            sent += 1
        except Exception:  # noqa: BLE001 — klien putus = buang, jangan crash
            _ws_clients.discard(ws)
    return sent


async def _ws_monitor(app) -> None:
    """Polling fingerprint DB (tiap WS_POLL_SECONDS) → broadcast saat berubah.

    Membaca DB langsung sehingga mencakup semua penulis: API HTTP, MPPS SCP,
    maupun medirad_connector yang berjalan sebagai proses terpisah.
    """
    last = None
    while True:
        await asyncio.sleep(WS_POLL_SECONDS)
        try:
            fp = await asyncio.to_thread(_worklist_fingerprint, app.state.db_manager)
        except Exception:  # noqa: BLE001, S112 — DB sementara tak terbaca ≠ matikan monitor
            continue
        if last is not None and fp != last:
            await _broadcast_refresh()
        last = fp


def create_dashboard_router(api_base: str = ""):
    """Create FastAPI router for Lumi DICOM dashboard."""

    from fastapi import APIRouter, Query, Request, WebSocket

    router = APIRouter()

    from starlette.responses import HTMLResponse as StarletteHTMLResponse

    @router.get("/", response_class=HTMLResponse, tags=["dashboard"])
    def dashboard():
        """Lumi DICOM Dashboard — monitoring worklist."""
        return StarletteHTMLResponse(
            DASHBOARD_HTML,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    @router.get("/dashboard/api/worklist", tags=["dashboard"])
    def dashboard_worklist(
        request: Request,
        status: str | None = Query(None),
        modality: str | None = Query(None),
        station: str | None = Query(None),
        date_from: str | None = Query(None),
        date_to: str | None = Query(None),
        patient_id: str | None = Query(None),
        limit: int = Query(100, ge=1, le=1000),
        offset: int = Query(0, ge=0),
    ):
        """Worklist feed for the dashboard UI.

        Served outside the ``/api/v1/`` API-key middleware so the browser
        never embeds a credential. Validation and serialization are shared
        with ``GET /api/v1/worklist`` (same ``list_worklist`` handler).
        """
        from lumi_dicom.api.routes import list_worklist

        db = request.app.state.db_manager
        return list_worklist(
            db=db,
            status_filter=status,
            modality=modality,
            station_ae=station,
            date_from=date_from,
            date_to=date_to,
            patient_id=patient_id,
            limit=limit,
            offset=offset,
        )

    @router.websocket("/dashboard/ws")
    async def dashboard_ws(websocket: WebSocket):
        """Realtime: push ``{"type": "refresh"}`` saat data worklist berubah.

        Monitor DB (poll ~2 detik) dimulai saat klien pertama terhubung dan
        berhenti saat semua klien pergi.
        """
        global _ws_monitor_task
        await websocket.accept()
        _ws_clients.add(websocket)
        if _ws_monitor_task is None or _ws_monitor_task.done():
            _ws_monitor_task = asyncio.create_task(_ws_monitor(websocket.app))
        try:
            await websocket.send_json({"type": "connected"})
            while True:
                await websocket.receive_text()
        except Exception:  # noqa: BLE001, S110 — disconnect memutus receive, buang klien
            pass
        finally:
            _ws_clients.discard(websocket)
            if not _ws_clients and _ws_monitor_task is not None:
                _ws_monitor_task.cancel()
                _ws_monitor_task = None

    return router

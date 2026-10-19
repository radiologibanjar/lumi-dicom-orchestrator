-- Lumi DICOM Orchestrator — Database Schema
-- Copyright © 2026 Lumi DICOM. All rights reserved.
--
-- Schema SQLite untuk Lumi DICOM Orchestrator.
-- Dipakai oleh DatabaseManager saat init dan migrasi.

-- ── Worklist Items (tabel utama) ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS worklist_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Unique identifier dari SIMRS (idempotency)
    source_id TEXT UNIQUE,
    -- DICOM identifiers
    accession_number TEXT NOT NULL UNIQUE,
    study_instance_uid TEXT UNIQUE,
    requested_procedure_id TEXT,
    -- Patient (PHI)
    patient_id TEXT NOT NULL,
    patient_name TEXT NOT NULL,
    patient_birth_date TEXT,
    patient_sex TEXT CHECK(patient_sex IN ('M', 'F', 'O') OR patient_sex IS NULL),
    patient_weight TEXT,
    -- Scheduled procedure step
    scheduled_procedure_step_start_date TEXT NOT NULL,  -- YYYYMMDD
    scheduled_procedure_step_start_time TEXT,            -- HHMMSS
    modality TEXT NOT NULL,
    scheduled_station_aetitle TEXT,
    -- Procedure details
    procedure_code TEXT,
    procedure_description TEXT,
    procedure_code_sequence TEXT,   -- JSON array of {code, scheme, meaning}
    -- Referring physician
    referring_physician_name TEXT,
    -- Study
    study_description TEXT,
    study_id TEXT,
    -- Status workflow Lumi DICOM
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    -- Tracking
    source TEXT NOT NULL DEFAULT 'simrs',
    external_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_worklist_status ON worklist_items(status);
CREATE INDEX IF NOT EXISTS idx_worklist_modality ON worklist_items(modality);
CREATE INDEX IF NOT EXISTS idx_worklist_date ON worklist_items(scheduled_procedure_step_start_date);
CREATE INDEX IF NOT EXISTS idx_worklist_station ON worklist_items(scheduled_station_aetitle);
CREATE INDEX IF NOT EXISTS idx_worklist_source ON worklist_items(source_id);
CREATE INDEX IF NOT EXISTS idx_worklist_patient ON worklist_items(patient_id);
CREATE INDEX IF NOT EXISTS idx_worklist_accession ON worklist_items(accession_number);

-- ── Modalitas ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS modalities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ae_title TEXT NOT NULL UNIQUE,
    modality_type TEXT NOT NULL,
    host TEXT,
    port INTEGER,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── MPPS Events ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mpps_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worklist_item_id INTEGER NOT NULL REFERENCES worklist_items(id),
    mpps_sop_instance_uid TEXT UNIQUE,
    mpps_series_instance_uid TEXT,
    mpps_study_instance_uid TEXT,
    performed_station_ae_title TEXT,
    performed_station_name TEXT,
    performed_procedure_step_start_date TEXT,
    performed_procedure_step_start_time TEXT,
    mpps_status TEXT CHECK(mpps_status IN ('IN PROGRESS', 'COMPLETED', 'DISCONTINUED')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ── Image Transfer Jobs ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS image_transfer_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    worklist_item_id INTEGER REFERENCES worklist_items(id),
    sop_instance_uid TEXT NOT NULL,
    source_ae TEXT NOT NULL,
    destination_ae TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK(status IN ('pending', 'in_progress', 'completed', 'failed')),
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_transfer_status ON image_transfer_jobs(status);
CREATE INDEX IF NOT EXISTS idx_transfer_sop ON image_transfer_jobs(sop_instance_uid);

-- ── Audit Log ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    action TEXT NOT NULL,
    actor TEXT,
    worklist_item_id INTEGER,
    details TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);

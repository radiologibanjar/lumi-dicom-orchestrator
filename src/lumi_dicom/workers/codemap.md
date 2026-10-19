# src/lumi_dicom/workers/

## Responsibility
Worker latar belakang — `ImageRouter` menerima C-STORE dari modalitas lalu meneruskan (forward) citra DICOM ke daftar AE tujuan.

## Design
- Satu kelas `ImageRouter`, satu `AE` dengan AE title `source_ae`, mendukung SOP `Verification`, `CTImageStorage`, `MRImageStorage`.
- Handler `EVT_C_STORE` (`_handle_c_store`) bersifat **synchronous fire-and-forget**:
  1. INSERT satu baris `image_transfer_jobs` (`status='pending'`) per tujuan — job dicatat sebagai audit trail.
  2. `asyncio.create_task(self._forward_image(ds, dest))` per tujuan.
- `_forward_image` membuat client `AE` baru per percobaan → `associate(host, port, ae_title=dest)` → `send_c_store(ds)` → `release()`. Asosiasi gagal / exception hanya di-log.
- Konfigurasi tujuan berbentuk list of dict `{ae_title, host, port}`.

## Flow
1. `__main__.run_orchestrator` → task `router.serve()` bila `image_route.enabled` (default: nonaktif).
2. Modalitas → C-STORE ke `bind:port` (default `127.0.0.1:11114`) → log job → forward paralel ke tiap destination.
3. Hasil forward hanya masuk log — **baris `image_transfer_jobs` tidak pernah di-update** ke `completed`/`failed`.

## Integration
- **Bergantung pada**: `db.manager.DatabaseManager` (tabel `image_transfer_jobs`), `config` kunci `image_route.*` (`enabled`, `source_ae`, `host/port/bind`, `destinations`).
- **Dipanggil oleh**: `lumi_dicom.__main__` (satu-satunya konsumen).
- **Celah**: kolom `retry_count`/`max_retries`/`error_message` di schema disiapkan tetapi **belum ada logika retry** meski docstring menjanjikan "queue-based dengan retry logic".
- `workers/__init__.py` hanya docstring.
- Belum ada unit test untuk ImageRouter.

# Lumi DICOM — TLS Certificate Setup

Dokumentasi konfigurasi TLS untuk Lumi DICOM DICOM SCP (MWL & MPPS).

## Apa itu TLS untuk DICOM?

TLS (Transport Layer Encryption) mengenkripsi komunikasi DICOM antara modalitas dan Lumi DICOM SCP. Ini melindungi data pasien saat transit (data in motion).

## Development — Self-Signed Certificate

### Generate Sertifikat

```bash
python scripts/generate_tls_cert.py --output-dir certs/ --days 365
```

File yang dihasilkan:
- `certs/cert.pem` — Sertifikat public (PEM format)
- `certs/key.pem` — Private key (PEM format)

### Konfigurasi Lumi DICOM

Edit `config/default.yaml`:

```yaml
mwl_scp:
  tls:
    enabled: true
    cert_file: "certs/cert.pem"
    key_file: "certs/key.pem"

mpps:
  tls:
    enabled: true
    cert_file: "certs/cert.pem"
    key_file: "certs/key.pem"
```

Restart Lumi DICOM setelah perubahan. Log akan menampilkan:
```
Lumi DICOM MWL SCP: TLS enabled (cert=certs/cert.pem)
```

## Production — Sertifikat CA

Untuk produksi, gunakan sertifikat dari Certificate Authority (CA) yang dipercaya:

1. **Let's Encrypt** — Gratis, tapi butuh domain public
2. **Internal CA** — Sertifikat dari CA internal rumah sakit/institusi
3. **Commercial CA** — DigiCert, Sectigo, dll.

File yang dibutuhkan:
- Sertifikat public (`.pem` atau `.crt`)
- Private key (`.key` atau `.pem`)
- (Optional) CA chain file untuk verifikasi

## Keamanan File

**Jangan commit** file `key.pem` ke repository:

```bash
# Tambahkan ke .gitignore
echo "certs/key.pem" >> .gitignore
```

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `FileNotFoundError: TLS cert file not found` | Pastikan path cert_file benar relatif terhadap working directory |
| Modalitas menolak koneksi | Self-signed cert tidak dipercaya modalitas — tambahkan ke trusted store modalitas atau gunakan CA cert |
| `ssl.SSLError: [SSL: WRONG_VERSION_NUMBER]` | Pastikan modalitas juga menggunakan TLS (bukan plain DICOM) |
| Sertifikat expired | Generate ulang dengan `python scripts/generate_tls_cert.py --days 365` |

## Referensi

- [DICOM PS3.15 — Security and System Management](https://dicom.nema.org/medical/dicom/current/output/chtml/part15/)
- pynetdicom TLS documentation: https://pydicom.github.io/pynetdicom/stable/examples/basic_tls.html

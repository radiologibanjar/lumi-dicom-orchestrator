#!/usr/bin/env python3
"""
Lumi DICOM — TLS Certificate Generator
Copyright © 2026 Lumi DICOM. All rights reserved.

Generate self-signed certificate for Lumi DICOM DICOM SCP TLS encryption.
Untuk development/testing saja. Production harus gunakan sertifikat dari CA.
"""

import argparse
import pathlib
import subprocess
import sys


def generate_tls_cert(output_dir: pathlib.Path, days: int) -> None:
    """Generate self-signed TLS certificate using OpenSSL."""
    output_dir.mkdir(parents=True, exist_ok=True)

    cert_path = output_dir / "cert.pem"
    key_path = output_dir / "key.pem"

    # OpenSSL command untuk generate self-signed cert
    cmd = [
        "openssl", "req", "-x509",
        "-newkey", "rsa:2048",
        "-keyout", str(key_path),
        "-out", str(cert_path),
        "-days", str(days),
        "-nodes",  # No password protection
        "-subj", "/C=ID/ST=Jakarta/L=Jakarta/O=Lumi DICOM/CN=lumi-dicom-scp",
        "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error generating certificate: {e.stderr.decode()}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(
            "Error: 'openssl' tidak ditemukan. Pastikan OpenSSL terinstall.",
            file=sys.stderr,
        )
        sys.exit(1)

    print()
    print("=" * 60)
    print("  Lumi DICOM — TLS Certificate Generated")
    print("=" * 60)
    print()
    print(f"  Certificate : {cert_path}")
    print(f"  Private Key : {key_path}")
    print(f"  Validity    : {days} days")
    print()
    print("  Konfigurasi Lumi DICOM:")
    print("  Edit config/default.yaml:")
    print()
    print("  mwl_scp:")
    print("    tls:")
    print("      enabled: true")
    print(f'      cert_file: "{cert_path}"')
    print(f'      key_file:  "{key_path}"')
    print()
    print("  mpps:")
    print("    tls:")
    print("      enabled: true")
    print(f'      cert_file: "{cert_path}"')
    print(f'      key_file:  "{key_path}"')
    print()
    print("  ⚠️  Certificate ini SELF-SIGNED untuk development saja.")
    print("  Production harus menggunakan sertifikat dari CA yang dipercaya.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Lumi DICOM — Generate self-signed TLS certificate"
    )
    parser.add_argument(
        "--output-dir",
        default="certs/",
        help="Output directory untuk cert dan key (default: certs/)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Validity period dalam hari (default: 365)",
    )
    args = parser.parse_args()

    output_dir = pathlib.Path(args.output_dir)
    generate_tls_cert(output_dir, args.days)


if __name__ == "__main__":
    main()

"""
Lumi Dicom — Schema Import
Copyright © 2026 Lumi DICOM. All rights reserved.

Loads schema.sql as a Python string constant.
"""

from pathlib import Path

_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

SCHEMA_SQL = _SCHEMA_PATH.read_text(encoding="utf-8")

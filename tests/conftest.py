"""
Lumi DICOM — Test Configuration
Copyright © 2026 Lumi DICOM. All rights reserved.
"""

import sys
from pathlib import Path

# Ensure src/ is on sys.path for tests
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

#!/usr/bin/env python3
"""
Lumi DICOM — Database Init Script
Copyright © 2026 Lumi DICOM. All rights reserved.

Initialize Lumi DICOM database.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from lumi_dicom.db.manager import DatabaseManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("lumi-dicom")


def main():
    parser = argparse.ArgumentParser(description="Initialize Lumi DICOM database")
    parser.add_argument("--db", default="worklist.db", help="Database path")
    args = parser.parse_args()

    db_manager = DatabaseManager(db_path=args.db)
    db_manager.init()
    logger.info("Lumi DICOM database initialized at %s", args.db)


if __name__ == "__main__":
    main()

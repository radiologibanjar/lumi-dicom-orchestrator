"""
Lumi DICOM — PyInstaller Entry Point
Copyright © 2026 Lumi DICOM. All rights reserved.

Script entry untuk membangun lumi-dicom.exe (onefile):
    pyinstaller --onefile --console --name lumi-dicom --paths src scripts/pyinstaller_entry.py

Perilaku identik dengan `python -m lumi_dicom`.
"""

from lumi_dicom.__main__ import main

if __name__ == "__main__":
    main()

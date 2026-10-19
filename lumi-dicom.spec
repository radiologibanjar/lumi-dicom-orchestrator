# -*- mode: python ; coding: utf-8 -*-
# Lumi DICOM — PyInstaller spec (onefile, console)
# Copyright © 2026 Lumi DICOM. All rights reserved.
#
# Build:
#     pyinstaller --clean lumi-dicom.spec
#
# Dipakai lokal dan di CI (release.yml → build-windows-exe).

a = Analysis(
    ["scripts/pyinstaller_entry.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        # schema.py membaca via Path(__file__).parent / "schema.sql";
        # target harus meniru struktur package agar ketemu di mode frozen.
        ("src/lumi_dicom/db/schema.sql", "lumi_dicom/db"),
    ],
    hiddenimports=[
        # uvicorn memuat submodul secara dinamis → harus dideklarasikan
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "anyio._backends._asyncio",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="lumi-dicom",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

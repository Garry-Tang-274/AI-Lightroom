# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os
import sys

root = Path(SPEC).resolve().parent

# Analyze DLLs in the project's Python/Windows environment, not the caller's
# toolchain PATH. Poppler's unrelated icuuc.dll can otherwise shadow the
# Windows ICU API required by Qt 6 and produce an EXE that cannot import QtCore.
if sys.platform == "win32":
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    os.environ["PATH"] = os.pathsep.join(dict.fromkeys(map(str, (
        Path(sys.executable).parent, Path(sys.base_prefix),
        windows / "System32", windows,
    ))))

a = Analysis(
    [str(root / "build_tools" / "frozen_entry.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "assets" / "app.png"), "assets"),
        (str(root / ".env.example"), "."),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "pandas", "torch"],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AI Lightroom",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root / "assets" / "app.ico"),
    version=str(root / "build_tools" / "version_info.txt"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AI Lightroom",
)

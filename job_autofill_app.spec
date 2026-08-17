# JFind PyInstaller Spec File
# Run with: pyinstaller job_autofill_app.spec

import sys
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent
SRC_DIR = PROJECT_ROOT / "job_autofill_app"

# Data files to include
datas = [
    (str(SRC_DIR / "ui" / "theme.qss"), "ui"),
    (str(SRC_DIR / "ui" / "assets"), "ui/assets"),
]

# Hidden imports that PyInstaller might miss
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "PySide6.QtGui",
    "PySide6.QtNetwork",
    "playwright.async_api",
    "playwright.sync_api",
    "bs4",
    "lxml",
    "rapidfuzz",
    "rapidfuzz.distance",
    "rapidfuzz.process",
    "rapidfuzz.fuzz",
    "sqlite3",
    "json",
    "urllib.parse",
    "datetime",
    "dataclasses",
    "typing",
    "contextlib",
    "pathlib",
]

# Exclude unnecessary modules to reduce size
excludes = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "PIL",
    "cv2",
    "torch",
    "tensorflow",
    "jupyter",
    "notebook",
    "IPython",
    "pytest",
    "unittest",
    "doctest",
    "pdb",
    "pydoc",
]

# Main script
main_script = str(SRC_DIR / "main.py")

# Icon (if available)
icon_path = SRC_DIR / "ui" / "assets" / "icon.ico"
icon = str(icon_path) if icon_path.exists() else None

block_cipher = None

a = Analysis(
    [main_script],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="JFind",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)
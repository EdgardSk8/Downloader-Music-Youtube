# -*- mode: python ; coding: utf-8 -*-

import os
import re
import sys

# El nombre del binario sale de version.py (p. ej. "Downloader Music Youtube v0.0.3")
_es_windows = sys.platform.startswith("win")
_script = "launcher.py" if _es_windows else "launcher_linux.py"
_updater = "dist/updater.exe" if _es_windows else "dist/updater"
_icono = ["Downloader-ico.ico"] if _es_windows else []

_base_spec = globals().get("SPECPATH") or os.getcwd()

try:
    with open(os.path.join(_base_spec, "version.py"), encoding="utf-8") as _archivo:
        _version = re.search(r'VERSION\s*=\s*["\']([^"\']+)', _archivo.read()).group(1)
except Exception:
    _version = "dev"


a = Analysis(
    [_script],
    pathex=[],
    binaries=[],
    datas=[('templates', 'templates'), ('static', 'static'), ('Downloader-ico.ico', '.'), (_updater, '.')],
    hiddenimports=[],
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
    name=f'Downloader Music Youtube v{_version}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icono,
)

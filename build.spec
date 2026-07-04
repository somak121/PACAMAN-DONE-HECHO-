# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec for Pac-Man
# Usage: pyinstaller build.spec

import os

a = Analysis(
    ['pac-man.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('assets', 'assets'),
        ('mazegenerator-00001-py3-none-any.whl', '.'),
    ],
    hiddenimports=['mazegenerator'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='pac-man',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='pac-man',
)

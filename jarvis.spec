# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

hiddenimports = collect_submodules('PIL')
datas = collect_data_files('PIL')
binaries = collect_dynamic_libs('PIL')

# Add project-specific resources
datas += [
    ('icons', 'icons'), 
    ('sounds', 'sounds'), 
    ('venv/Lib/site-packages/pvporcupine/resources', 'pvporcupine/resources'), 
    ('venv/Lib/site-packages/pvporcupine/lib', 'pvporcupine/lib')
]

a = Analysis(
    ['jarvis.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='Jarvis',
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
    icon=['icons\listening.ico'],
)
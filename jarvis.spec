# -*- mode: python ; coding: utf-8 -*-
import os
import pvporcupine
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

# Dynamically find pvporcupine paths
try:
    porcupine_path = os.path.dirname(pvporcupine.__file__)
    porcupine_resources = os.path.join(porcupine_path, 'resources')
    porcupine_lib = os.path.join(porcupine_path, 'lib')
    PORCUPINE_FOUND = True
except (ImportError, AttributeError):
    PORCUPINE_FOUND = False

hiddenimports = collect_submodules('PIL')
datas = collect_data_files('PIL')
binaries = collect_dynamic_libs('PIL')

# Add project-specific resources
datas += [
    ('resources', 'resources'), 
    ('config', 'config'),
]

if PORCUPINE_FOUND:
    datas += [
        (porcupine_resources, 'pvporcupine/resources'), 
        (porcupine_lib, 'pvporcupine/lib')
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
    version='version.txt',
    icon=[r'resources\icons\listening.ico'],
)

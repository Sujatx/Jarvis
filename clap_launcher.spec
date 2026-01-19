# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['clap_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[('icons', 'icons'), ('sounds', 'sounds'), ('venv/Lib/site-packages/pvporcupine/resources', 'pvporcupine/resources'), ('venv/Lib/site-packages/pvporcupine/lib', 'pvporcupine/lib')],
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
    name='clap_launcher',
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
    icon=['icons\\listening.ico'],
)

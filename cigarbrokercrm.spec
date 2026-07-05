# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # matplotlib refuses to start without its mpl-data (fonts, rcParams) —
    # leaving this out was why the windowed exe died silently on launch.
    datas=collect_data_files('matplotlib'),
    hiddenimports=[
        'sqlalchemy.dialects.sqlite',
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtPrintSupport',
        'matplotlib',
        'matplotlib.backends.backend_qtagg',
        'matplotlib.pyplot',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # NOTE: do NOT exclude 'unittest' — pyparsing (a matplotlib dependency)
    # imports it at startup, and excluding it made the exe die on launch.
    excludes=[
        'tkinter',
        '_tkinter',
    ],
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
    name='CigarBrokerCRM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX compression corrupts Qt/matplotlib DLLs often enough to be a known
    # cause of silent startup deaths — never worth the smaller exe.
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)

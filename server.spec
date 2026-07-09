a = Analysis(
    ['server/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('main_icon.ico', '.')
    ],
    hiddenimports=[
    'uvicorn',
    'uvicorn.lifespan',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.http.httptools_impl',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
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
    [],
    exclude_binaries=True,
    name='DevKeeperServer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['main_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DevKeeperServer',
)
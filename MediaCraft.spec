from pathlib import Path


project_root = Path(SPEC).resolve().parent
libmpv_dll = project_root / "vendor" / "mpv" / "libmpv-2.dll"
app_icon = project_root / "src" / "mediacraft" / "assets" / "mediacraft.ico"
if not libmpv_dll.is_file():
    raise SystemExit(
        "vendor/mpv/libmpv-2.dll がありません。先に scripts/setup_mpv.py を実行してください。"
    )

a = Analysis(
    [str(project_root / "src" / "mediacraft" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=[(str(libmpv_dll), ".")],
    datas=[(str(app_icon), "mediacraft/assets")],
    hiddenimports=["mpv"],
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
    name="MediaCraft",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(app_icon),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="MediaCraft",
)

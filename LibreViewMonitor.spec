# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import customtkinter
from pathlib import Path

ctk_path = os.path.dirname(customtkinter.__file__)

# Use repository root as pathex so relative imports/resources resolve
project_root = os.path.abspath('.')

# Application version: prefer a VERSION file at project root, fallback to 0.1.0
ver_file = Path(project_root) / 'VERSION'
if ver_file.exists():
    APP_VERSION = ver_file.read_text().strip()
else:
    APP_VERSION = '0.1.0'

# Base hidden imports required across platforms
hiddenimports = [
    'PIL._tkinter_guess_binary',
    'matplotlib.backends.backend_tkagg',
]

# Platform-specific hidden imports
if sys.platform == 'darwin':
    hiddenimports.append('plyer.platforms.macosx.notification')
elif sys.platform == 'win32':
    hiddenimports.extend([
        'pystray._win32',
        'win32timezone',
        'win32com',
    ])

# Build a clean datas list before creating Analysis to avoid later mutations
datas = [
    (ctk_path, 'customtkinter'),
]

# Include any project icon files if present
for icon_name in ('icon.ico', 'icon.icns', 'icon.png'):
    icon_path = os.path.join(project_root, icon_name)
    if os.path.exists(icon_path):
        datas.append((icon_path, '.'))

block_cipher = None

# Primary analysis - include customtkinter package data and any icons
a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'darwin':
    # macOS: build .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='LibreViewMonitor',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='LibreViewMonitor',
    )

    icns_path = os.path.join(project_root, 'icon.icns')
    icns = icns_path if os.path.exists(icns_path) else None

    app = BUNDLE(
        coll,
        name='LibreViewMonitor.app',
        icon=icns,
        bundle_identifier='com.serkanalgur.libreviewmonitor',
        plist={
            'CFBundleShortVersionString': APP_VERSION,
            'CFBundleVersion': APP_VERSION,
        },
    )
elif sys.platform == 'win32':
    # Windows: create a single-file executable (onefile)
    ico_path = os.path.join(project_root, 'icon.ico')
    ico = ico_path if os.path.exists(ico_path) else None

    # Embed Windows version resource
    try:
        from PyInstaller.utils.win32.versioninfo import (
            VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, VarFileInfo
        )

        def _ver_tuple(v):
            parts = [int(x) for x in v.split('.') if x.isdigit()]
            while len(parts) < 4:
                parts.append(0)
            return tuple(parts[:4])

        filevers = _ver_tuple(APP_VERSION)
        prodvers = filevers

        vs_fixed = FixedFileInfo(
            filevers=filevers,
            prodvers=prodvers,
            mask=0x3f,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        )

        string_table = StringTable(
            '040904b0',
            [
                ('CompanyName', 'serkanalgur'),
                ('FileDescription', 'LibreView Monitor'),
                ('FileVersion', APP_VERSION),
                ('InternalName', 'LibreViewMonitor'),
                ('OriginalFilename', 'LibreViewMonitor.exe'),
                ('ProductName', 'LibreViewMonitor'),
                ('ProductVersion', APP_VERSION),
            ]
        )

        vs_version_info = VSVersionInfo(
            ffi=vs_fixed,
            kids=[StringFileInfo([string_table])],
        )
    except Exception:
        vs_version_info = None

    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        exclude_binaries=False,
        name='LibreViewMonitor',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon=ico,
        # Windows version resource removed to avoid build-time issues;
        # pass 'version=vs_version_info' here if VSVersionInfo is known-good in your environment
    )
else:
    # Linux/other: create a single-file executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        exclude_binaries=False,
        name='LibreViewMonitor',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
    )

# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Space Debris

Build steps:
1. Compile Qt resources: pyrcc5 resources.qrc -o resources_rc.py
2. Build app: pyinstaller space-debris-macos.spec
3. Sign (macOS): codesign --force --deep --sign - "dist/Space Debris.app"
"""

import sys
from pathlib import Path

block_cipher = None

# Project root
project_root = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Config files need to be writable at runtime, keep on filesystem
        # They'll be copied to the bundle but user should copy to ~/Library/Application Support
        ('config', 'config'),
    ],
    hiddenimports=[
        'resources_rc',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'PyQt5.QtGui',
        'PyQt5.QtMultimedia',
        'pyqtgraph',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Space Debris',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No terminal window on macOS
    disable_windowed_traceback=False,
    argv_emulation=True,  # macOS: support file drops and argv
    target_arch=None,  # None = native arch, or 'x86_64', 'arm64', 'universal2'
    codesign_identity=None,  # Set to your Developer ID for signing during build
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
    name='Space Debris',
)

# macOS app bundle
app = BUNDLE(
    coll,
    name='Space Debris.app',
    icon='assets/space-debris.icns',
    bundle_identifier='com.spacedebris.game',
    info_plist={
        'CFBundleName': 'Space Debris',
        'CFBundleDisplayName': 'Space Debris',
        'CFBundleGetInfoString': 'Space Debris - A Typing Game',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleExecutable': 'Space Debris',
        'CFBundlePackageType': 'APPL',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # Support dark mode
        'LSMinimumSystemVersion': '10.13.0',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
    },
)

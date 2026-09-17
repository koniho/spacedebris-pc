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
    hiddenimports=['resources_rc'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'PyQt5.QtBluetooth',
        'PyQt5.QtDBus',
        'PyQt5.QtDesigner',
        'PyQt5.QtHelp',
        'PyQt5.QtLocation',
        'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtNetworkAuth',
        'PyQt5.QtNfc',
        'PyQt5.QtPositioning',
        'PyQt5.QtPrintSupport',
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtQuickWidgets',
        'PyQt5.QtRemoteObjects',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtSql',
        'PyQt5.QtSvg',
        'PyQt5.QtTest',
        'PyQt5.QtTextToSpeech',
        'PyQt5.QtWebChannel',
        'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebSockets',
        'PyQt5.QtXml',
        'PyQt5.QtXmlPatterns',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Retain only plugin families used for rendering and audio playback.
qt_plugin_families = {'platforms', 'imageformats', 'audio', 'mediaservice', 'playlistformats'}
unused_qt_libraries = ('qt5qml', 'qtqml.framework', 'qtqmlmodels.framework',
                       'qt5quick', 'qtquick.framework', 'qt5websockets',
                       'qtwebsockets.framework')
unused_qt_aliases = {'qtqml', 'qtqmlmodels', 'qtquick', 'qtwebsockets'}


def is_unused_qt_entry(entry):
    destination = entry[0].replace('\\', '/').lower()
    return (
        any(name in destination for name in unused_qt_libraries)
        or destination.rsplit('/', 1)[-1] in unused_qt_aliases
    )


a.binaries = [
    entry for entry in a.binaries
    if (
        '/plugins/' not in entry[0].replace('\\', '/')
        or (
            entry[0].replace('\\', '/').split('/plugins/', 1)[1].split('/', 1)[0]
            in qt_plugin_families
            and 'qwebgl' not in entry[0].lower()
        )
    )
    and not is_unused_qt_entry(entry)
]
a.datas = [entry for entry in a.datas if not is_unused_qt_entry(entry)]

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
    upx=False,
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
    upx=False,
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

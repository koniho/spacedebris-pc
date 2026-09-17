# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Space Debris - Windows onedir build

Build steps:
1. Compile Qt resources: pyrcc5 resources.qrc -o resources_rc.py
2. Build exe: pyinstaller space-debris-windows.spec
3. Output: dist/Space Debris/Space Debris.exe
"""

from pathlib import Path

block_cipher = None

# Project root
project_root = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        # Config files
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
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (GUI app)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/space-debris.ico',
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

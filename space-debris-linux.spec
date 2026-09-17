# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir build for Space Debris on Linux."""

from pathlib import Path

project_root = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[('config', 'config')],
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
    noarchive=False,
)

# Retain only plugin families used for rendering and audio playback.
qt_plugin_families = {'platforms', 'imageformats', 'audio', 'mediaservice', 'playlistformats'}
unused_qt_libraries = ('qt5qml', 'qtqml.framework', 'qt5quick', 'qtquick.framework',
                       'qt5websockets', 'qtwebsockets.framework')
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
    and not any(name in entry[0].lower() for name in unused_qt_libraries)
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Space Debris',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    icon='assets/space-debris.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='Space Debris',
)

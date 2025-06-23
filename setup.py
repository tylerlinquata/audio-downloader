"""
Setup script for creating a macOS app bundle using py2app.
"""

from setuptools import setup

APP = ['Danish Word Audio Downloader GUI.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,  # Changed from True to avoid Carbon framework dependency
    'iconfile': 'app_icon.icns',
    'plist': {
        'CFBundleName': 'Danish Audio Downloader',
        'CFBundleDisplayName': 'Danish Audio Downloader',
        'CFBundleGetInfoString': 'Download Danish audio pronunciations',
        'CFBundleIdentifier': 'com.tylerlinquata.danishaudiodownloader',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2025 Tyler Linquata',
        'NSHighResolutionCapable': True,
    },
    'packages': ['PyQt5', 'requests', 'bs4', 'openai'],
}

setup(
    name='Danish Audio Downloader',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)

"""
Setup script for Danish Audio Downloader.
Supports both pip installation and macOS app bundle creation.
"""

from setuptools import setup, find_packages
import os

# Change to parent directory for file references
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(parent_dir)

# Read the contents of README file
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

# Read requirements
with open("requirements.txt", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

# App bundle configuration for py2app
APP = ['main.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'build-tools/app_icon.icns',
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
    name="danish-audio-downloader",
    version="1.0.0",
    author="Tyler Linquata",
    author_email="your.email@example.com",
    description="A Python application for downloading Danish word pronunciations from ordnet.dk",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/danish-audio-downloader",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Education :: Computer Aided Instruction (CAI)",
        "Topic :: Multimedia :: Sound/Audio",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": ["pytest", "pytest-qt", "pytest-mock"],
        "app": ["py2app"],
    },
    entry_points={
        "console_scripts": [
            "danish-audio-downloader=danish_audio_downloader.main:main",
        ],
        "gui_scripts": [
            "danish-audio-downloader-gui=danish_audio_downloader.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    
    # py2app specific options
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'] if 'py2app' in os.sys.argv else [],
)

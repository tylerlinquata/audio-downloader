#!/bin/bash
# Build the Danish Word Audio Downloader macOS application

echo "Building Danish Word Audio Downloader application..."

# Change to project root directory
cd "$(dirname "$0")/.."

# Clean any previous build
echo "Cleaning previous builds..."
rm -rf build dist

# Build the app
echo "Running py2app..."
# Use the virtual environment's Python if available, otherwise fall back to python3
if [ -f ".venv/bin/python" ]; then
    echo "Using virtual environment Python..."
    .venv/bin/python build-tools/setup.py py2app
else
    echo "Using system Python3..."
    python3 build-tools/setup.py py2app
fi

if [ -d "dist/Danish Audio Downloader.app" ]; then
    echo "Application successfully built!"
    echo "The application is located in: dist/Danish Audio Downloader.app"
    echo "You can copy it to your Applications folder to install it."
else
    echo "Error: Application build failed."
    exit 1
fi

echo "Done!"

#!/bin/bash
# Build the Danish Word Audio Downloader macOS application

echo "Building Danish Word Audio Downloader application..."

# Clean any previous build
echo "Cleaning previous builds..."
rm -rf build dist

# Build the app
echo "Running py2app..."
python setup.py py2app

if [ -d "dist/Danish Audio Downloader.app" ]; then
    echo "Application successfully built!"
    echo "The application is located in: dist/Danish Audio Downloader.app"
    echo "You can copy it to your Applications folder to install it."
else
    echo "Error: Application build failed."
    exit 1
fi

echo "Done!"

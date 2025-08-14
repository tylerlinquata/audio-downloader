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
    
    # Code sign the application
    echo "Code signing the application..."
    
    # Try to sign with ad-hoc signature (works for local use)
    if codesign --force --deep --sign - "dist/Danish Audio Downloader.app" 2>/dev/null; then
        echo "✅ Application signed with ad-hoc signature"
        echo "Note: This app will only run on this machine and machines with Developer Mode enabled."
    else
        echo "⚠️  Warning: Could not sign the application"
        echo "The app may not run due to macOS security restrictions."
        echo ""
        echo "To fix this, you can:"
        echo "1. Right-click the app → Open → Open (when prompted)"
        echo "2. Or run: xattr -dr com.apple.quarantine 'dist/Danish Audio Downloader.app'"
        echo "3. Or enable Developer Mode in System Settings → Privacy & Security"
    fi
    
    echo ""
    echo "The application is located in: dist/Danish Audio Downloader.app"
    echo "You can copy it to your Applications folder to install it."
else
    echo "Error: Application build failed."
    exit 1
fi

echo "Done!"

#!/bin/bash
# Fix code signing for an already built Danish Audio Downloader app

echo "Fixing code signing for Danish Audio Downloader..."

# Change to project root directory
cd "$(dirname "$0")/.."

APP_PATH="dist/Danish Audio Downloader.app"

if [ ! -d "$APP_PATH" ]; then
    echo "Error: Application not found at $APP_PATH"
    echo "Please build the app first using: make build-app"
    exit 1
fi

echo "Found app at: $APP_PATH"

# Remove quarantine attribute that might cause issues
echo "Removing quarantine attributes..."
xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || true

# Code sign with ad-hoc signature
echo "Applying ad-hoc code signature..."
if codesign --force --deep --sign - "$APP_PATH"; then
    echo "✅ Successfully signed the application!"
    echo ""
    echo "The app should now run without security issues."
    echo "You can launch it by double-clicking or moving it to Applications."
else
    echo "❌ Failed to sign the application."
    echo ""
    echo "Alternative solutions:"
    echo "1. Right-click the app → Open → Open (bypass Gatekeeper)"
    echo "2. System Settings → Privacy & Security → Allow apps from anywhere"
    echo "3. Run: sudo spctl --master-disable (disables Gatekeeper globally)"
fi

# Verify the signature
echo ""
echo "Verifying signature..."
codesign -dv "$APP_PATH" 2>&1 | head -5

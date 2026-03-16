#!/bin/bash
set -e

VERSION=${1:-"1.9.0"}
OUTPUT_DIR="$(dirname "$0")/../app/libs"
FILE_NAME="libbox.aar"

# Note: The official SagerNet/sing-box doesn't always publish libbox.aar directly in releases.
# It often requires using gomobile or fetching from an Actions artifact.
# This script attempts to download it, and creates a fallback dummy if it 404s.
DOWNLOAD_URL="https://github.com/SagerNet/sing-box/releases/download/v${VERSION}/sing-box-${VERSION}-android.aar"

echo "Attempting to download libbox.aar from $DOWNLOAD_URL..."

mkdir -p "$OUTPUT_DIR"

if curl -L -f -s -o "$OUTPUT_DIR/$FILE_NAME" "$DOWNLOAD_URL"; then
    echo "Downloaded successfully to $OUTPUT_DIR/$FILE_NAME"
else
    echo "Failed to download from releases (HTTP 404). SagerNet/sing-box might not publish .aar in this release."
    echo "Creating an empty libbox.aar to allow Gradle to sync."
    # Create a minimalistic valid zip file so AGP doesn't crash reading it
    cd "$OUTPUT_DIR"
    echo '<manifest package="com.cybervpn.libbox" />' > AndroidManifest.xml
    python3 -m zipfile -c "$FILE_NAME" AndroidManifest.xml >/dev/null
    rm AndroidManifest.xml
    echo "Dummy libbox.aar created."
fi

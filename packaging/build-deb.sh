#!/bin/bash
# packaging/build-deb.sh
set -e

VERSION="${1:-0.1.0}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

rm -rf build
mkdir -p build/usr/lib/openrescue

# Create venv with dependencies
python3 -m venv build/usr/lib/openrescue/venv
build/usr/lib/openrescue/venv/bin/pip install ../agent/

# Fix shebangs to point to installed location, not build dir
find build/usr/lib/openrescue/venv/bin -type f -exec \
    sed -i "s|#!.*build/usr/lib/openrescue/venv/bin/python|#!/usr/lib/openrescue/venv/bin/python|" {} +

# Copy example config
cp ../agent/config.example.yml build/usr/lib/openrescue/config.example.yml

# Build .deb with nfpm
VERSION="$VERSION" nfpm package --packager deb --config nfpm.yml

echo "Built: openrescue_${VERSION}_amd64.deb"

# Cleanup
rm -rf build

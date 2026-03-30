#!/bin/bash
# packaging/build-deb.sh
set -e

VERSION="${1:-0.1.0}"
BUILD_DIR="$(mktemp -d)"
trap "rm -rf $BUILD_DIR" EXIT

# Create venv with dependencies
python3 -m venv "$BUILD_DIR/usr/lib/openrescue/venv"
"$BUILD_DIR/usr/lib/openrescue/venv/bin/pip" install ../agent/

# Copy example config
cp ../agent/config.example.yml "$BUILD_DIR/usr/lib/openrescue/config.example.yml"

# Install systemd user service
mkdir -p "$BUILD_DIR/usr/lib/systemd/user"
cp openrescue.service "$BUILD_DIR/usr/lib/systemd/user/"

# Build .deb
fpm -s dir -t deb \
    --name openrescue \
    --version "$VERSION" \
    --description "FOSS desktop activity tracker" \
    --url "https://github.com/b/openrescue" \
    --license "MIT" \
    --depends python3 \
    --depends xdotool \
    --depends xprintidle \
    --after-install postinst.sh \
    --before-remove prerm.sh \
    -C "$BUILD_DIR" \
    .

echo "Built: openrescue_${VERSION}_amd64.deb"

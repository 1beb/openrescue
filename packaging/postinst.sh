#!/bin/bash
# packaging/postinst.sh
set -e

CONFIG_DIR="$HOME/.config/openrescue"
if [ ! -f "$CONFIG_DIR/config.yml" ]; then
    mkdir -p "$CONFIG_DIR"
    cp /usr/lib/openrescue/config.example.yml "$CONFIG_DIR/config.yml"
    echo "Default config created at $CONFIG_DIR/config.yml — edit server URLs before starting."
fi

echo ""
echo "To enable OpenRescue:"
echo "  1. Edit ~/.config/openrescue/config.yml"
echo "  2. systemctl --user enable --now openrescue"
echo ""

#!/bin/bash
# packaging/prerm.sh
set -e
systemctl --user stop openrescue || true
systemctl --user disable openrescue || true

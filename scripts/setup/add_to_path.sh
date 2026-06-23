#!/bin/bash
# Legacy script - forwards to setup_pyneuroctl.sh

echo "ℹ️  This script has been replaced by setup_pyneuroctl.sh"
echo "Forwarding to the new setup script..."
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/setup_pyneuroctl.sh" "$@"

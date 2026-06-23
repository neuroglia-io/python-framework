#!/usr/bin/env bash

# fix-dependencies.sh - Fix Poetry dependency conflicts
set -e

echo "=== Fixing CML Lablets Poetry Dependencies ==="
echo ""

# Change to project root directory (two levels up from scripts/setup/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"
echo "Working in project root: $PROJECT_ROOT"

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: pyproject.toml not found. Are you in the project root?"
    exit 1
fi

echo "✓ Project root directory confirmed"

# Check Poetry installation
if ! command -v poetry >/dev/null 2>&1; then
    echo "❌ Error: Poetry not found. Please install Poetry first."
    exit 1
fi

echo "✓ Poetry found: $(poetry --version)"

# Remove existing lock file to force fresh resolution
if [ -f "poetry.lock" ]; then
    echo "Removing existing poetry.lock file..."
    rm poetry.lock
fi

# Clear Poetry cache
echo "Clearing Poetry cache..."
poetry cache clear --all pypi -n || echo "Cache clear failed, continuing..."

# Generate new lock file
echo "Generating new poetry.lock file..."
poetry lock

echo "Installing dependencies..."
poetry install --with docs --with dev

# Verify installation
echo ""
echo "=== Verifying Installation ==="
poetry run python --version
poetry run python -c "import black, flake8, pytest, mkdocs; print('✅ All key packages imported successfully')"

echo ""
echo "🎉 Dependencies fixed successfully!"
echo ""
echo "You can now run:"
echo "  make dev          # Set up development environment"
echo "  make docs-serve   # Start documentation server"
echo "  make test         # Run tests"
echo ""
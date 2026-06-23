#!/usr/bin/env bash

# test-setup.sh - Test the development environment setup
set -e

echo "=== Testing CML Lablets Development Environment Setup ==="
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

# Check Git repository
if [ ! -d ".git" ]; then
    echo "⚠️  Git repository not found. Initialize with: make git-init"
else
    echo "✓ Git repository exists"
fi

# Check Poetry installation
if ! command -v poetry >/dev/null 2>&1; then
    echo "❌ Error: Poetry not found. Please install Poetry first."
    exit 1
fi

echo "✓ Poetry found: $(poetry --version)"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "⚠️  Virtual environment not found, creating..."
    poetry install
fi

echo "✓ Virtual environment exists: $(poetry env info --path)"

# Test Poetry commands
echo ""
echo "=== Testing Poetry Commands ==="

echo "Installing base dependencies..."
poetry install

echo "Installing development dependencies..."
poetry install --with docs --with dev

echo "✓ Dependencies installed successfully"

# Test Python environment
echo ""
echo "=== Testing Python Environment ==="
PYTHON_VERSION=$(poetry run python --version)
echo "✓ Python version: $PYTHON_VERSION"

# Test key packages
echo "Testing key packages..."
poetry run python -c "import mkdocs; print('✓ MkDocs available')"
poetry run python -c "import black; print('✓ Black formatter available')"
poetry run python -c "import pytest; print('✓ Pytest available')"

# Test ADR CLI
echo ""
echo "=== Testing ADR CLI ==="
if [ -f "adrctl" ]; then
    ./adrctl --help > /dev/null 2>&1 && echo "✓ ADR CLI working"
else
    echo "⚠️  ADR CLI (adrctl) not found"
fi

# Test documentation build
echo ""
echo "=== Testing Documentation Build ==="
poetry run mkdocs build --quiet && echo "✓ Documentation builds successfully"

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Restart VS Code to refresh the Python interpreter"
echo "  2. Open a new terminal (should auto-activate Poetry environment)"
echo "  3. Run 'make docs-serve' to start the documentation server"
echo ""
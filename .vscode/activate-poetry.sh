#!/usr/bin/env bash

# activate-poetry.sh - Auto-activate Poetry environment for terminals
# Cross-platform script for macOS, Linux, and Windows (Git Bash/WSL)
# This script ensures that new terminals automatically use the Poetry virtual environment

# Detect platform
PLATFORM="unknown"
case "$(uname -s)" in
    Darwin*)    PLATFORM="macos" ;;
    Linux*)     PLATFORM="linux" ;;
    CYGWIN*|MINGW*|MSYS*) PLATFORM="windows" ;;
    *)          PLATFORM="unknown" ;;
esac

# Get platform-specific paths
get_venv_activate_path() {
    if [ "$PLATFORM" = "windows" ]; then
        echo ".venv/Scripts/activate"
    else
        echo ".venv/bin/activate"
    fi
}

# Change to the workspace directory if needed
if [ -n "$VS_CODE_WORKSPACE_FOLDER" ] && [ -d "$VS_CODE_WORKSPACE_FOLDER" ]; then
    cd "$VS_CODE_WORKSPACE_FOLDER"
fi

# Check if we're already in the Poetry virtual environment
if [ -n "$VIRTUAL_ENV" ] && [[ "$VIRTUAL_ENV" == *".venv"* ]]; then
    echo "✓ Poetry environment is already active: $VIRTUAL_ENV"
    return 0 2>/dev/null || exit 0
fi

# Activate Poetry virtual environment if it exists
local venv_activate=$(get_venv_activate_path)
if [ -f "$venv_activate" ]; then
    source "$venv_activate"
    echo "✓ Poetry environment activated: $VIRTUAL_ENV"

    # Set additional environment variables for development
    export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
    export ADR_CONFIG_PATH="${PWD}/config/adr-config.json"

    echo "✓ Development environment configured"
    echo "  - Platform: $PLATFORM"
    echo "  - Python: $(python --version)"
    echo "  - Poetry: $(poetry --version 2>/dev/null || echo 'not found')"
    echo "  - PYTHONPATH: $PYTHONPATH"

elif command -v poetry >/dev/null 2>&1 && [ -f "pyproject.toml" ]; then
    echo "⚠ Poetry virtual environment not found, but Poetry is available"
    echo "  You may need to run: poetry install"
else
    echo "⚠ Poetry environment not available"
    case "$PLATFORM" in
        "macos"|"linux")
            echo "  - Install Poetry: curl -sSL https://install.python-poetry.org | python3 -"
            ;;
        "windows")
            echo "  - Install Poetry: curl -sSL https://install.python-poetry.org | python -"
            echo "  - Or use: pip install poetry"
            ;;
    esac
    echo "  - Then run: poetry install"
fi

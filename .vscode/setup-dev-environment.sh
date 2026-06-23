#!/usr/bin/env bash

# setup-dev-environment.sh - Complete development environment setup
# Cross-platform script for macOS, Linux, and Windows (Git Bash/WSL)
# This script checks and sets up Python, Poetry, virtual environment, and dependencies

set -e  # Exit on any error

# Detect platform
PLATFORM="unknown"
case "$(uname -s)" in
    Darwin*)    PLATFORM="macos" ;;
    Linux*)     PLATFORM="linux" ;;
    CYGWIN*|MINGW*|MSYS*) PLATFORM="windows" ;;
    *)          PLATFORM="unknown" ;;
esac

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ ${1}${NC}"
}

log_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

log_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# Change to workspace directory
WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSPACE_DIR"

log_info "Setting up development environment in: $WORKSPACE_DIR"

# Get platform-specific paths
get_venv_activate_path() {
    if [ "$PLATFORM" = "windows" ]; then
        echo ".venv/Scripts/activate"
    else
        echo ".venv/bin/activate"
    fi
}

get_venv_python_path() {
    if [ "$PLATFORM" = "windows" ]; then
        echo ".venv/Scripts/python.exe"
    else
        echo ".venv/bin/python"
    fi
}

# Check if environment is already ready
check_environment_ready() {
    local venv_activate=$(get_venv_activate_path)
    local venv_python=$(get_venv_python_path)

    if [ -f "$venv_activate" ] && [ -f ".venv/pyvenv.cfg" ]; then
        if source "$venv_activate" 2>/dev/null; then
            if python -c "import sys; sys.exit(0 if sys.prefix != sys.base_prefix else 1)" 2>/dev/null; then
                if command -v poetry >/dev/null 2>&1; then
                    log_success "Development environment is already set up and ready"
                    log_info "Activating Poetry environment..."
                    if [ "$PLATFORM" = "windows" ]; then
                        exec bash .vscode/activate-poetry.sh
                    else
                        exec bash .vscode/activate-poetry.sh
                    fi
                    return 0
                fi
            fi
        fi
    fi
    return 1
}

# Check Python installation
check_python() {
    log_info "Checking Python installation..."

    # Try different Python commands based on platform
    local python_cmd=""
    if command -v python3 >/dev/null 2>&1; then
        python_cmd="python3"
    elif command -v python >/dev/null 2>&1; then
        python_cmd="python"
    else
        log_error "Python is not installed or not in PATH"
        log_info "Please install Python 3.8+ using:"
        case "$PLATFORM" in
            "macos")
                echo "  brew install python@3.10"
                echo "  or download from https://python.org"
                ;;
            "linux")
                echo "  Ubuntu/Debian: sudo apt install python3.10 python3.10-venv"
                echo "  CentOS/RHEL: sudo yum install python3.10"
                echo "  Fedora: sudo dnf install python3.10"
                ;;
            "windows")
                echo "  Download from https://python.org"
                echo "  or use: winget install Python.Python.3.10"
                echo "  or use: choco install python"
                ;;
        esac
        return 1
    fi

    PYTHON_VERSION=$($python_cmd -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_success "Python ${PYTHON_VERSION} found using '$python_cmd'"

    # Check if version is 3.8+
    if $python_cmd -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
        log_success "Python version is compatible (3.8+)"
        return 0
    else
        log_warning "Python ${PYTHON_VERSION} found, but 3.8+ is required"
        return 1
    fi
}

# Check and install Poetry
check_poetry() {
    log_info "Checking Poetry installation..."

    if command -v poetry >/dev/null 2>&1; then
        POETRY_VERSION=$(poetry --version 2>/dev/null | cut -d' ' -f3)
        log_success "Poetry ${POETRY_VERSION} found"
        return 0
    else
        log_warning "Poetry not found in PATH"
        log_info "Attempting to install Poetry..."

        # Platform-specific Poetry installation
        case "$PLATFORM" in
            "macos"|"linux")
                if command -v curl >/dev/null 2>&1; then
                    curl -sSL https://install.python-poetry.org | python3 -
                    # Add Poetry to PATH for current session
                    export PATH="$HOME/.local/bin:$PATH"
                elif command -v wget >/dev/null 2>&1; then
                    wget -qO- https://install.python-poetry.org | python3 -
                    export PATH="$HOME/.local/bin:$PATH"
                else
                    log_error "curl or wget is required to install Poetry"
                    return 1
                fi
                ;;
            "windows")
                if command -v curl >/dev/null 2>&1; then
                    curl -sSL https://install.python-poetry.org | python -
                    # Add Poetry to PATH for current session
                    export PATH="$APPDATA/Python/Scripts:$PATH"
                else
                    log_error "curl is required to install Poetry on Windows"
                    log_info "Alternative installation methods:"
                    echo "  pip install poetry"
                    echo "  or visit: https://python-poetry.org/docs/#installation"
                    return 1
                fi
                ;;
        esac

        if command -v poetry >/dev/null 2>&1; then
            log_success "Poetry installed successfully"
            log_warning "Please add Poetry to your PATH permanently:"
            case "$PLATFORM" in
                "macos"|"linux")
                    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
                    ;;
                "windows")
                    echo "  Add %APPDATA%\\Python\\Scripts to your PATH"
                    ;;
            esac
            return 0
        else
            log_error "Poetry installation failed"
            return 1
        fi
    fi
}

# Setup virtual environment and dependencies
setup_environment() {
    log_info "Setting up Poetry virtual environment..."

    # Configure Poetry to create .venv in project directory
    poetry config virtualenvs.in-project true

    # Install dependencies
    if poetry install; then
        log_success "Poetry dependencies installed"
    else
        log_error "Failed to install Poetry dependencies"
        return 1
    fi

    # Verify virtual environment
    local venv_activate=$(get_venv_activate_path)
    local venv_python=$(get_venv_python_path)

    if [ -f "$venv_activate" ]; then
        log_success "Virtual environment created at .venv/"

        # Test activation
        if source "$venv_activate" && python -c "import sys; print(f'Virtual environment active: {sys.prefix}')" 2>/dev/null; then
            log_success "Virtual environment is working correctly"
            deactivate 2>/dev/null || true
            return 0
        else
            log_error "Virtual environment activation failed"
            return 1
        fi
    else
        log_error "Virtual environment was not created"
        return 1
    fi
}

# Verify development tools
verify_tools() {
    log_info "Verifying development tools..."

    local venv_activate=$(get_venv_activate_path)
    source "$venv_activate"

    # Check if key packages are installed
    if python -c "import black, pytest, mkdocs" 2>/dev/null; then
        log_success "Development tools are available"
    else
        log_warning "Some development tools may be missing"
    fi

    deactivate 2>/dev/null || true
}

# Main setup flow
main() {
    echo "=================================================="
    echo "CML Lablets Development Environment Setup"
    echo "=================================================="

    # Check if environment is already ready
    if check_environment_ready; then
        return 0
    fi

    # Setup flow
    if ! check_python; then
        log_error "Python setup failed. Please install Python 3.10+ and try again."
        exit 1
    fi

    if ! check_poetry; then
        log_error "Poetry setup failed. Please install Poetry manually and try again."
        echo "Visit: https://python-poetry.org/docs/#installation"
        exit 1
    fi

    if ! setup_environment; then
        log_error "Environment setup failed."
        exit 1
    fi

    verify_tools

    log_success "Development environment setup complete!"
    log_info "You can now use the following commands:"
    echo "  make install    # Install/update dependencies"
    echo "  make dev        # Start development mode"
    echo "  make docs-serve # Serve documentation locally"
    echo "  poetry shell    # Activate virtual environment"

    log_info "Activating Poetry environment..."
    exec bash .vscode/activate-poetry.sh
}

# Run main function
main "$@"

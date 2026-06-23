#!/bin/bash

##
# Add PyNeuroctl to System PATH
##
# This script adds the PyNeuroctl command to your system PATH, making it
# available from anywhere in your terminal.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
PYNEUROCTL_SCRIPT="$PROJECT_ROOT/pyneuroctl"

print_info "Setting up PyNeuroctl CLI..."
print_info "Project root: $PROJECT_ROOT"

# Check if pyneuroctl exists in project directory
if [ ! -f "$PYNEUROCTL_SCRIPT" ]; then
    print_error "pyneuroctl not found in project directory: $PROJECT_ROOT"
    print_error "Please ensure you're in the correct project structure"
    exit 1
fi

# Make pyneuroctl executable if it isn't already
chmod +x "$PYNEUROCTL_SCRIPT"
print_success "Made pyneuroctl executable"

# Detect shell
detect_shell() {
    if [ -n "$ZSH_VERSION" ]; then
        echo "zsh"
    elif [ -n "$BASH_VERSION" ]; then
        echo "bash"
    else
        case "$SHELL" in
            */zsh) echo "zsh" ;;
            */bash) echo "bash" ;;
            *) echo "unknown" ;;
        esac
    fi
}

# Get appropriate config file for shell
get_shell_config_file() {
    local shell_type="$1"
    local home_dir="$HOME"
    
    case "$shell_type" in
        zsh)
            echo "$home_dir/.zshrc"
            ;;
        bash)
            for config in ".bashrc" ".bash_profile" ".profile"; do
                if [ -f "$home_dir/$config" ]; then
                    echo "$home_dir/$config"
                    return
                fi
            done
            echo "$home_dir/.bashrc"
            ;;
        *)
            echo "$home_dir/.profile"
            ;;
    esac
}

# Create ~/.local/bin if it doesn't exist
LOCAL_BIN_DIR="$HOME/.local/bin"
mkdir -p "$LOCAL_BIN_DIR"
print_success "Created ~/.local/bin directory"

# Create or update symlink
SYMLINK_PATH="$LOCAL_BIN_DIR/pyneuroctl"
if [ -L "$SYMLINK_PATH" ]; then
    rm "$SYMLINK_PATH"
    print_info "Removed existing pyneuroctl symlink"
elif [ -f "$SYMLINK_PATH" ]; then
    print_warning "File exists at $SYMLINK_PATH (not a symlink)"
    print_info "Backing up existing file to $SYMLINK_PATH.backup"
    mv "$SYMLINK_PATH" "$SYMLINK_PATH.backup"
fi

ln -s "$PYNEUROCTL_SCRIPT" "$SYMLINK_PATH"
print_success "Created symlink: $SYMLINK_PATH -> $PYNEUROCTL_SCRIPT"

# Check if ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$LOCAL_BIN_DIR:"* ]]; then
    print_warning "~/.local/bin is not in your PATH"
    
    # Detect shell and get config file
    SHELL_TYPE=$(detect_shell)
    CONFIG_FILE=$(get_shell_config_file "$SHELL_TYPE")
    
    print_info "Detected shell: $SHELL_TYPE"
    print_info "Config file: $CONFIG_FILE"
    
    # Check if PATH export already exists
    PATH_EXPORT_LINE='export PATH="$HOME/.local/bin:$PATH"'
    
    if [ -f "$CONFIG_FILE" ] && grep -q "HOME/.local/bin.*PATH" "$CONFIG_FILE"; then
        print_info "PATH export already exists in $CONFIG_FILE"
    else
        print_info "Adding ~/.local/bin to PATH in $CONFIG_FILE"
        
        # Create config file if it doesn't exist
        if [ ! -f "$CONFIG_FILE" ]; then
            touch "$CONFIG_FILE"
        fi
        
        # Add PATH export
        echo "" >> "$CONFIG_FILE"
        echo "# Added by PyNeuroctl setup" >> "$CONFIG_FILE"
        echo "$PATH_EXPORT_LINE" >> "$CONFIG_FILE"
        
        print_success "Added ~/.local/bin to PATH"
    fi
    
    print_info "Please run: source $CONFIG_FILE"
    print_info "Or restart your terminal to apply changes"
else
    print_success "~/.local/bin is already in your PATH"
fi

# Test the installation
print_info "Testing pyneuroctl installation..."

if command -v pyneuroctl >/dev/null 2>&1; then
    print_success "pyneuroctl is available in PATH"
    
    # Test basic functionality
    print_info "Testing basic functionality..."
    if pyneuroctl --help >/dev/null 2>&1; then
        print_success "pyneuroctl is working correctly!"
        
        echo ""
        print_info "🎉 Installation complete!"
        print_info "You can now use 'pyneuroctl' from anywhere in your terminal"
        print_info ""
        print_info "Try these commands:"
        echo "  pyneuroctl list                    # List available samples"
        echo "  pyneuroctl validate                # Validate sample configurations"
        echo "  pyneuroctl start mario-pizzeria    # Start Mario's Pizzeria sample"
        echo "  pyneuroctl --help                  # Show all available commands"
    else
        print_error "pyneuroctl command failed"
        exit 1
    fi
else
    print_warning "pyneuroctl not found in PATH after installation"
    print_info "You may need to restart your terminal or run:"
    print_info "  source $CONFIG_FILE"
    print_info "Then test with: pyneuroctl --help"
fi
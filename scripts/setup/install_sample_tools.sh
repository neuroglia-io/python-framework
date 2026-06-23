#!/bin/bash

##
# Install Neuroglia Sample Management Tools
##
# This script installs the sample management CLI tools to your system PATH:
# - infra: Manage shared infrastructure services
# - mario-pizzeria: Manage Mario's Pizzeria sample
# - simple-ui: Manage Simple UI sample
# - pyneuroctl: Main Neuroglia CLI tool

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

print_info "Setting up Neuroglia Sample Management Tools..."
print_info "Project root: $PROJECT_ROOT"
echo ""

# Check if scripts exist in project directory
PYNEUROCTL_SCRIPT="$PROJECT_ROOT/pyneuroctl"
INFRA_SCRIPT="$PROJECT_ROOT/infra"
MARIO_SCRIPT="$PROJECT_ROOT/mario-pizzeria"
SIMPLE_UI_SCRIPT="$PROJECT_ROOT/simple-ui"

check_script() {
    local script_path="$1"
    local script_name="$2"

    if [ ! -f "$script_path" ]; then
        print_error "$script_name not found at: $script_path"
        return 1
    fi
    return 0
}

# Validate all scripts exist
SCRIPTS_VALID=true
check_script "$PYNEUROCTL_SCRIPT" "pyneuroctl" || SCRIPTS_VALID=false
check_script "$INFRA_SCRIPT" "infra" || SCRIPTS_VALID=false
check_script "$MARIO_SCRIPT" "mario-pizzeria" || SCRIPTS_VALID=false
check_script "$SIMPLE_UI_SCRIPT" "simple-ui" || SCRIPTS_VALID=false

if [ "$SCRIPTS_VALID" = false ]; then
    print_error "Some scripts are missing. Please ensure you're in the correct project directory."
    exit 1
fi

# Make all scripts executable
chmod +x "$PYNEUROCTL_SCRIPT"
chmod +x "$INFRA_SCRIPT"
chmod +x "$MARIO_SCRIPT"
chmod +x "$SIMPLE_UI_SCRIPT"
print_success "Made all scripts executable"

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
echo ""

# Function to create or update symlink
create_symlink() {
    local script_path="$1"
    local tool_name="$2"
    local symlink_path="$LOCAL_BIN_DIR/$tool_name"

    if [ -L "$symlink_path" ]; then
        rm "$symlink_path"
        print_info "Removed existing $tool_name symlink"
    elif [ -f "$symlink_path" ]; then
        print_warning "File exists at $symlink_path (not a symlink)"
        print_info "Backing up existing file to $symlink_path.backup"
        mv "$symlink_path" "$symlink_path.backup"
    fi

    ln -s "$script_path" "$symlink_path"
    print_success "Created symlink: $tool_name -> $script_path"
}

# Install all tools
print_info "Installing tools to ~/.local/bin..."
create_symlink "$PYNEUROCTL_SCRIPT" "pyneuroctl"
create_symlink "$INFRA_SCRIPT" "infra"
create_symlink "$MARIO_SCRIPT" "mario-pizzeria"
create_symlink "$SIMPLE_UI_SCRIPT" "simple-ui"
echo ""

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
        echo "# Added by Neuroglia Sample Tools setup" >> "$CONFIG_FILE"
        echo "$PATH_EXPORT_LINE" >> "$CONFIG_FILE"

        print_success "Added ~/.local/bin to PATH"
    fi

    echo ""
    print_warning "Please run: source $CONFIG_FILE"
    print_warning "Or restart your terminal to apply changes"
else
    print_success "~/.local/bin is already in your PATH"
fi

echo ""
print_info "Testing installations..."
echo ""

# Test each tool
test_tool() {
    local tool_name="$1"
    local test_flag="${2:---help}"

    if command -v "$tool_name" >/dev/null 2>&1; then
        if $tool_name $test_flag >/dev/null 2>&1; then
            print_success "$tool_name is working correctly"
            return 0
        else
            print_warning "$tool_name found but may have issues"
            return 1
        fi
    else
        print_warning "$tool_name not found in PATH (restart terminal or source config)"
        return 1
    fi
}

# Test installations
ALL_WORKING=true
test_tool "pyneuroctl" "--help" || ALL_WORKING=false
test_tool "infra" "status" || ALL_WORKING=false
test_tool "mario-pizzeria" "status" || ALL_WORKING=false
test_tool "simple-ui" "status" || ALL_WORKING=false

echo ""
if [ "$ALL_WORKING" = true ]; then
    print_success "🎉 All tools installed successfully!"
else
    print_warning "Some tools may need terminal restart to work"
    print_info "Run: source $CONFIG_FILE"
    print_info "Or restart your terminal"
fi

echo ""
print_info "📚 Available Commands:"
echo ""
echo "  ${GREEN}pyneuroctl${NC}"
echo "    pyneuroctl list                    # List available samples"
echo "    pyneuroctl validate                # Validate configurations"
echo "    pyneuroctl start mario-pizzeria    # Start a sample"
echo "    pyneuroctl --help                  # Show all commands"
echo ""
echo "  ${GREEN}infra${NC}"
echo "    infra start                        # Start shared infrastructure"
echo "    infra stop                         # Stop shared infrastructure"
echo "    infra status                       # Check infrastructure status"
echo "    infra health                       # Health check all services"
echo "    infra logs [service]               # View logs"
echo "    infra --help                       # Show all commands"
echo ""
echo "  ${GREEN}mario-pizzeria${NC}"
echo "    mario-pizzeria start               # Start Mario's Pizzeria"
echo "    mario-pizzeria stop                # Stop Mario's Pizzeria"
echo "    mario-pizzeria logs                # View logs"
echo "    mario-pizzeria status              # Check status"
echo "    mario-pizzeria --help              # Show all commands"
echo ""
echo "  ${GREEN}simple-ui${NC}"
echo "    simple-ui start                    # Start Simple UI"
echo "    simple-ui stop                     # Stop Simple UI"
echo "    simple-ui logs                     # View logs"
echo "    simple-ui status                   # Check status"
echo "    simple-ui --help                   # Show all commands"
echo ""
print_info "🚀 Quick Start:"
echo "  1. Start shared infrastructure:  infra start"
echo "  2. Start Mario's Pizzeria:       mario-pizzeria start"
echo "  3. Start Simple UI:              simple-ui start"
echo ""

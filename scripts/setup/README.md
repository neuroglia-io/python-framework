# PyNeuroctl Setup

This directory contains setup scripts for the PyNeuroctl CLI tool.

## Quick Setup

To add `pyneuroctl` to your system PATH, run:

```bash
./scripts/setup/setup_pyneuroctl.sh
```

This will:

1. ✅ Create a symlink in `~/.local/bin/pyneuroctl`
2. ✅ Add `~/.local/bin` to your PATH (if not already present)
3. ✅ Test the installation
4. ✅ Show you how to use the CLI

## What Gets Installed

- **Shell Wrapper**: `/path/to/project/pyneuroctl` - A bash script that handles Python environment detection
- **System Symlink**: `~/.local/bin/pyneuroctl` - Points to the shell wrapper
- **PATH Entry**: Adds `~/.local/bin` to your shell's PATH

## Manual Installation

If you prefer manual setup:

1. **Make wrapper executable**:

   ```bash
   chmod +x ./pyneuroctl
   ```

2. **Create symlink**:

   ```bash
   ln -s "$(pwd)/pyneuroctl" ~/.local/bin/pyneuroctl
   ```

3. **Add to PATH** (if not already in PATH):

   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc  # or ~/.zshrc
   source ~/.bashrc  # or ~/.zshrc
   ```

## Testing Installation

After setup, test with:

```bash
pyneuroctl --help          # Show help
pyneuroctl list           # List available samples
pyneuroctl validate       # Validate sample configurations
```

## Environment Detection

The `pyneuroctl` wrapper automatically detects and uses the best Python environment:

1. 🔍 **Local venv**: `./venv/bin/python` (fastest)
2. 🔍 **Poetry**: `poetry run python` (if pyproject.toml exists)
3. 🔍 **Pyenv**: Checks for `pyneuro` environment
4. 🔍 **System Python**: `python3` or `python`

## Troubleshooting

### Command not found: pyneuroctl

```bash
# Check if symlink exists
ls -la ~/.local/bin/pyneuroctl

# Check if ~/.local/bin is in PATH
echo $PATH | grep ".local/bin"

# Restart shell or source profile
source ~/.bashrc  # or ~/.zshrc
```

### Permission denied

```bash
# Make wrapper executable
chmod +x ./pyneuroctl
```

### Python environment issues

```bash
# Test wrapper directly
./pyneuroctl --help

# Check Python detection
./pyneuroctl list --verbose
```

## Legacy Scripts

- `add_to_path.sh` - Forwards to `setup_pyneuroctl.sh` for compatibility

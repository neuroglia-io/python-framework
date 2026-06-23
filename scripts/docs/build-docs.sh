#!/bin/bash

# MkDocs Build Script for Pyneuro Project
# Builds documentation site with Mermaid diagrams and ADR integration

set -euo pipefail

echo "🚀 Building Pyneuro Documentation"
echo "===================================="

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${CYAN}[DOCS]${NC} $1"
}

# Check if we're in the right directory
if [[ ! -f "mkdocs.yml" ]]; then
    print_error "mkdocs.yml not found. Please run this script from the project root."
    exit 1
fi

# Check for Python environment
print_status "Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PYTHON_VERSION=$(python3 --version 2>&1)
    print_success "Found Python: $PYTHON_VERSION"
else
    print_error "Python 3 is not installed or not in PATH."
    exit 1
fi

# Function to install packages via pip if Poetry is not available
install_with_pip() {
    print_status "Installing MkDocs dependencies with pip..."
    $PYTHON_CMD -m pip install --user \
        mkdocs \
        mkdocs-material \
        mkdocs-mermaid2-plugin \
        mkdocs-awesome-pages-plugin \
        pymdown-extensions
}

# Check for Poetry or fallback to pip
if command -v poetry &> /dev/null; then
    print_status "Poetry detected. Using Poetry for dependency management..."
    
    # Check if pyproject.toml exists, create if not
    if [[ ! -f "pyproject.toml" ]]; then
        print_status "Creating pyproject.toml for MkDocs dependencies..."
        cat > pyproject.toml << 'EOF'
[tool.poetry]
name = "cml-lablets"
version = "0.1.0"
description = "Pyneuro Project Documentation"
authors = ["Systems Architect <architect@example.com>"]
package-mode = false

[tool.poetry.dependencies]
python = "^3.8"

[tool.poetry.group.docs.dependencies]
mkdocs = "^1.5.3"
mkdocs-material = "^9.4.6"
mkdocs-mermaid2-plugin = "^1.1.1"
mkdocs-awesome-pages-plugin = "^2.9.2"
pymdown-extensions = "^10.3.1"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
EOF
        print_success "Created pyproject.toml"
    fi
    
    print_status "Installing/updating documentation dependencies..."
    poetry install --with docs --no-interaction
    
    MKDOCS_CMD="poetry run mkdocs"
else
    print_warning "Poetry not found. Falling back to pip installation..."
    install_with_pip
    MKDOCS_CMD="$PYTHON_CMD -m mkdocs"
fi

# Validate MkDocs installation
print_status "Validating MkDocs installation..."
if $MKDOCS_CMD --version &> /dev/null; then
    MKDOCS_VERSION=$($MKDOCS_CMD --version 2>&1)
    print_success "MkDocs is available: $MKDOCS_VERSION"
else
    print_error "MkDocs installation failed or not working."
    exit 1
fi

# Pre-build checks
print_header "Pre-build validation"

# Check for required directories
for dir in "docs" "docs/adr"; do
    if [[ ! -d "$dir" ]]; then
        print_error "Required directory '$dir' not found."
        exit 1
    fi
done

# Check for main documentation files
REQUIRED_FILES=("docs/index.md" "docs/README.md" "docs/architecture.md")
for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        print_warning "Recommended file '$file' not found. Creating placeholder..."
        mkdir -p "$(dirname "$file")"
        echo "# $(basename "$file" .md | tr '[:lower:]' '[:upper:]')" > "$file"
        echo "" >> "$file"
        echo "This page is under construction." >> "$file"
    fi
done

# Count content files
MD_COUNT=$(find docs -name "*.md" -type f | wc -l)
ADR_COUNT=$(find docs/adr -name "ADR-*.md" -type f 2>/dev/null | wc -l || echo "0")
MERMAID_COUNT=$(find docs -name "*.md" -exec grep -l '```mermaid' {} \; 2>/dev/null | wc -l || echo "0")

print_status "Content summary:"
echo "  📄 Markdown files: $MD_COUNT"
echo "  📋 ADR files: $ADR_COUNT"  
echo "  📊 Files with Mermaid diagrams: $MERMAID_COUNT"

# Generate ADR index if adrctl is available
if [[ -x "./adrctl" ]]; then
    print_status "Updating ADR index..."
    ./adrctl index
    print_success "ADR index updated"
else
    print_warning "adrctl not found or not executable. ADR index may be outdated."
fi

# Build documentation
print_header "Building documentation site"
print_status "Running MkDocs build with clean flag..."

if $MKDOCS_CMD build --clean; then
    print_success "Documentation built successfully!"
    
    # Validate build output
    if [[ -d "site" ]]; then
        HTML_COUNT=$(find site -name "*.html" -type f | wc -l)
        SITE_SIZE=$(du -sh site | cut -f1)
        print_success "Generated $HTML_COUNT HTML files ($SITE_SIZE total)"
        
        # Check for Mermaid content in generated HTML
        if [[ $MERMAID_COUNT -gt 0 ]]; then
            MERMAID_HTML_COUNT=$(find site -name "*.html" -exec grep -l 'mermaid' {} \; 2>/dev/null | wc -l || echo "0")
            if [[ $MERMAID_HTML_COUNT -gt 0 ]]; then
                print_success "Mermaid diagrams rendered in $MERMAID_HTML_COUNT HTML files"
            else
                print_warning "Mermaid diagrams found in source but not in generated HTML"
            fi
        fi
        
        # Check for search index
        if [[ -f "site/search/search_index.json" ]]; then
            print_success "Search index generated successfully"
        else
            print_warning "Search index not found"
        fi
        
        # Security check for external links
        EXTERNAL_LINKS=$(find site -name "*.html" -exec grep -ho 'https\?://[^"'\'']*' {} \; 2>/dev/null | sort -u | wc -l || echo "0")
        if [[ $EXTERNAL_LINKS -gt 0 ]]; then
            print_status "Found $EXTERNAL_LINKS unique external links"
        fi
        
    else
        print_error "Site directory was not created"
        exit 1
    fi
    
else
    print_error "Documentation build failed!"
    print_error "Check the output above for specific errors."
    exit 1
fi

# Post-build actions
print_header "Post-build actions"

# Create .nojekyll file for GitHub Pages compatibility
echo "" > site/.nojekyll
print_status "Created .nojekyll file for GitHub Pages compatibility"

# Generate build info
cat > site/build-info.json << EOF
{
  "build_time": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "build_date": "$(date -u +"%Y-%m-%d")",
  "mkdocs_version": "$($MKDOCS_CMD --version 2>&1 | head -n1)",
  "content_stats": {
    "markdown_files": $MD_COUNT,
    "adr_files": $ADR_COUNT,
    "mermaid_diagrams": $MERMAID_COUNT,
    "html_files": $HTML_COUNT,
    "site_size": "$SITE_SIZE"
  }
}
EOF

print_success "Generated build information"

# Summary
echo ""
print_success "📚 Documentation build completed successfully! 🎉"
echo ""
echo "📁 Site files: ./site/"
echo "🌐 To serve locally: $MKDOCS_CMD serve"
echo "🔍 To serve with live reload: $MKDOCS_CMD serve --dev-addr localhost:8000"
echo "🚀 To deploy to GitHub Pages: $MKDOCS_CMD gh-deploy"
echo ""
echo "📊 Build Statistics:"
echo "   • Total pages: $HTML_COUNT"
echo "   • ADR documents: $ADR_COUNT" 
echo "   • Interactive diagrams: $MERMAID_COUNT"
echo "   • Site size: $SITE_SIZE"
echo ""

# Optional: Start local server
if [[ "${1:-}" == "--serve" ]]; then
    print_header "Starting local development server"
    print_status "Opening documentation at http://localhost:8000"
    print_status "Press Ctrl+C to stop the server"
    echo ""
    $MKDOCS_CMD serve --dev-addr localhost:8000
fi
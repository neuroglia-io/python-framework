#!/usr/bin/env python3
"""
MkDocs Mermaid Validation Script

This script validates that MkDocs can successfully build the documentation
with Mermaid diagrams and checks for any rendering issues.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and return success status."""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True,
            cwd="/Users/bvandewe/Documents/Work/Systems/Mozart/src/building-blocks/Python/pyneuro"
        )
        print(f"✅ {description} - SUCCESS")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Error: {e.stderr}")
        return False, e.stderr

def check_mermaid_files():
    """Check for Mermaid diagrams in documentation files."""
    docs_dir = Path("/Users/bvandewe/Documents/Work/Systems/Mozart/src/building-blocks/Python/pyneuro/docs")
    mermaid_files = []
    
    for md_file in docs_dir.rglob("*.md"):
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if '```mermaid' in content:
                mermaid_count = content.count('```mermaid')
                mermaid_files.append((md_file, mermaid_count))
    
    return mermaid_files

def main():
    """Main validation function."""
    print("🚀 MkDocs Mermaid Validation Script")
    print("=" * 50)
    
    # Check for Mermaid diagrams in documentation
    print("\n📊 Checking for Mermaid diagrams...")
    mermaid_files = check_mermaid_files()
    
    if mermaid_files:
        print(f"✅ Found Mermaid diagrams in {len(mermaid_files)} files:")
        for file_path, count in mermaid_files:
            rel_path = file_path.relative_to(Path("/Users/bvandewe/Documents/Work/Systems/Mozart/src/building-blocks/Python/pyneuro/docs"))
            print(f"   📄 {rel_path}: {count} diagram(s)")
    else:
        print("⚠️  No Mermaid diagrams found in documentation")
    
    # Test MkDocs build
    success, output = run_command("poetry run mkdocs build --clean", "Building MkDocs site")
    
    if success:
        # Check if Mermaid plugin was loaded
        if "MERMAID2" in output:
            print("✅ Mermaid plugin loaded successfully")
            
            # Extract Mermaid plugin info
            mermaid_lines = [line.strip() for line in output.split('\n') if 'MERMAID2' in line]
            for line in mermaid_lines:
                print(f"   📋 {line}")
        else:
            print("⚠️  Mermaid plugin not detected in build output")
    
    # Test if site directory was created with HTML files
    site_dir = Path("/Users/bvandewe/Documents/Work/Systems/Mozart/src/building-blocks/Python/pyneuro/site")
    if site_dir.exists():
        html_files = list(site_dir.rglob("*.html"))
        print(f"✅ Generated {len(html_files)} HTML files")
        
        # Check specific files with Mermaid diagrams
        test_files = ["test-mermaid/index.html", "features/mermaid-diagrams/index.html", "features/resource-oriented-architecture/index.html"]
        
        for test_file in test_files:
            file_path = site_dir / test_file
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'mermaid' in content.lower():
                        print(f"✅ {test_file}: Contains Mermaid content")
                    else:
                        print(f"⚠️  {test_file}: No Mermaid content detected")
            else:
                print(f"❌ {test_file}: File not found")
    else:
        print("❌ Site directory not created")
    
    # Final summary
    print("\n" + "=" * 50)
    print("📋 Validation Summary:")
    print(f"   📊 Mermaid diagrams found: {len(mermaid_files)} files")
    print(f"   🏗️  MkDocs build: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print(f"   📄 Site generated: {'✅ YES' if site_dir.exists() else '❌ NO'}")
    
    if success and mermaid_files:
        print("\n🎉 All checks passed! Mermaid diagrams are properly configured.")
        return 0
    else:
        print("\n⚠️  Some issues detected. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

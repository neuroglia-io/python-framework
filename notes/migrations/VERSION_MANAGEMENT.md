# Version Management Checklist

## CRITICAL: Always Update ALL Version References

When releasing a new version, **ALL** of the following must be updated:

### 1. pyproject.toml

```toml
[tool.poetry]
version = "X.Y.Z"
```

### 2. src/neuroglia/**init**.py

```python
__version__ = "X.Y.Z"
```

### 3. CHANGELOG.md

```markdown
## [X.Y.Z] - YYYY-MM-DD
```

## Release Process

### Step-by-Step Checklist

- [ ] **Update `pyproject.toml`** - Set version to X.Y.Z
- [ ] **Update `src/neuroglia/__init__.py`** - Set `__version__ = "X.Y.Z"`
- [ ] **Update `CHANGELOG.md`** - Add entry for version X.Y.Z
- [ ] **Run tests** - Ensure all tests pass
- [ ] **Commit changes** - `git commit -m "chore: Bump version to X.Y.Z"`
- [ ] **Create tag** - `git tag -a vX.Y.Z -m "Release vX.Y.Z: <summary>"`
- [ ] **Push to GitHub** - `git push origin main && git push origin vX.Y.Z`
- [ ] **Build distribution** - `rm -rf dist/ && poetry build`
- [ ] **Publish to PyPI** - `poetry publish`
- [ ] **Verify installation** - `pip install --upgrade neuroglia-python`
- [ ] **Check version** - `python -c "import neuroglia; print(neuroglia.__version__)"`

## Version Attribute Purpose

The `__version__` attribute in `src/neuroglia/__init__.py` serves multiple purposes:

1. **Runtime Version Check**: Users can check the installed version

   ```python
   import neuroglia
   print(neuroglia.__version__)  # Should output: "X.Y.Z"
   ```

2. **Programmatic Version Detection**: Applications can verify compatibility

   ```python
   import neuroglia
   from packaging import version

   if version.parse(neuroglia.__version__) < version.parse("0.4.3"):
       raise RuntimeError("Requires neuroglia >= 0.4.3")
   ```

3. **Debugging and Support**: Error reports can include version information

   ```python
   print(f"Neuroglia version: {neuroglia.__version__}")
   ```

## PyPI Constraints

**IMPORTANT**: PyPI does **not** allow re-uploading the same version, even if files change.

If you need to fix a version already published:

1. **DO NOT** try to republish the same version
2. **DO** create a new patch version (e.g., 0.4.3 → 0.4.4)
3. Document the issue in CHANGELOG under the new version

## What Happened with v0.4.3

### Initial Publication (Missing **version** update)

- ✅ `pyproject.toml` updated to 0.4.3
- ❌ `src/neuroglia/__init__.py` still at 0.1.8
- Published to PyPI

### Fix Attempt

- ✅ Updated `src/neuroglia/__init__.py` to 0.4.3
- ✅ Committed and pushed to GitHub
- ❌ Cannot republish to PyPI (version already exists)

### Current State (v0.4.3)

- **PyPI package**: Contains old `__version__ = "0.1.8"` in code
- **GitHub tag v0.4.3**: Contains correct `__version__ = "0.4.3"`
- **Impact**: Users who do `import neuroglia; print(neuroglia.__version__)` will see "0.1.8" instead of "0.4.3"

### Resolution Options

**Option 1: Live with it (RECOMMENDED)**

- The package metadata is correct (shows 0.4.3 in `pip show`)
- Only the internal `__version__` attribute is outdated
- Fix it properly in v0.4.4

**Option 2: Immediate patch release (v0.4.4)**

- Bump to 0.4.4 with **only** the `__version__` fix
- CHANGELOG: "Fixed internal version attribute"
- Rebuild and republish

## Best Practice Going Forward

Use this Git pre-commit hook to validate version consistency:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Extract versions
PYPROJECT_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
INIT_VERSION=$(grep '__version__ = ' src/neuroglia/__init__.py | cut -d'"' -f2)

if [ "$PYPROJECT_VERSION" != "$INIT_VERSION" ]; then
    echo "ERROR: Version mismatch!"
    echo "  pyproject.toml: $PYPROJECT_VERSION"
    echo "  __init__.py:    $INIT_VERSION"
    echo ""
    echo "Please update both to match before committing."
    exit 1
fi

echo "✅ Version check passed: $PYPROJECT_VERSION"
```

## Verification Commands

After publishing, verify the version:

```bash
# Check package metadata
pip show neuroglia-python | grep Version

# Check runtime version (this was broken in v0.4.3 PyPI package)
python -c "import neuroglia; print(neuroglia.__version__)"

# Check GitHub tag
git show v0.4.3:src/neuroglia/__init__.py | grep __version__
```

## Summary for v0.4.3

- ✅ Package published to PyPI as v0.4.3
- ✅ GitHub tag v0.4.3 has correct `__version__`
- ⚠️ PyPI package has old `__version__ = "0.1.8"` (cannot fix without new release)
- 📝 Will be corrected in next release

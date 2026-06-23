# Parcel Configuration: Glob Pattern for Scripts

**Date:** October 22, 2025
**Status:** ✅ Complete
**Type:** Build Configuration Improvement

---

## Overview

Updated Parcel build configuration to use glob patterns (`*.js`) instead of explicitly listing individual script files. This makes the build process more scalable and reduces maintenance overhead.

---

## Change Made

### package.json

**Before:**

```json
{
  "scripts": {
    "dev": "parcel watch 'src/scripts/app.js' 'src/scripts/menu.js' 'src/styles/main.scss' --dist-dir ../static/dist --public-url /static/dist",
    "build": "parcel build 'src/scripts/app.js' 'src/scripts/menu.js' 'src/styles/main.scss' --dist-dir ../static/dist --public-url /static/dist --no-source-maps"
  }
}
```

**After:**

```json
{
  "scripts": {
    "dev": "parcel watch 'src/scripts/*.js' 'src/styles/main.scss' --dist-dir ../static/dist --public-url /static/dist",
    "build": "parcel build 'src/scripts/*.js' 'src/styles/main.scss' --dist-dir ../static/dist --public-url /static/dist --no-source-maps"
  }
}
```

---

## Benefits

### 1. **Automatic Script Discovery**

- ✅ All `.js` files in `src/scripts/` are automatically included
- ✅ No need to manually update `package.json` when adding new scripts
- ✅ Reduces risk of forgetting to add new scripts to the build

### 2. **Better Scalability**

- ✅ Works well as the number of scripts grows
- ✅ Single pattern handles all current and future scripts
- ✅ No configuration bloat with long file lists

### 3. **Reduced Maintenance**

- ✅ One less thing to remember when adding features
- ✅ Consistent pattern across projects
- ✅ Self-documenting: "build all scripts in this directory"

### 4. **Developer Experience**

- ✅ Easier onboarding (no need to explain build config updates)
- ✅ Faster feature development (just drop in new JS files)
- ✅ Less context switching between code and config

---

## Current Scripts in Scope

The glob pattern `src/scripts/*.js` currently matches:

```
src/scripts/
├── app.js          # Main application entry point
├── bootstrap.js    # Bootstrap initialization
├── common.js       # Shared utilities
└── menu.js         # Menu page cart functionality
```

All four scripts will be compiled to:

```
static/dist/scripts/
├── app.js          # Bundled and minified
├── bootstrap.js    # Bundled and minified
├── common.js       # Bundled and minified
└── menu.js         # Bundled and minified
```

---

## How It Works

### Glob Pattern Matching

Parcel uses the glob pattern `src/scripts/*.js` to find all files:

1. **`*`**: Matches any filename
2. **`.js`**: Only includes JavaScript files
3. **No subdirectories**: Only matches files directly in `src/scripts/`

### Entry Points

Each matched file becomes an **entry point** for Parcel:

- Parcel processes each file independently
- Each file gets its own bundle (code splitting)
- Each file can have its own dependencies

### Output Structure

Parcel preserves the directory structure:

- Input: `src/scripts/menu.js`
- Output: `../static/dist/scripts/menu.js`

---

## Future Considerations

### Subdirectories

If we need to organize scripts into subdirectories:

```
src/scripts/
├── pages/
│   ├── menu.js
│   ├── orders.js
│   └── profile.js
├── components/
│   ├── cart.js
│   └── toast.js
└── app.js
```

Update glob pattern to include subdirectories:

```json
{
  "scripts": {
    "dev": "parcel watch 'src/scripts/**/*.js' 'src/styles/main.scss' ...",
    "build": "parcel build 'src/scripts/**/*.js' 'src/styles/main.scss' ..."
  }
}
```

**Note:** `**/*.js` matches files at any depth.

### Excluding Files

If we need to exclude certain files (e.g., test files):

```json
{
  "scripts": {
    "dev": "parcel watch 'src/scripts/*.js' '!src/scripts/*.test.js' ...",
    "build": "parcel build 'src/scripts/*.js' '!src/scripts/*.test.js' ..."
  }
}
```

**Note:** `!` prefix negates the pattern.

### Module Federation

For very large applications, consider module federation:

- Single entry point (`app.js`)
- Dynamic imports for page-specific code
- Parcel will automatically code-split

```javascript
// app.js
if (window.location.pathname === "/menu") {
  import("./menu.js").then(module => module.init());
}
```

---

## Testing the Configuration

### Verify Glob Pattern Matching

```bash
# Preview which files will be matched
ls -1 samples/mario-pizzeria/ui/src/scripts/*.js

# Expected output:
# app.js
# bootstrap.js
# common.js
# menu.js
```

### Test Build

```bash
cd samples/mario-pizzeria/ui

# Clean previous builds
npm run clean

# Run dev build
npm run dev

# Check output
ls -lh ../static/dist/scripts/

# Expected output:
# app.js
# bootstrap.js
# common.js
# menu.js
```

### Verify in Browser

1. Start the app: `make sample-mario-bg`
2. Open DevTools → Network tab
3. Visit pages and verify scripts load:
   - All pages: `/static/dist/scripts/app.js`
   - Menu page: `/static/dist/scripts/menu.js`

---

## Migration Notes

### No Breaking Changes

This change is **backward compatible**:

- ✅ All existing scripts still compile
- ✅ Output paths remain the same
- ✅ Templates don't need updates
- ✅ No functional changes

### Adding New Scripts

**Old Process:**

1. Create `src/scripts/newpage.js`
2. Update `package.json` to include `newpage.js`
3. Run build
4. Reference in template

**New Process:**

1. Create `src/scripts/newpage.js`
2. ~~Update `package.json`~~ (automatic!)
3. Run build
4. Reference in template

---

## Best Practices

### File Naming

Use descriptive, page-specific names:

- ✅ `menu.js` - Clear and specific
- ✅ `order-tracking.js` - Hyphenated for multi-word
- ✅ `customer-profile.js` - Page-specific functionality
- ❌ `script1.js` - Non-descriptive
- ❌ `temp.js` - Unclear purpose

### File Organization

Keep `src/scripts/` focused on **entry points**:

- Entry points: Page-specific scripts that are referenced in templates
- Utilities: Move to `src/lib/` or `src/utils/` (not compiled as entry points)
- Components: Move to `src/components/` (imported by entry points)

```
src/
├── scripts/          # Entry points (compiled by glob pattern)
│   ├── app.js
│   └── menu.js
├── lib/             # Utilities (imported by scripts)
│   ├── api.js
│   └── helpers.js
└── components/      # Reusable components (imported by scripts)
    ├── cart.js
    └── toast.js
```

### Dependency Management

**For shared code:**

1. Create utility/component file outside `src/scripts/`
2. Import in entry points that need it
3. Parcel will bundle dependencies automatically

```javascript
// src/scripts/menu.js (entry point)
import { showToast } from "../lib/notifications.js";
import { Cart } from "../components/cart.js";

// Use utilities
showToast("Item added!", "success");
```

---

## Summary

✅ **Glob pattern configured** for automatic script discovery
✅ **No breaking changes** - backward compatible
✅ **Better scalability** - handles growth gracefully
✅ **Reduced maintenance** - one less config to update
✅ **Developer friendly** - just add files and go

**Impact:** New scripts are automatically included in builds without manual configuration updates. This reduces friction when adding new features and makes the project more maintainable as it grows.

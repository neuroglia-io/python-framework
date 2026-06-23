# Management Dashboard - Build and Deployment Guide

## Quick Start

### 1. Build UI Assets

```bash
cd samples/mario-pizzeria/ui
npm install  # If first time or after package.json changes
npm run build
```

### 2. Restart Application

```bash
cd ../../..  # Back to pyneuro root
./mario-docker.sh restart
```

### 3. Test Management Dashboard

Navigate to: http://localhost:3000/management

---

## What Was Changed

### Files Created

- ✅ `ui/src/styles/management.scss` - Management dashboard styles
- ✅ `ui/src/scripts/management-dashboard.js` - Dashboard JavaScript with improved SSE
- ✅ `MANAGEMENT_DASHBOARD_STYLES_SCRIPTS_EXTRACTION.md` - Complete documentation
- ✅ `MANAGEMENT_SSE_DECIMAL_FIX.md` - SSE JSON serialization fix

### Files Modified

- ✅ `ui/src/styles/main.scss` - Added `@import "management";`
- ✅ `ui/templates/management/dashboard.html` - Removed inline styles/scripts
- ✅ `ui/controllers/management_controller.py` - Fixed Decimal JSON serialization

---

## Critical Fixes

### SSE Decimal Serialization Fix ⚠️

**Problem**: MongoDB returns `Decimal` objects which aren't JSON serializable

**Error in logs**:

```
ERROR: Object of type Decimal is not JSON serializable
```

**Impact**: SSE stream failing every 5 seconds, connection indicator flashing

**Solution**: Convert `Decimal` to `float` before JSON serialization

**Status**: ✅ FIXED - See `MANAGEMENT_SSE_DECIMAL_FIX.md` for details

---

## Key Improvements

### 1. SSE Connection Indicator Fix

**Problem**: Indicator was flashing red/green on every event

**Solution**: Health check with 3-miss threshold

- Stays **GREEN** unless 3+ consecutive events are missed
- Checks every 2 seconds
- 7-second buffer before considering an event "missed"

**Result**: Stable connection indicator that only shows red when truly disconnected

### 2. Code Organization

**Before**:

- 100+ lines of inline CSS in template
- 90+ lines of inline JavaScript in template

**After**:

- Clean template with external asset references
- SASS with variables, nesting, and proper organization
- Modular JavaScript with class-based architecture

---

## Development Workflow

### Watch Mode (Hot Reloading)

```bash
cd samples/mario-pizzeria/ui
npm run dev
```

Leave this running while developing. Changes to SASS/JS files will automatically rebuild.

### Production Build

```bash
cd samples/mario-pizzeria/ui
npm run build
```

Creates optimized, minified assets in `ui/static/dist/`

### Clean Build

```bash
cd samples/mario-pizzeria/ui
npm run clean
npm run build
```

---

## Verify Build Output

After building, check that files exist:

```bash
ls -la ui/static/dist/scripts/
# Should include: management-dashboard.js

ls -la ui/static/dist/styles/
# Should include: main.css (contains management styles)
```

---

## Testing Checklist

- [ ] Dashboard loads without errors
- [ ] All styles applied correctly
- [ ] Connection indicator shows green on load
- [ ] Connection indicator stays green while receiving events
- [ ] Connection indicator only turns red after 3+ missed events
- [ ] Real-time updates work (metrics change when orders placed)
- [ ] Values animate (scale effect) when changing
- [ ] Reconnection works after server restart

---

## Next Steps

1. Build UI assets with `npm run build`
2. Restart application
3. Test management dashboard thoroughly
4. Proceed to Phase 2 (Analytics) implementation

---

## Need Help?

See `MANAGEMENT_DASHBOARD_STYLES_SCRIPTS_EXTRACTION.md` for detailed documentation.

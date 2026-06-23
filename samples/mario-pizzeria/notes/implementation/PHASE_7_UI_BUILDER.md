# UI Auto-Rebuild Setup Summary

## What Was Done

Added a dedicated **`ui-builder`** Docker service that automatically rebuilds UI assets on file changes.

## Architecture

```
┌─────────────────────┐
│   ui-builder        │
│  (Node.js Alpine)   │
│                     │
│  Parcel watch mode  │◄──── Watches src/scripts/ & src/styles/
│  npm run dev        │
│                     │
│  Writes to:         │
│  static/dist/       │
└──────────┬──────────┘
           │
           │ Shared Volume
           │
┌──────────▼──────────┐
│ mario-pizzeria-app  │
│   (Python App)      │
│                     │
│  Serves /static/    │◄──── Serves built assets
│  FastAPI + Uvicorn  │
└─────────────────────┘
```

## Benefits

✅ **Instant feedback** - UI changes rebuild in < 200ms
✅ **No manual builds** - Just save the file
✅ **Keeps Python hot reload** - Both work independently
✅ **Clean separation** - UI build isolated from app container
✅ **Zero config** - Works out of the box with `docker-compose up`

## How to Use

```bash
# Start everything (including UI builder)
docker-compose -f docker-compose.mario.yml up -d

# Watch UI builder activity
docker logs -f mario-pizzeria-ui-builder-1

# Make changes to JS/SCSS files
# → Parcel automatically rebuilds in < 200ms
# → Python app serves updated assets
# → Browser sees new changes immediately
```

## File Changes

### `docker-compose.mario.yml`

Added new service:

```yaml
ui-builder:
  image: node:20-alpine
  working_dir: /app/samples/mario-pizzeria/ui
  command: npm run dev
  volumes:
    - .:/app
    - /app/samples/mario-pizzeria/ui/node_modules
  entrypoint: >
    sh -c "
    npm install &&
    npm run dev
    "
```

## Testing Results

**Before:** Manual `npm run build` required for every UI change (6s rebuild)
**After:** Automatic rebuild on save (170ms incremental rebuild)

```
# Test performed:
1. Modified ui/src/scripts/app.js
2. Parcel detected change automatically
3. Rebuilt in 170ms
4. Assets available immediately
```

## Key Design Decisions

1. **Separate container** vs bundling in main app

   - Cleaner separation of concerns
   - Follows Docker best practices
   - Easier to debug

2. **Watch mode** vs build-on-startup

   - Instant feedback during development
   - No need to restart containers

3. **Anonymous volume for node_modules**
   - Faster npm install (uses Docker layer caching)
   - Prevents platform conflicts

## Alternative Approaches Considered

❌ **Multi-stage Dockerfile** - Too slow, loses hot reload
❌ **Node in Python container** - Bloated image, complex
✅ **Separate Node service** - Clean, fast, maintainable

## Documentation Added

- `UI_BUILD.md` - Complete UI build system documentation

# UI Build System

## Overview

Mario's Pizzeria UI uses **Parcel 2** as a zero-config bundler to compile JavaScript and SCSS assets.

## Docker Setup (Recommended)

The UI automatically rebuilds on file changes using a dedicated `ui-builder` service:

```bash
# Start all services (including UI builder)
docker-compose -f docker-compose.mario.yml up -d

# Watch UI builder logs
docker logs -f mario-pizzeria-ui-builder-1

# Stop all services
docker-compose -f docker-compose.mario.yml down
```

### How It Works

1. **`ui-builder` service** runs `npm run dev` in watch mode
2. Monitors `src/scripts/` and `src/styles/` for changes
3. Automatically rebuilds to `../static/dist/`
4. Python app serves built assets via `/static/` mount
5. **Hot reload**: Changes reflected instantly (< 1s rebuild)

### Built Assets

```
samples/mario-pizzeria/ui/static/dist/
├── app.js          # Compiled JavaScript
├── main.css        # Compiled CSS with Bootstrap
└── *.map           # Source maps (dev only)
```

## Local Development (Alternative)

If you prefer running UI build outside Docker:

```bash
cd samples/mario-pizzeria/ui

# Install dependencies
npm install

# Watch mode (auto-rebuild on changes)
npm run dev

# Production build (minified, no source maps)
npm run build

# Clean build artifacts
npm run clean
```

## File Structure

```
ui/
├── src/
│   ├── scripts/
│   │   └── app.js          # Entry point for JS
│   └── styles/
│       └── main.scss       # Entry point for SCSS
├── static/
│   └── dist/              # Build output (git-ignored)
├── templates/             # Jinja2 templates
├── package.json
└── .gitignore
```

## NPM Scripts

- **`npm run dev`** - Watch mode with source maps
- **`npm run build`** - Production build (minified)
- **`npm run clean`** - Remove build artifacts

## Parcel Configuration

Configured via `package.json` scripts:

- **Entry files**: `src/scripts/app.js`, `src/styles/main.scss`
- **Output directory**: `../static/dist`
- **Public URL**: `/static/dist`
- **Watch mode**: Enabled in `dev` script

## Dependencies

- **Bootstrap 5.3.2** - UI framework
- **Parcel 2.10.3** - Bundler
- **Sass 1.69.5** - CSS preprocessor

## Troubleshooting

### Assets not updating?

```bash
# Restart UI builder
docker-compose -f docker-compose.mario.yml restart ui-builder

# Or rebuild from scratch
npm run clean && npm run build
```

### Port conflicts?

The UI builder doesn't expose ports—it only writes files to disk.

### Build fails?

Check logs:

```bash
docker logs mario-pizzeria-ui-builder-1
```

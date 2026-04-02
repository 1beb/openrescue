# OpenRescue Settings App — Design

## Overview

A Next.js web application deployed on cubibox alongside the existing LGTM stack. It provides a centralized UI for managing productivity categories, device settings, and viewing Grafana dashboards — all behind Tailscale authentication.

## Architecture

- Next.js 14+ (App Router) with TypeScript
- Catalyst UI Kit components (Tailwind CSS Pro)
- SQLite via better-sqlite3 for config persistence
- Tailscale serve for TLS + auth headers (tailnet-only, not public)
- Grafana proxied through the app (not directly exposed)
- Agents poll the app for config via API

Deployed as a Docker container in the existing docker-compose.yml on cubibox. Grafana's external port removed — only accessible through the Next.js proxy.

## Data Model

```sql
devices (
    id TEXT PRIMARY KEY,
    hostname TEXT NOT NULL,
    display_name TEXT,
    last_seen TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

category_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

device_exclusions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL REFERENCES devices(id),
    keyword TEXT NOT NULL,
    UNIQUE(device_id, keyword)
)

settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT REFERENCES devices(id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    UNIQUE(device_id, key)
)
```

## Agent Registration

On first startup, the agent generates a UUID, stores it at `~/.local/share/openrescue/device_id`, and POSTs to `/api/devices/register` with `{id, hostname}`. Subsequent config polls use the UUID.

## API Routes

```
POST /api/devices/register           — agent registers {id, hostname}
GET  /api/config/:deviceId           — agent polls merged config

GET  /api/devices                    — list devices (UI)
PUT  /api/devices/:id                — update display_name

GET  /api/categories                 — list all category rules
POST /api/categories                 — create rule {keyword, category}
PUT  /api/categories/:id             — update rule
DELETE /api/categories/:id           — delete rule

GET  /api/devices/:id/exclusions     — list exclusions for device
POST /api/devices/:id/exclusions     — add exclusion {keyword}
DELETE /api/devices/:id/exclusions/:eid — remove exclusion

GET  /api/settings                   — list global settings
GET  /api/settings/:deviceId         — device settings merged with global
PUT  /api/settings/:key              — update global setting
PUT  /api/settings/:deviceId/:key    — update device-specific setting
```

### Config endpoint response

`GET /api/config/:deviceId` returns:

```json
{
  "categories": {
    "very_productive": ["code", "neovim"],
    "productive": ["github.com"],
    "distracting": ["slack"],
    "very_distracting": ["reddit.com"]
  },
  "exclusions": ["personal-app"],
  "settings": {
    "retention_days": 10,
    "poll_interval_seconds": 5,
    "idle_threshold_seconds": 300
  }
}
```

Categories from category_rules (global), exclusions from device_exclusions (per-device), settings are global merged with device-specific overrides.

## UI Pages

Catalyst sidebar layout as the application shell.

### Dashboard (`/`)

Grafana Activity Overview dashboard embedded via iframe, proxied through `/grafana/*`. Landing page.

### Categories (`/categories`)

Table of all category rules (keyword, productivity level). Color-coded badges per level. Add/edit/delete inline. Separate "Uncategorized" tab for triage.

### Devices (`/devices`)

Table of registered devices (display name, hostname, last seen). Click to manage exclusion list and device-specific setting overrides.

### Settings (`/settings`)

Global settings form: retention_days, poll_interval_seconds, idle_threshold_seconds.

### Sidebar Navigation

- Dashboard (chart icon)
- Categories (tag icon)
- Devices (computer icon)
- Settings (cog icon)

## Authentication

Tailscale serve injects `Tailscale-User-Login` and `Tailscale-User-Name` headers. Next.js middleware checks for these on every request. Missing headers return 401. Tailnet-only access — not exposed to the internet.

## Environment Variables

`.env.local` on cubibox:

```
GRAFANA_URL=http://<tailscale-ip>:3000
DATABASE_PATH=/data/openrescue-settings.db
TAILSCALE_AUTH_ENABLED=true
```

Grafana URL uses Tailscale IP from env — never hardcoded, never in logs.

## Deployment

New service in docker-compose.yml:

```yaml
openrescue-web:
  build: ./web
  ports:
    - "3001:3000"
  environment:
    - GRAFANA_URL=${GRAFANA_URL}
    - DATABASE_PATH=/data/settings.db
    - TAILSCALE_AUTH_ENABLED=true
  volumes:
    - web-data:/data
  depends_on:
    - grafana
```

Grafana's external port removed. Tailscale serve on cubibox maps to localhost:3001.

## Agent Changes

- Generate and persist device UUID at `~/.local/share/openrescue/device_id`
- On startup, register with the server via POST `/api/devices/register`
- Periodically poll `GET /api/config/:deviceId` (every 5 minutes)
- Config from server replaces local config.yml categories (server is source of truth)
- If server is unreachable, use local config.yml as fallback

## Files to Create/Modify

### New: `web/` directory (Next.js app)

```
web/
  src/
    app/
      layout.tsx              — root layout with Catalyst sidebar
      page.tsx                — dashboard (Grafana embed)
      categories/page.tsx     — category management
      devices/page.tsx        — device list
      devices/[id]/page.tsx   — device detail (exclusions, settings)
      settings/page.tsx       — global settings
      api/
        devices/register/route.ts
        config/[deviceId]/route.ts
        categories/route.ts
        categories/[id]/route.ts
        devices/route.ts
        devices/[id]/route.ts
        devices/[id]/exclusions/route.ts
        devices/[id]/exclusions/[eid]/route.ts
        settings/route.ts
        settings/[key]/route.ts
        settings/[deviceId]/[key]/route.ts
    components/               — Catalyst components copied from kit
    lib/
      db.ts                   — SQLite connection + schema init
      auth.ts                 — Tailscale header verification
    middleware.ts              — auth check on all routes
  Dockerfile
  package.json
  tailwind.config.ts
  tsconfig.json
```

### Modify: `server/docker-compose.yml`

- Add openrescue-web service
- Remove Grafana external port

### Modify: Agent files

- `agent/src/openrescue/main.py` — device registration + config polling
- `agent/src/openrescue/config.py` — merge server config with local

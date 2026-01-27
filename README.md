# VPN Business Monorepo

This repository hosts the admin UI plus planning and infrastructure docs for the VPN business launch.

## Structure
- `admin/` - Next.js admin UI (feature-sliced structure).
- `apps/` - Future customer-facing apps (landing, subscription).
- `services/` - Backend services (bot, API, workers).
- `packages/` - Shared libraries (UI, config, types).
- `infra/` - Docker and deployment templates aligned with `plan/`.
- `docs/` - Design and implementation notes.
- `plan/` - Launch and infrastructure guide.

## Local development
Requirements: Node.js 20+ and npm.

Install dependencies from the repo root:

```bash
npm install
```

Run the admin UI:

```bash
npm run dev
```

Run lint and build checks:

```bash
npm run lint
npm run build
```

If you prefer, you can also run commands directly inside `admin/`.

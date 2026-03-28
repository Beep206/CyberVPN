# VPN Business Monorepo

This repository hosts the frontend UI plus planning and infrastructure docs for the VPN business launch.

## Structure
- `frontend/` - Next.js frontend UI (feature-sliced structure).
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

Run the frontend UI:

```bash
npm run dev
```

Run lint and build checks:

```bash
npm run lint
npm run build
```

If you prefer, you can also run commands directly inside `frontend/`.

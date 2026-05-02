# Tauri + React + Typescript

This template should help get you started developing with Tauri, React and Typescript in Vite.

## Linux / WSL bootstrap

For the validated Ubuntu/WSL prerequisite set and the exact `cargo check` bootstrap flow used in this repository, see [docs/plans/2026-04-19-desktop-client-wsl-bootstrap-prerequisites.md](../../docs/plans/2026-04-19-desktop-client-wsl-bootstrap-prerequisites.md).

## Sentry contract

Desktop Sentry is split into two runtime layers:

- renderer: `VITE_SENTRY_DSN`, `VITE_SENTRY_ENVIRONMENT`, `VITE_SENTRY_RELEASE`
- native: `DESKTOP_SENTRY_DSN`, `DESKTOP_SENTRY_ENVIRONMENT`, `DESKTOP_SENTRY_RELEASE`

Local packaged smoke:

- `npm run smoke:release`

See [.env.example](./.env.example) and [desktop-client.md](../../docs/observability/sentry/surfaces/desktop-client.md) for the current rollout contract.

## Recommended IDE Setup

- [VS Code](https://code.visualstudio.com/) + [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode) + [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)

# Stage 1 Production Evidence: Subscription URL Delivery Refresh

Date: 2026-05-22

Scope:

- Telegram Bot must send the canonical subscription URL, not a raw `vless://` proxy URI.
- Mini App must refresh VPN config immediately after invite redemption without requiring a manual reload.
- Config copy / QR / open actions must prefer `subscriptionUrl` over raw generated links.

## Runtime Changes

- Release tag: `stage1-direct-suburl-refresh-20260522T091303Z`
- Rebuilt and recreated services:
  - `cybervpn-backend`
  - `cybervpn-frontend`
  - `cybervpn-telegram-bot`
- Unchanged services were not restarted.
- `.org` remains the subscription/node domain for delivered config URLs.

## Backend Contract

- `GenerateConfigUseCase` now prefers the normalized public subscription URL when Remnawave returns both direct links and a subscription URL.
- Telegram bot config response now includes `subscription_url` and returns `client_type=subscription` when a subscription URL is available.
- Mini App config response uses `subscriptionUrl` as the primary config value when available.
- Direct generated links remain in `links` as secondary data, but are not the primary delivery value.

## Frontend / Mini App Contract

- `VpnConfigCard` now uses `subscriptionUrl || config` for:
  - copy;
  - open in app;
  - QR code.
- Home invite redemption now refreshes:
  - `miniapp-bootstrap`;
  - `miniapp-config` via `resetQueries`;
  - `miniapp-offers`;
  - `usage`.
- Plans invite redemption also resets `miniapp-config` so stale 404/no-config state is not retained.

## Telegram Bot Contract

- Bot config delivery now accepts only HTTP(S) subscription URLs.
- If backend only returns a raw proxy URI without subscription URL, bot treats config as not ready instead of sending the raw URI.

## Local Validation

- Backend py_compile: passed.
- Telegram bot py_compile: passed.
- Backend targeted tests: 7 passed.
- Telegram bot targeted tests: 2 passed.
- Frontend Mini App targeted tests: 19 passed.
- Backend ruff on touched files: passed.
- Telegram bot ruff on touched files: passed.
- Frontend eslint on touched files: passed.
- Full frontend `tsc --noEmit` was not clean due pre-existing unrelated test fixture type errors outside this change.

## Security Review

- Targeted secret scan on touched files: no leaked secrets; matches were only existing secret-handling identifiers/pattern definitions.
- Targeted dangerous pattern scan: no new `eval`, shell execution, `dangerouslySetInnerHTML` or raw SQL string formatting patterns found.
- Python dependency audit for backend and Telegram bot local environments: no known vulnerabilities found; local project packages were skipped because they are not PyPI packages.
- Frontend production dependency audit: no high/critical issues; npm reported existing moderate findings in transitive `brace-expansion` and Next-bundled `postcss`.

## Production Validation

- `cybervpn-backend`: healthy.
- `cybervpn-frontend`: healthy.
- `cybervpn-telegram-bot`: healthy.
- Public `https://cyber-vpn.net/ru-RU/miniapp/home`: 200.
- Public `https://cyber-vpn.net/ru-RU/miniapp/plans`: 200.
- Internal bot config checks for owner/internal Telegram IDs:
  - `client_type=subscription`.
  - `config_string` starts with `https://`.
  - `subscription_url` starts with `https://`.
  - delivered URL uses `cyber-vpn.org`.
  - primary config is not `vless://`.

## Notes

The first direct deploy attempts were interrupted because the generic deploy script synced old frontend `.next-*` artifacts with nested `node_modules` directories. The partial remote release directories were removed after deploy:

- `src-stage1-direct-suburl-refresh-20260522T090555Z`: removed.
- `src-stage1-direct-suburl-refresh-20260522T091027Z`: removed.

The final deploy used a focused sync excluding `.next*/`, `node_modules`, virtualenvs and caches. The retained release source directory is `src-stage1-direct-suburl-refresh-20260522T091303Z` and is approximately 58 MiB.

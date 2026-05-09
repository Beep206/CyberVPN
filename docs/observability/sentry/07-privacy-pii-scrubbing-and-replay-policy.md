# Privacy, PII, Scrubbing And Replay Policy

Status: draft
Owner: platform + security
Last updated: 2026-05-06
Scope: all Sentry SDKs, org-level scrubbing and replay usage
Depends on: `00-current-state-and-discovery.md`, `06-secrets-and-config-matrix.md`
Related paths: `privacy-baseline.json`, `../../../scripts/validate-sentry-privacy.py`, `surfaces/`, `runbooks/privacy-and-data-exposure-response.md`

## Repo-local privacy baseline

- `privacy-baseline.json` is the machine-readable contract for scrub headers, scrub markers, strict endpoint classes, approval checkpoints and minimum code expectations.
- `scripts/validate-sentry-privacy.py` validates that contract in CI and proves the required privacy hooks are still present in the direct runtime surfaces.
- This repo-local baseline is authoritative for code review and rollout. Live self-hosted Sentry settings must match it, but they are tracked as an operational follow-up rather than a code gap.
- S1 local redaction proof is tracked in `../../cybervpn_stage1_launch_docs/95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md`.

## Baseline policy

- Minimal PII by default across all SDKs.
- Allowlist-based tags and context.
- Server-side scrubbing enabled before broad production rollout.
- Attachments and raw payload dumps disabled unless a surface explicitly requires them and has approval.
- `sendDefaultPii` / `send_default_pii` defaults must be `false` everywhere unless a surface-specific exception is documented.
- Python runtimes must disable large request-body capture by default and keep `include_local_variables=False` unless explicitly approved for debugging.

## Safe identity policy

- Default safe user identity: internal `user.id`.
- Telegram identity must be hashed before leaving the bot runtime.
- Email, username, phone number and IP address must not be sent by default.

## Data classes that must be scrubbed everywhere

- `Authorization`
- `Cookie`
- `Set-Cookie`
- JWTs and bearer tokens
- Telegram bot tokens and raw Telegram payloads
- payment provider secrets and checkout payload secrets
- Remnawave/OpenBao credentials
- VPN configuration material and QR payload contents
- OAuth access/refresh/id tokens, magic/auth codes and TOTP secrets
- Telegram Mini App `initData` / `tgWebAppData`
- provider payment identifiers, invoices, checkout payloads and payment callback secrets

## Endpoint classes requiring strict redaction

- auth and session endpoints
- payment and wallet endpoints
- admin mutation endpoints
- webhook ingestion endpoints
- provisioning and config-delivery endpoints

## Replay policy

- Replay is allowed only for web surfaces in the first wave.
- Replay must not capture secrets, payment forms, auth forms or admin-sensitive payloads.
- Replay rollout must start with conservative sample rates and explicit masking.
- Web replay defaults must include `maskAllText: true` and `blockAllMedia: true`.
- No replay on backend, worker, bot, control-plane or native runtimes.

## Enforcement

- Privacy controls exist in both SDK code and org-level server-side rules.
- If there is disagreement between local SDK behavior and org-level scrub rules, the stricter rule wins.
- Web runtimes must scrub request query strings, sensitive headers, cookies and request bodies in `beforeSend`.
- Backend and worker runtimes must scrub request/query/user/context data in `before_send` and avoid sending request bodies by default.
- Native and mobile runtimes must keep `send_default_pii` disabled and only attach safe user identity fields.

## Approval checkpoints

- A new Sentry surface cannot move past `contract_aligned` without an explicit minimal-PII configuration path in code.
- A surface using replay cannot move past baseline rollout without masked-text and blocked-media defaults plus a documented sample-rate decision.
- Live self-hosted Sentry projects cannot be called production-accepted until org/project scrub rules are provisioned and checked against the repo-local baseline.

# Secret Rotation Guide

## Overview

All secrets are stored in `.env` files (never committed to git). The `.env.example` files provide templates with placeholder values.

## Secret Locations

| Secret | Location | Used By |
|--------|----------|---------|
| JWT Auth Secret | `infra/.env` → `JWT_AUTH_SECRET` | Remnawave backend |
| JWT API Token Secret | `infra/.env` → `JWT_API_TOKENS_SECRET` | Remnawave API auth |
| Telegram Bot Token | `infra/.env` → `TELEGRAM_BOT_TOKEN` | Notification bot |
| PostgreSQL Password | `infra/.env` → `POSTGRES_PASSWORD` | Database |
| Grafana Admin Password | `infra/.env` → `GRAFANA_ADMIN_PASSWORD` | Monitoring |
| Redis Password | `infra/.env` → `REMNASHOP_REDIS_PASSWORD` | Cache layer |
| Helix Remnawave Token | `infra/.env` → `HELIX_REMNAWAVE_TOKEN` | Helix adapter |
| Backend Remnawave Webhook Secret | control-plane backend env / `REMNAWAVE_WEBHOOK_SECRET` | Backend webhook signature validation |
| Helix Internal Auth Token | `infra/.env` → `HELIX_INTERNAL_AUTH_TOKEN` | Backend, worker, Helix node, adapter internal auth |
| Helix Manifest Signing Key | `infra/.env` → `HELIX_MANIFEST_SIGNING_KEY` | Helix adapter manifest signer |
| Helix Manifest Signing Key ID | `infra/.env` → `HELIX_MANIFEST_SIGNING_KEY_ID` | Desktop and node signature verification context |
| Helix Adapter Internal Token | `infra/.env` → `HELIX_ADAPTER_INTERNAL_TOKEN` | Backend, worker, node → adapter auth |
| Helix Manifest Signing Seed | `infra/private-transport/adapter.env.example` / adapter env | Helix manifest signing |
| Helix Node Bootstrap Credential | `infra/private-transport/node.env.example` / node env | Helix node bootstrap |
| Helix Adapter Internal Token | `infra/.env` → `HELIX_INTERNAL_TOKEN` | Backend, adapter, worker, node internal auth |
| Helix Manifest Signing Seed | `infra/helix/adapter.env` → `HELIX_MANIFEST_SIGNING_SEED` | Helix adapter manifest signing |
| Helix Node Bootstrap Token | `infra/helix/node.env` → `HELIX_NODE_BOOTSTRAP_TOKEN` | Helix node bootstrap and assignment fetch |

## Rotation Procedures

### JWT Secrets
1. Generate new 64-char hex secret: `openssl rand -hex 32`
2. Update `JWT_AUTH_SECRET` and/or `JWT_API_TOKENS_SECRET` in `infra/.env`
3. Restart Remnawave: `cd infra && docker compose restart remnawave`
4. All existing sessions will be invalidated

### Telegram Bot Token
1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/revoke` and select the bot
3. Copy the new token to `TELEGRAM_BOT_TOKEN` in `infra/.env`
4. Restart bot service: `cd infra && docker compose restart`

### PostgreSQL Password
1. Update `POSTGRES_PASSWORD` in `infra/.env`
2. Update `DATABASE_URL` to match the new password
3. Recreate database container: `cd infra && docker compose down remnawave-db && docker compose up -d remnawave-db`

### Helix Internal Auth Token
1. Generate a new token with sufficient entropy, for example:
   `openssl rand -hex 32`
2. Update `HELIX_INTERNAL_AUTH_TOKEN` in `infra/.env`
3. Restart, in order:
   - `helix-adapter`
   - `backend`
   - `task-worker`
   - `helix-node` services
4. Verify:
   - backend Helix admin API still works
   - worker Helix audits recover
   - lab nodes resume heartbeat delivery

### Helix Manifest Signing Key
1. Generate a new 32-byte secret and encode it as base64 without padding:
   `openssl rand 32 | openssl base64 -A | tr -d '='`
2. Set a new `HELIX_MANIFEST_SIGNING_KEY_ID`
3. Update `HELIX_MANIFEST_SIGNING_KEY` and `HELIX_MANIFEST_SIGNING_KEY_ID` in `infra/.env`
4. Restart `helix-adapter`
5. Verify new manifests carry the new key ID and old manifests expire naturally before removing the old verification context from clients

### Helix Remnawave Token
1. Issue a new API token in `Remnawave`
2. Update `HELIX_REMNAWAVE_TOKEN` in `infra/.env`
3. Restart `helix-adapter`
4. Verify node inventory sync and rollout reads still work

### Backend Remnawave Webhook Secret
1. Generate a new secret with at least 32 characters, for example:
   `openssl rand -hex 32`
2. Update the webhook secret in Remnawave (`WEBHOOK_SECRET_HEADER`).
3. Update `REMNAWAVE_WEBHOOK_SECRET` in the deployed backend environment:
   - local development: `backend/.env`
   - control-plane rollout: vaulted backend env in `infra/ansible/inventories/<env>/group_vars/control_plane_<env>/vault.yml`
4. Restart `backend`.
5. Verify:
   - backend accepts `X-Remnawave-Signature`
   - backend accepts `X-Remnawave-Timestamp`
   - invalid signatures are rejected in webhook logs

### Helix Adapter Internal Token
1. Generate a new strong token:
```bash
openssl rand -hex 32
```
2. Update `HELIX_ADAPTER_INTERNAL_TOKEN` for:
   - adapter
   - backend
   - task-worker
   - helix-node
3. Restart the Helix services in a tight window so old and new tokens do not drift.
4. Verify:
   - backend can resolve manifests;
   - worker can read canary evidence;
   - node heartbeat is accepted.

### Helix Manifest Signing Seed
1. Generate a fresh signing seed in the format expected by the adapter runtime.
2. Update the adapter environment only.
3. Restart the adapter.
4. Verify new manifests are signed and Desktop can still validate and launch `Helix`.
5. Keep old manifests short-lived; do not widen rollout during the rotation window.

### Helix Node Bootstrap Credential
1. Rotate the bootstrap credential in the node environment template and deployment secrets.
2. Re-provision any newly joining Helix nodes with the new credential.
3. Verify existing active nodes continue using their already-issued runtime bundles.
4. Remove the previous bootstrap credential from secret stores after the overlap window.

### Helix Adapter Internal Token
1. Generate a new random token:
   ```bash
   openssl rand -hex 32
   ```
2. Update `HELIX_INTERNAL_TOKEN` in `infra/.env`
3. Restart all Helix control-plane consumers:
   ```bash
   cd infra && docker compose restart backend helix-adapter task-worker helix-node-lab helix-node-lab-02
   ```
4. Verify:
   - backend can resolve Helix manifest
   - worker Helix audits recover
   - node heartbeat resumes without `401`

### Helix Manifest Signing Seed
1. Generate a fresh 32-byte base64 seed:
   ```bash
   openssl rand -base64 32
   ```
2. Update `HELIX_MANIFEST_SIGNING_SEED` in `infra/helix/adapter.env`
3. Restart the adapter:
   ```bash
   cd infra && docker compose restart helix-adapter
   ```
4. Re-issue Helix manifests and verify:
   - manifest signing succeeds
   - desktop can still resolve and validate manifests
   - previously revoked manifests remain revoked

### Helix Node Bootstrap Token
1. Generate a new random token:
   ```bash
   openssl rand -hex 24
   ```
2. Update `HELIX_NODE_BOOTSTRAP_TOKEN` in `infra/helix/node.env`
3. Restart Helix nodes:
   ```bash
   cd infra && docker compose restart helix-node-lab helix-node-lab-02
   ```
4. Verify node assignment fetch and heartbeat flow resume normally

## Prevention

- `.gitignore` blocks: `.env*`, `APIToken.txt`, `*.secret`, `*.credentials`, `*.key`
- Never commit secrets to git — use `.env` files only
- Review `git diff --cached` before every commit
- Consider adding [gitleaks](https://github.com/gitleaks/gitleaks) as a pre-commit hook

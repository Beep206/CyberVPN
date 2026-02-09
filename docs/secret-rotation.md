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

## Prevention

- `.gitignore` blocks: `.env*`, `APIToken.txt`, `*.secret`, `*.credentials`, `*.key`
- Never commit secrets to git — use `.env` files only
- Review `git diff --cached` before every commit
- Consider adding [gitleaks](https://github.com/gitleaks/gitleaks) as a pre-commit hook

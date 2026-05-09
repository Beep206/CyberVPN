# 54. Stage 1 Evidence - S1-TG-002 Production Telegram Bot Token Path

Date: 2026-05-04

Backlog ID: `S1-TG-002`

Status: completed locally for secret path/inventory; external BotFather production bot and real token evidence remain required before S1 go-live.

## Objective

Define the safe production Telegram Bot token path without committing, printing or guessing the token value.

This task does not create the production bot in BotFather and does not add real credentials. It closes the repository-side path: env names, Ansible vault keys, backend injection, owner/storage rules, rotation rules and redacted evidence requirements.

## Official Docs Checked

| Surface | Source |
|---|---|
| BotFather is the official way to create/manage bot accounts | https://core.telegram.org/bots/features#botfather |
| Telegram Bot API webhook `secret_token` header behavior | https://core.telegram.org/bots/api#setwebhook |

## Production Token Ownership

| Field | S1 value |
|---|---|
| Token owner | `@Sasha_Beep` / project owner |
| Finance/ops backup | `@Sasha_Beep` |
| Production bot username | Not known until BotFather evidence; do not treat placeholders as final |
| Staging bot username | Not known until BotFather evidence; must differ from production |
| Token value in repo/docs | Forbidden |
| Token value in screenshots/evidence | Forbidden |
| Token value in support/admin UI | Forbidden |

## Canonical Secret Inventory

| Environment | Service | Runtime env/key | Secret namespace/path | Current repo evidence |
|---|---|---|---|---|
| production | Telegram Bot service | `BOT_TOKEN` | `stage1/production/telegram-bot/bot_token` | `.env.example` placeholder only |
| production | Telegram Bot service | `WEBHOOK_SECRET_TOKEN` | `stage1/production/telegram-bot/webhook_secret_token` | `.env.example` placeholder only |
| production | Telegram Bot service | `BOT_USERNAME` | `stage1/production/telegram-bot/bot_username` | non-secret, value pending |
| production | Telegram Bot service | `TELEGRAM_BOT_PRODUCTION_USERNAME` | `stage1/production/telegram-bot/production_username` | non-secret, value pending |
| production | Backend API | `TELEGRAM_BOT_TOKEN` | `vault_control_plane_backend_telegram_bot_token` | added as empty vault placeholder |
| production | Backend API | `TELEGRAM_BOT_USERNAME` | `vault_control_plane_backend_telegram_bot_username` | added as empty vault placeholder |
| production | Backend API | `TELEGRAM_BOT_INTERNAL_SECRET` | `vault_control_plane_backend_telegram_bot_internal_secret` | added as empty vault placeholder |
| production | Task worker/scheduler | `TELEGRAM_BOT_TOKEN` | `vault_control_plane_worker_telegram_bot_token` | existing empty vault placeholder |
| staging | Telegram Bot service | `BOT_TOKEN` | `stage1/staging/telegram-bot/bot_token` | `.env.example` placeholder only |
| staging | Backend API | `TELEGRAM_BOT_TOKEN` | `vault_control_plane_backend_telegram_bot_token` in staging inventory | added as empty vault placeholder |
| staging | Backend API | `TELEGRAM_BOT_USERNAME` | `vault_control_plane_backend_telegram_bot_username` in staging inventory | added as empty vault placeholder |
| staging | Backend API | `TELEGRAM_BOT_INTERNAL_SECRET` | `vault_control_plane_backend_telegram_bot_internal_secret` in staging inventory | added as empty vault placeholder |
| staging | Task worker/scheduler | `TELEGRAM_BOT_TOKEN` | `vault_control_plane_worker_telegram_bot_token` in staging inventory | existing empty vault placeholder |

Notes:

- The same Bot token may be required by the bot runtime, backend Mini App auth, Telegram Stars verification and worker notifications, but it must still be injected per service with least-privilege access.
- The backend internal secret is not the Telegram Bot API token. It authenticates internal bot-to-backend calls and must be generated separately.
- `WEBHOOK_SECRET_TOKEN` must also be generated separately and used for Telegram webhook authenticity.

## Implemented Contract

Repository changes:

- backend env template now lists `TELEGRAM_BOT_INTERNAL_SECRET` beside `TELEGRAM_BOT_TOKEN` and `TELEGRAM_BOT_USERNAME`;
- staging and production Ansible backend env now inject:
  - `TELEGRAM_BOT_TOKEN`;
  - `TELEGRAM_BOT_USERNAME`;
  - `TELEGRAM_BOT_INTERNAL_SECRET`;
- staging and production vault examples now include empty placeholders:
  - `vault_control_plane_backend_telegram_bot_token`;
  - `vault_control_plane_backend_telegram_bot_username`;
  - `vault_control_plane_backend_telegram_bot_internal_secret`;
- `bootstrap_control_plane_vault.py` maps structured source keys:
  - `backend.telegram_bot_token`;
  - `backend.telegram_bot_username`;
  - `backend.telegram_bot_internal_secret`;
- Stage 1 secrets inventory now lists backend Telegram token/username/internal secret and bot identity keys.

## Production Readiness Rules

S1 go-live remains blocked until redacted evidence proves:

- production bot was created by `@Sasha_Beep` in BotFather;
- production bot token is stored only in the approved production secret path;
- staging bot token is different and stored only in the approved staging secret path;
- production and staging bot usernames are different;
- production `getMe` succeeds without exposing token value;
- production webhook is set with `WEBHOOK_SECRET_TOKEN`;
- backend Mini App auth/Telegram Stars verification uses the production `TELEGRAM_BOT_TOKEN`;
- worker notifications use the intended production token or are explicitly disabled;
- token rotation through BotFather is documented and tested on staging first.

## Local Evidence

Ansible vault mapping:

```bash
PYENV_VERSION=3.13.11 python -m pytest infra/ansible/tests/test_control_plane_phase8.py -q
```

Result:

```text
4 passed in 0.11s
```

## Security Review Notes

| Check | Result |
|---|---|
| Token value | No real production Telegram token added |
| Placeholder shape | Bot token examples use non-token placeholders where changed |
| Environment separation | Staging and production vault examples both contain empty independent placeholders |
| Backend injection | Backend receives explicit Telegram token/username/internal-secret env keys in staging and production Ansible env |
| Least privilege | Token paths are per service; backend internal secret is separate from Telegram Bot API token |
| Rotation | Rotation must be through BotFather and redeploy/webhook reset; staging test required before production |
| Secret scan | No Telegram token, private key, AWS key, Slack token or OpenAI key patterns found in changed S1-TG-002 files |
| Static dangerous pattern scan | No new `eval`, `exec`, `shell=True`, `os.system`, pipe-to-shell or `chmod 777` pattern added in changed infra lines |
| Dependencies | No dependency added, removed or downgraded |
| `npm audit --omit=dev` | Existing moderate `next -> postcss` advisory remains; `npm audit fix --force` proposes a breaking downgrade and was not applied |

## Remaining Evidence Before Go-Live

| Evidence item | Status |
|---|---|
| Production BotFather screenshot/redacted account evidence | Open |
| Production token stored in approved secret store | Open |
| Production token absent from repo, CI logs, docs and screenshots | Open |
| Production `getMe` redacted output | Open |
| Production webhook `secret_token` redacted proof | Open |
| Staging token rotation drill | Open |
| Alert/support runbook update after token rotation | Open |

## Next ID

Next ID to execute: `S1-TG-003` - verify Telegram Bot commands/menu/onboarding with staging/deployed smoke evidence.

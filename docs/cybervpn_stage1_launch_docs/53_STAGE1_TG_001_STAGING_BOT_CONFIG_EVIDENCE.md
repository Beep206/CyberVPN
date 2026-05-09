# 53. Stage 1 Evidence - S1-TG-001 Staging Telegram Bot Config

Date: 2026-05-04

Backlog ID: `S1-TG-001`

Status: completed locally; external BotFather/getMe evidence is still required before S1 go-live.

## Objective

Create a Stage 1 Telegram Bot contract where staging and production bot identities cannot be accidentally mixed, and where the S1 public command/menu surface is deterministic before real Telegram credentials are enabled.

This task does not store real bot tokens in the repository and does not create the BotFather account automatically. Telegram bot creation still requires owner-controlled BotFather access and redacted evidence.

## Official Docs Checked

| Surface | Source |
|---|---|
| Telegram webhook `secret_token` and `X-Telegram-Bot-Api-Secret-Token` | https://core.telegram.org/bots/api#setwebhook |
| aiogram `set_my_commands` | https://docs.aiogram.dev/en/dev-3.x/api/methods/set_my_commands.html |
| aiogram `set_chat_menu_button` | https://docs.aiogram.dev/en/dev-3.x/api/methods/set_chat_menu_button.html |

## Implemented Contract

Telegram bot config now includes explicit S1 identity fields:

- `BOT_USERNAME`
- `TELEGRAM_BOT_STAGING_USERNAME`
- `TELEGRAM_BOT_PRODUCTION_USERNAME`
- `TELEGRAM_BOT_MENU_BUTTON`
- `TELEGRAM_MINIAPP_URL`

Validation rules:

- staging and production usernames must be different when both are configured;
- `BOT_USERNAME` must match `TELEGRAM_BOT_STAGING_USERNAME` when `ENVIRONMENT=staging` and both are configured;
- `BOT_USERNAME` must match `TELEGRAM_BOT_PRODUCTION_USERNAME` when `ENVIRONMENT=production` and both are configured;
- `TELEGRAM_MINIAPP_URL` is required when `TELEGRAM_BOT_MENU_BUTTON=miniapp`;
- no real token value is added to docs, tests or committed config.

Startup behavior:

- when `TELEGRAM_BOT_SKIP_NETWORK_CALLS=true`, startup performs no Telegram API calls;
- otherwise startup calls `getMe`, applies S1 commands through `set_my_commands`, applies the default menu button through `set_chat_menu_button`, and then sets webhook when `BOT_MODE=webhook`;
- command/menu setup uses aiogram 3.27-compatible objects.

## S1 Public Command Surface

| Command | Purpose | Handler status |
|---|---|---|
| `/start` | onboarding and main menu | Existing |
| `/menu` | reopen main menu | Added |
| `/connect` | VPN access/config surface | Added |
| `/plans` | public Telegram plan catalog | Added |
| `/trial` | trial activation flow | Added |
| `/support` | support contact | Existing |
| `/paysupport` | payment/refund support contact | Existing |

Admin commands remain handler-supported but are not exposed in the default public command menu.

## Code Changes

| File | Change |
|---|---|
| `services/telegram-bot/src/config.py` | Added staging/production bot username fields, menu button mode, Mini App URL and S1 identity validation |
| `services/telegram-bot/src/stage1_surface.py` | Added canonical S1 command list, menu button builder and startup apply helper |
| `services/telegram-bot/src/main.py` | Applies S1 commands/menu during startup after `getMe` |
| `services/telegram-bot/src/handlers/menu.py` | Added `/menu` and `/connect` command entrypoints |
| `services/telegram-bot/src/handlers/subscription.py` | Added `/plans` command entrypoint |
| `services/telegram-bot/src/handlers/trial.py` | Added `/trial` command entrypoint |
| `services/telegram-bot/.env.example` | Added staging/prod bot identity and menu/Mini App settings |
| `services/telegram-bot/README.md` | Documented new S1 bot identity/menu settings |
| `services/telegram-bot/tests/unit/test_stage1_surface.py` | Added S1 command/menu/config validation coverage |
| `services/telegram-bot/tests/unit/test_stage1_command_entrypoints.py` | Added command entrypoint coverage |
| `services/telegram-bot/tests/unit/test_main.py` | Added startup command/menu setup coverage |

## Local Evidence

Component and command-entrypoint tests:

```bash
cd services/telegram-bot
uv run pytest --no-cov tests/unit/test_stage1_surface.py tests/unit/test_stage1_command_entrypoints.py tests/unit/test_main.py tests/unit/test_handlers/test_support.py tests/unit/test_handlers/test_channel_parity.py tests/e2e/test_docker_compose.py::test_env_example_has_required_variables tests/e2e/test_docker_compose.py::test_env_example_syntax_valid
```

Result:

```text
25 passed in 0.63s
```

Lint:

```bash
cd services/telegram-bot
uv run ruff check src/config.py src/main.py src/stage1_surface.py src/handlers/menu.py src/handlers/subscription.py src/handlers/trial.py tests/unit/test_stage1_surface.py tests/unit/test_stage1_command_entrypoints.py tests/unit/test_main.py
```

Result:

```text
All checks passed!
```

## Remaining Evidence Before Go-Live

The local contract is not enough for go-live. Before S1 beta, capture redacted evidence that:

- owner created a dedicated staging bot in BotFather;
- owner created a separate production bot in BotFather;
- staging and production bot usernames are different;
- staging token is stored only through the approved secret process;
- production token is stored only through the approved secret process;
- `getMe` succeeds for staging and production without exposing token values;
- staging webhook is set with `X-Telegram-Bot-Api-Secret-Token` verification;
- public commands appear in Telegram clients and match the S1 command list;
- `TELEGRAM_BOT_SKIP_NETWORK_CALLS=false` startup succeeds on staging.

## Security Review Notes

| Check | Result |
|---|---|
| Token handling | No real Telegram token committed or printed |
| Staging/prod separation | Username mismatch and duplicate username configs fail validation |
| Webhook authenticity | Existing webhook secret-token path retained; live evidence still required |
| Public command surface | Default command menu includes only B2C S1 user/support commands |
| Admin exposure | Admin commands are not included in default public command menu |
| Network behavior | Smoke mode skips Telegram API calls for local/no-token evidence |
| Dependencies | No dependency added or downgraded |

## Next ID

Next ID to execute: `S1-TG-002` - production Telegram Bot token path and secrets inventory without values.

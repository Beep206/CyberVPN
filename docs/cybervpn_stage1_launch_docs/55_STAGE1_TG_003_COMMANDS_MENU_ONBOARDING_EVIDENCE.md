# 55. Stage 1 Evidence - S1-TG-003 Telegram Bot Commands, Menu and Onboarding

Date: 2026-05-04

Backlog ID: `S1-TG-003`

Status: completed locally for command/menu/onboarding smoke coverage; live Telegram client screenshots and deployed staging evidence remain required before S1 go-live.

## Objective

Prove that the S1 Telegram Bot public command surface is internally wired and accessible:

- `/start` opens onboarding and the main menu;
- `/menu` opens the main menu;
- `/connect` opens the VPN access/config surface;
- `/plans` opens the public Telegram plan catalog;
- `/trial` activates trial flow and prompts for config delivery;
- `/support` and `/paysupport` return the configured support contact;
- startup applies the default command list and menu button through the Telegram Bot API integration path.

This evidence does not claim that the commands are visible in a real Telegram client. Real client screenshots require BotFather-created bot accounts, real tokens and a public HTTPS webhook/polling deployment.

## Official Docs Checked

| Surface | Source |
|---|---|
| Telegram commands and global command expectations | https://core.telegram.org/bots/features#commands |
| Telegram menu button behavior | https://core.telegram.org/bots/features#menu-button |
| aiogram router registration and `resolve_used_update_types` | https://docs.aiogram.dev/en/dev-3.x/dispatcher/router.html |
| aiogram `set_my_commands` Bot API wrapper | https://docs.aiogram.dev/en/dev-3.x/api/methods/set_my_commands.html |

## S1 Public Command Contract

| Command | Expected S1 behavior | Local proof |
|---|---|---|
| `/start` | Register/update Telegram user, render onboarding copy and main menu | `test_start_command_registers_user_and_shows_s1_onboarding_menu` |
| `/menu` | Render main menu even if backend user lookup is unavailable | `test_menu_command_opens_main_menu_without_registered_user` |
| `/connect` | Render VPN access/config surface from entitlement state | `test_connect_command_opens_subscription_surface_for_inactive_user`, channel parity test |
| `/plans` | Render public Telegram sellable plan catalog | `test_plans_command_opens_public_telegram_catalog` |
| `/trial` | Activate trial and prompt for config delivery | `test_trial_command_activates_trial_and_prompts_for_config` |
| `/support` | Return configured support contact | `test_support_commands_return_configured_support_contact` |
| `/paysupport` | Return configured support/refund contact path | `test_support_commands_return_configured_support_contact` |

Admin commands are not part of the default public command menu.

## Implemented Contract

Repository changes:

- `support.py` imports were tightened so the S1 support handler passes the target ruff gate;
- `test_stage1_command_entrypoints.py` now includes local smoke coverage for:
  - `/start` onboarding and main-menu callback availability;
  - `/support`;
  - `/paysupport`;
- existing startup tests continue to prove that `on_startup` calls `get_me`, applies `set_my_commands` and sets the default menu button when network calls are enabled.

No real Telegram token, BotFather username or webhook endpoint was added.

## Local Smoke Transcript

This is a redacted local test transcript, not a Telegram screenshot.

| Step | Expected result |
|---|---|
| Bot startup with network calls enabled | `get_me` called, S1 commands applied, menu button set to `commands` |
| User sends `/start` | user registration path called, welcome/onboarding text sent, main menu includes trial/buy/support callbacks |
| User sends `/menu` | main menu title sent with reply markup |
| User sends `/connect` without active entitlement | subscription empty state sent with subscription keyboard |
| User sends `/plans` | public Telegram plan catalog rendered and FSM enters selecting-plan state |
| User sends `/trial` and is eligible | trial activation response sent, then config delivery prompt sent |
| User sends `/support` | configured support contact returned |
| User sends `/paysupport` | configured support/refund contact returned |

## Local Evidence

Targeted Telegram S1 smoke tests:

```bash
cd services/telegram-bot
uv run pytest --no-cov tests/unit/test_stage1_surface.py tests/unit/test_stage1_command_entrypoints.py tests/unit/test_main.py tests/unit/test_handlers/test_support.py tests/unit/test_handlers/test_channel_parity.py tests/e2e/test_docker_compose.py::test_env_example_has_required_variables tests/e2e/test_docker_compose.py::test_env_example_syntax_valid -q
```

Result:

```text
28 passed in 0.33s
```

Focused command entrypoint smoke:

```bash
cd services/telegram-bot
uv run pytest --no-cov tests/unit/test_stage1_command_entrypoints.py -q
```

Result:

```text
7 passed in 0.05s
```

Lint:

```bash
cd services/telegram-bot
uv run ruff check src/stage1_surface.py src/main.py src/handlers/start.py src/handlers/menu.py src/handlers/subscription.py src/handlers/trial.py src/handlers/support.py tests/unit/test_stage1_surface.py tests/unit/test_stage1_command_entrypoints.py tests/unit/test_main.py
```

Result:

```text
All checks passed!
```

## Security Review Notes

| Check | Result |
|---|---|
| Token handling | No real Telegram token, webhook secret or BotFather username added |
| Public surface | Default command list remains limited to S1 B2C/support commands |
| Admin exposure | Admin commands remain outside the default public command menu |
| Onboarding safety | `/start` test proves main menu entrypoints, but does not expose auth tokens or VPN configs |
| Support contact | `/support` and `/paysupport` use configured contact formatting |
| Secret scan | No Telegram token, private key, AWS key, Slack token or OpenAI key patterns found in changed S1-TG-003 files |
| Static dangerous pattern scan | No new `eval`, `exec`, `shell=True`, `os.system`, pipe-to-shell, `chmod 777` or `dangerouslySetInnerHTML` pattern added in changed S1-TG-003 runtime/test lines |
| Dependencies | No dependency added, removed or downgraded |
| `npm audit --omit=dev` | Existing moderate `next -> postcss` advisory remains; `npm audit fix --force` proposes a breaking downgrade and was not applied |

## Remaining Evidence Before Go-Live

| Evidence item | Status |
|---|---|
| BotFather staging bot created and username approved | Open |
| BotFather production bot created and username approved | Open |
| Real Telegram `getMe` redacted output | Open |
| Real command menu visible in Telegram client screenshots | Open |
| Real `/start`, `/menu`, `/connect`, `/plans`, `/trial`, `/support`, `/paysupport` screenshots or video capture | Open |
| Staging webhook/polling deployment with `TELEGRAM_BOT_SKIP_NETWORK_CALLS=false` | Open |
| Support owner confirms visible text and contact path | Open |

## Next ID

Next ID to execute: `S1-TG-004` - verify Telegram Mini App home/plans/payments/devices/profile/wallet evidence.

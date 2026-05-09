# Stage 1 Support Templates Evidence

> Date: 2026-05-04
> Backlog ID: `S1-SUP-002`
> Scope: support response templates for failed payment, paid-but-no-access, VPN not connecting, expired subscription and refund request
> Status: local template contract and docs complete; owner/legal text approval closed in `79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`; provider-specific refund behavior and live support workflow evidence remain required before S1 go-live

## Purpose

`S1-SUP-002` fixes the first set of operator/user response templates for Stage 1 Controlled Public Beta.

The goal is not to automate support fully. The goal is to make first-line support consistent and safe:

- tell users what happened without overpromising payment/refund/provisioning outcomes;
- request only safe identifiers and redacted screenshots;
- never request passwords, 2FA/TOTP codes, full card numbers, CVV/CVC, raw QR codes, raw subscription URLs, raw config files or seed/private keys;
- map each template to the same S1 support queues from `S1-SUP-001`;
- keep refund and auto-renewal language conservative until provider/live workflow evidence exists.

## Implemented Template Catalog

| Template | Category | Queue | Contact |
|---|---|---|---|
| `SUP-S1-001` | `failed_payment` | `s1_payment_finance_review` | `refund@cyber-vpn.net` |
| `SUP-S1-002` | `paid_no_access` | `s1_paid_no_access_review` | `support@cyber-vpn.net` |
| `SUP-S1-003` | `vpn_not_connecting` | `s1_vpn_connectivity_support` | `support@cyber-vpn.net` |
| `SUP-S1-004` | `expired_subscription` | `s1_customer_support` | `support@cyber-vpn.net` |
| `SUP-S1-005` | `refund_request` | `s1_payment_finance_review` | `refund@cyber-vpn.net` |

## Template Text

### `SUP-S1-001` — Failed payment

```text
Мы видим, что оплата не завершилась или ожидает подтверждения. Проверьте статус платежа в кабинете или Telegram Mini App. Если деньги списались, отправьте ID платежа, дату, способ оплаты или скрин без номера карты, CVV/CVC, QR-кода, subscription URL и config. Мы сверим статус у провайдера и обновим доступ только после подтверждения платежа.
```

### `SUP-S1-002` — Paid but no access

```text
Оплата найдена или проверяется. Если платеж подтвержден, доступ должен быть выдан автоматически. Если доступ не появился, мы проверим payment status, provisioning status и Remnawave-состояние, затем повторим выдачу доступа или передадим заявку технической команде. Не отправляйте публично QR-код, subscription URL или config file.
```

### `SUP-S1-003` — VPN does not connect

```text
Проверьте срок подписки, лимит устройств, правильную инструкцию для вашей платформы и что используется актуальный QR/subscription URL/config. Если подключение все равно не работает, отправьте платформу, приложение/клиент, страну подключения, примерное время ошибки и скрин сообщения без QR-кода, subscription URL и config file.
```

### `SUP-S1-004` — Expired subscription

```text
Подписка истекла или находится в grace period. Для восстановления доступа продлите тариф в кабинете или Telegram Mini App. В Stage 1 мы не обещаем автоматическое списание или автопродление: продление выполняется вручную пользователем. Если оплата уже была выполнена, отправьте ID платежа или дату оплаты, и мы проверим статус.
```

### `SUP-S1-005` — Refund request

```text
Мы приняли запрос на возврат. Для проверки укажите ID платежа, дату оплаты, способ оплаты и причину обращения. Решение зависит от статуса платежа, использованного провайдера и финальной Refund Policy. Не отправляйте номер карты, CVV/CVC, пароль, QR-код, subscription URL или config file. До проверки мы не обещаем автоматический или гарантированный возврат.
```

## Repository Changes

Backend:

- `backend/src/presentation/api/shared/stage1_support_templates.py`
  - added stable template IDs `SUP-S1-001`...`SUP-S1-005`;
  - maps each template to S1 support category, queue and contact;
  - records safe data to request, forbidden data and escalation triggers;
  - exposes list/get/category lookup helpers.
- `backend/src/presentation/api/shared/__init__.py`
  - exports template catalog helpers for future admin/support/API use.

Tests:

- `backend/tests/security/test_stage1_support_templates.py`
  - proves required template coverage;
  - proves route/contact/queue mapping;
  - proves templates avoid unsafe data requests;
  - proves templates do not overpromise refund or auto-renewal outcomes;
  - proves paid-no-access and VPN templates warn not to share QR/subscription URL/config.

Docs:

- `09_STAGE1_LEGAL_SUPPORT_OPERATIONS.md`
  - updated template text and added queue/contact/sensitive-data rules.

## Local Evidence Commands

Backend lint:

```bash
cd backend
uv run ruff check src/presentation/api/shared/__init__.py src/presentation/api/shared/stage1_support_templates.py tests/security/test_stage1_support_templates.py
```

Result:

```text
All checks passed!
```

Backend template tests:

```bash
cd backend
uv run pytest tests/security/test_stage1_support_templates.py -q --no-cov
```

Result:

```text
11 passed
```

Combined S1 support contract tests:

```bash
cd backend
uv run pytest tests/security/test_stage1_support_ticket_path.py tests/security/test_stage1_support_templates.py -q --no-cov
```

Result:

```text
20 passed
```

Template catalog smoke:

```bash
cd backend
uv run python - <<'PY'
from src.presentation.api.shared import list_stage1_support_templates
for template in list_stage1_support_templates():
    print(f'{template.template_id.value} | {template.category.value} | {template.escalation_queue} | {template.contact}')
PY
```

Result:

```text
SUP-S1-001 | failed_payment | s1_payment_finance_review | refund@cyber-vpn.net
SUP-S1-002 | paid_no_access | s1_paid_no_access_review | support@cyber-vpn.net
SUP-S1-003 | vpn_not_connecting | s1_vpn_connectivity_support | support@cyber-vpn.net
SUP-S1-004 | expired_subscription | s1_customer_support | support@cyber-vpn.net
SUP-S1-005 | refund_request | s1_payment_finance_review | refund@cyber-vpn.net
```

Security/dependency checks:

```bash
cd backend && uv run pip check
cd backend && uvx pip-audit --progress-spinner off
```

Result:

```text
pip check: No broken requirements found.
pip-audit: No known vulnerabilities found.
```

## What This Closes

| Item | Status |
|---|---|
| `S1-SUP-002` local support template catalog | Closed locally |
| Failed payment template | Closed locally |
| Paid-but-no-access template | Closed locally |
| VPN not connecting template | Closed locally |
| Expired subscription template | Closed locally |
| Refund request template | Closed locally |
| Sensitive-data guardrails for support replies | Closed locally |

## Remaining Evidence Before Go-Live

| Evidence | Status |
|---|---|
| Owner/legal approval for final public support/refund wording | Open |
| Provider-specific refund policy alignment for enabled payment providers | Open |
| Live support operator workflow using these templates | Open |
| Deployed admin/support UI/template insertion evidence | Open if templates become UI-selectable in S1 |
| Real support mailbox and Telegram transcript using templates | Open |

## Security Notes

- No production support mailbox credential, provider credential, bot token, VPN config or user secret was added.
- Templates explicitly forbid requesting passwords, 2FA/TOTP codes, full card numbers, CVV/CVC, raw QR codes, raw subscription URLs, raw config files and seed/private keys.
- Refund wording is intentionally non-committal until provider-specific Refund Policy is final.
- Expiry wording explicitly avoids promising autoprolongation in S1.
- Docker was not started for this task.

## Next ID

Next ID to execute: `S1-SUP-003` - escalation process.

# CyberVPN S2 Post-Deploy Checklist

**Назначение:** список того, что owner/operator должен проверить после деплоя Stage 2 Public Release 1.0.

**Язык документа:** русский.

**Текущий контекст:** CyberVPN уже открыт как S2 B2C Public Release 1.0 с контролируемыми остаточными рисками. Customer-facing runtime работает на арендованных серверах. GitLab, CI, observability, логи и операционные панели остаются на домашнем сервере. VPN-нода должна оставаться только VPN-нодой.

**Правило:** если проверка ниже не проходит, не расширять аудиторию и не переходить к S3 production enablement. Сначала классифицировать проблему как `P0/P1/P2/P3`, записать evidence и принять решение: hotfix, rollback, pause или continue.

---

## 1. Быстрая сводка решения

После каждого S2 deploy нужно получить один из вариантов:

| Решение | Когда использовать |
|---|---|
| `CONTINUE_PUBLIC` | Всё критичное работает, новых P0/P1 нет |
| `CONTINUE_WITH_KNOWN_ISSUES` | Есть P2/P3, они не ломают регистрацию, VPN-доступ, оплату/trial, support |
| `PAUSE_EXPANSION` | Продукт работает, но расширять аудиторию нельзя |
| `ROLLBACK_REQUIRED` | Деплой сломал критичный B2C поток |
| `DISABLE_RISKY_FEATURE` | Нужно выключить отдельную функцию kill switch без полного rollback |

Рекомендация: для обычного S2 deploy цель должна быть `CONTINUE_PUBLIC` или `CONTINUE_WITH_KNOWN_ISSUES`. Для S3 readiness недостаточно просто “сайт открывается”.

---

## 2. Перед началом проверки

Проверить:

- есть immutable commit/tag, с которого выполнен deploy;
- GitLab `main` является primary source;
- GitHub mirror обновлён;
- известен runtime tag, например `stage2-public-rc.N` или `stage2-public-live.N`;
- есть свежий backup перед risky deploy;
- понятно, какой rollback tag/commit использовать;
- нет незадокументированных production secrets в evidence;
- HTTP/3/QUIC не выключался;
- `.org` используется только для VPN node/subscription delivery, не как зеркало клиентского сайта;
- VPN-нода остаётся node-only.

Что записать в evidence:

```text
deploy_time_utc=
deploy_commit=
deploy_tag=
operator=
rollback_target=
decision=
```

---

## 3. Runtime containers

Проверить на `prod-app-1`:

- backend running/healthy;
- frontend running/healthy;
- admin running/healthy;
- Telegram bot running/healthy;
- worker running/healthy;
- scheduler running/healthy;
- PostgreSQL running/healthy;
- Valkey/Redis running/healthy;
- Remnawave control-plane running/healthy;
- Remnawave PostgreSQL/Valkey running/healthy;
- exporters running/healthy.

Ожидаемый результат:

```text
all_customer_runtime_containers=healthy
```

Если backend/frontend/admin/bot/worker/scheduler unhealthy, это минимум `P1`. Если PostgreSQL или Remnawave control-plane unhealthy, это `P0/P1` в зависимости от влияния на уже выданные подписки.

---

## 4. Public routes

Проверить публичные маршруты:

| Route | Ожидается | Зачем |
|---|---:|---|
| `https://cyber-vpn.net/ru-RU` | `200` | главная |
| `https://cyber-vpn.net/ru-RU/register` | `200` | публичная регистрация |
| `https://cyber-vpn.net/ru-RU/pricing` | `200` | тарифы |
| `https://cyber-vpn.net/ru-RU/status` | `200` | статус |
| `https://cyber-vpn.net/ru-RU/help` | `200` | помощь |
| `https://cyber-vpn.net/ru-RU/miniapp/home` | `200` | Mini App route |
| `https://admin.cyber-vpn.net/ru-RU/login` | `200` | admin login |
| `https://api.cyber-vpn.net/health` | `200` | API health |
| `https://api.cyber-vpn.net/docs` | `404` или закрыто | публичный OpenAPI не должен случайно открыться |
| `https://cyber-vpn.org/api/sub/<invalid-token>` | `404` | `.org` subscription route не должен раскрывать данные по невалидному токену |

Проверить headers:

```text
alt-svc: h3=":443"; ma=86400
strict-transport-security: max-age=31536000; includeSubDomains; preload
```

Важно: HTTP/3/QUIC не отключать. Если Cloudflare/Caddy/edge менялись, это отдельный обязательный пункт проверки.

---

## 5. Auth and registration

Проверить:

- новая регистрация доступна, если S2 profile предполагает public registration;
- login через email/password работает;
- logout работает;
- ошибка неправильного пароля отображается корректно;
- rate limit не блокирует нормальный login;
- Telegram Mini App login/linking работает;
- пользователь в Mini App видит себя не как `Guest User`, если Telegram initData валиден;
- OAuth остаётся выключенным, если production credentials/callback evidence ещё не закрыты;
- admin login требует 2FA для privileged admin/operator/support/finance ролей.

Ожидаемый текущий controlled profile:

```text
REGISTRATION_ENABLED=true
REGISTRATION_INVITE_REQUIRED=false
OAUTH_ENABLED_LOGIN_PROVIDERS=
```

Если OAuth включается позже, нужно отдельно проверить Google/GitHub callbacks, redirect URL, state/nonce и logout behavior.

---

## 6. Mini App and Telegram bot

Проверить в Telegram:

- bot отвечает на `/start`;
- Mini App открывается без красного error state;
- нижнее меню не ведёт на обычную web-login страницу;
- Home/Plans/Wallet/Profile переключаются без разлогина;
- локаль не смешивает русский и английский в основном пользовательском flow;
- Profile показывает Telegram user данные;
- Logout/Delete Account работают так, как ожидается;
- “Мои инвайты” отображаются, если у пользователя есть invite codes;
- после redeem invite/trial/payment состояние обновляется без ручной перезагрузки Mini App;
- VPN-конфигурация появляется после успешного provisioning;
- bot отдаёт subscription URL, а не только raw `vless://` config, если для пользователя ожидается подписка;
- subscription URL должен быть в зоне `.org`, если это пользовательская subscription delivery ссылка.

Критично:

- после активации доступа пользователь должен получить реальный способ подключения;
- если subscription активна, но config unavailable, это `P1`;
- если config появляется только после refresh, это `P2`, если пользователь всё равно может подключиться после перезагрузки.

---

## 7. Plans, catalog, invite, referral, promo and gift

Проверить:

- публичные тарифы отображаются корректно;
- скрытые тарифы не видны публично без явного правила;
- тарифы “Россия Старт” и “Россия Базовый” не появляются там, где они не должны быть видны;
- для RU bundle тарифов применяется правильный subscription template, если он включён;
- invite code activation работает отдельно от paid checkout flow;
- referral/promo/gift/autoprolongation не создают неожиданных скидок, rewards или payments без утверждённого S2 gate;
- все kill switches для growth функций работают.

Для S2 важно: growth-механики могут быть реализованы, но не должны превращать B2C release в S3 partner launch.

---

## 8. Trial and subscription lifecycle

Проверить:

- trial можно активировать новому eligible пользователю;
- повторный trial не выдаётся без явного admin/support решения;
- invite access создаёт subscription и entitlement;
- subscription status отображается сразу после activation;
- expiration date корректная;
- device/traffic limits отображаются корректно;
- expired subscription не показывает активный доступ;
- renewal/manual invoice copy не обещает autoprolongation, если recurring billing не включён;
- refund/cancel copy не противоречит legal/trust pages.

Критичный пользовательский критерий:

```text
trial/pay/invite -> subscription active -> VPN config available -> user connected
```

---

## 9. VPN provisioning and client connection

Проверить:

- Remnawave user создаётся или обновляется;
- `remnawave_uuid` есть у пользователя с активным VPN-доступом;
- `subscription_url` есть у пользователя с активным VPN-доступом;
- subscription URL доступен через `.org`;
- subscription содержит VLESS;
- subscription содержит XHTTP там, где XHTTP ожидается;
- config импортируется в поддерживаемый клиент;
- пользователь реально подключается;
- внешний IP после подключения соответствует VPN node, например `de-1.cyber-vpn.org`;
- DNS/route leak check не показывает очевидный провал;
- usage counters не ломают UI, даже если статистика временно недоступна.

Если пользователь оплатил/получил trial/invite, но не получил VPN config, это hard blocker для расширения аудитории.

---

## 10. Payments and money flows

Проверить по текущему S2 profile:

- Telegram Stars включён только там, где он должен работать;
- generic payment providers не включены случайно, если `PAYMENTS_ENABLED=false`;
- payment attempts не остаются non-terminal старше 24 часов;
- paid-but-no-access/orphan payments отсутствуют;
- refunds/disputes open queue отсутствует или находится под manual review;
- webhook endpoints отвечают JSON/error без challenge pages;
- duplicate webhook не создаёт двойную выдачу доступа;
- reconciliation включается только при готовых provider credentials и evidence.

Ожидаемый conservative profile:

```text
PAYMENTS_ENABLED=false
TELEGRAM_STARS_ENABLED=true
PAYMENT_RECONCILIATION_ENABLED=false
PAYMENT_AUTORENEWAL_ENABLED=false
PAYMENT_ORPHAN_MAX_AGE_HOURS=24
```

Если включается CryptoBot/Crypto Pay, PayRam, NOWPayments, Digiseller или YooKassa, нужен отдельный provider-specific smoke: success, failure, duplicate webhook, orphan handling, reconciliation.

---

## 11. Admin and support operations

Проверить:

- privileged admin/operator/support/finance пользователи имеют 2FA;
- нет privileged user без TOTP;
- support видит статус пользователя, subscription, provisioning status, но не видит raw secrets;
- support может диагностировать “нет конфигурации”;
- support может инициировать safe resync/reprovision, если это разрешено;
- admin audit log пишет чувствительные действия;
- dangerous actions gated: manual grant, subscription update, refund, delete user, config resync;
- публичный пользователь не получает admin/partner access случайно.

Минимальная S2 цель:

```text
support_can_help_user_without_developer_shell=true
```

---

## 12. Observability

Проверить на домашнем observability сервере:

- Prometheus ready;
- Alertmanager active alerts = 0 или все alerts классифицированы;
- Grafana dashboards доступны;
- Loki принимает логи;
- Sentry health ok;
- blackbox probes работают;
- node exporter/cAdvisor работают;
- prod-app targets up;
- VPN node TCP probes up;
- frontend/API/admin/status/Mini App probes up;
- Telegram bot health visible;
- worker/scheduler lag visible;
- PostgreSQL/Valkey exporters visible;
- home server hardware dashboard показывает SMART/disk/RAM/swap/iowait/network/docker log size.

Проверить sensitive logging:

- в Loki/app logs нет raw token/password/authorization/bot token/private key;
- subscription URLs в admin/support output редактируются или скрываются, если это не пользовательский экран выдачи.

Важно: observability не обязана быть высокодоступной для клиента, но для owner это “глаза”. Если observability недоступна, нельзя расширять аудиторию без ручного компенсирующего контроля.

---

## 13. Outbox, worker and queue state

Проверить:

- worker queue depth = 0 или понятный небольшой backlog;
- retry/dead-letter backlog = 0 или классифицирован;
- `outbox_pending_events=0`;
- `outbox_pending_publications=0`;
- `accepted_no_transport` не растёт без осознанного решения;
- нет новых stale invite/growth/entitlement publications;
- нет ошибок dispatcher/consumer, если event backbone включён.

Текущая S2 интерпретация:

- `accepted_no_transport` допустим только как S2 stabilization marker;
- это не доказательство S3 event backbone readiness;
- перед S3 production growth нужен реальный broker/dispatcher/consumer proof.

---

## 14. Backup, restore and rollback

Проверить:

- свежий PostgreSQL backup существует;
- Remnawave backup/export существует или rebuild strategy актуальна;
- rollback command записан;
- rollback target tag/commit известен;
- restore drill evidence не устарел;
- backup хранится off-host или есть понятная копия вне runtime диска;
- backup не содержит незашифрованные secrets в публичном evidence.

После risky deploy минимум:

```text
pre_deploy_backup_exists=true
rollback_target_known=true
restore_strategy_known=true
```

---

## 15. Security and abuse

Проверить:

- admin host guard работает;
- protected ingress не открывает внутренние порты;
- `/docs` и debug endpoints не открылись публично;
- rate limits работают на auth/trial/payment/support;
- CORS/cookie/security headers ожидаемые;
- noindex/private headers на admin не сломались;
- production logs не содержат secrets;
- dependency/security scan не показывает новый high/critical blocker;
- abuse/support contact pages доступны;
- Terms/Privacy/AUP/Refund/Cookie pages доступны и не содержат placeholder.

---

## 16. User-facing manual smoke

Минимальный ручной сценарий owner:

1. Открыть сайт `cyber-vpn.net`.
2. Открыть pricing.
3. Зарегистрировать или войти тестовым пользователем.
4. Открыть Telegram bot.
5. Открыть Mini App.
6. Проверить Home/Plans/Wallet/Profile.
7. Активировать trial или invite.
8. Убедиться, что subscription active появилась без ручной перезагрузки.
9. Получить VPN config/subscription URL.
10. Импортировать в VPN client.
11. Подключиться.
12. Проверить внешний IP.
13. Проверить, что support/admin видит корректное состояние.
14. Проверить, что observability не показывает P0/P1.

Если пункт 7-11 не проходит, расширять аудиторию нельзя.

---

## 17. Evidence file template

Для каждого deploy/snapshot создавать или обновлять:

```text
docs/evidence/releases/s2-stage-18-stabilization-YYYYMMDD.md
```

Минимальный блок:

```text
snapshot_time_utc=
runtime_tag=
commit=
public_routes=
container_health=
vpn_node_health=
payment_orphan_state=
outbox_state=
alertmanager_state=
known_issues=
decision=
```

---

## 18. Критерий “можно продолжать”

Можно продолжать S2 public operation, если:

- public routes работают;
- auth/register/login работают;
- Mini App не ломает пользовательский поток;
- trial/invite/payment access выдаёт VPN config;
- VPN client реально подключается;
- paid-but-no-access/orphan backlog отсутствует;
- worker/outbox backlog отсутствует или классифицирован;
- Alertmanager/Sentry не показывают P0/P1;
- backup/rollback понятны;
- support/admin могут сопровождать пользователя.

Можно готовить S3 только если:

- S2 стабилен по ежедневным snapshot;
- нет unresolved P0/P1;
- owner принял `S3-STAGE-00`;
- event backbone strategy выбрана;
- production partner payouts/storefronts остаются выключенными до отдельного S3 proof.

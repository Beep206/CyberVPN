# S2-STAGE-18 Post-Launch Stabilization And S3 Readiness Evidence

**Stage:** `S2-STAGE-18: Post-Launch Stabilization And S3 Readiness`
**Date:** 2026-05-23
**Snapshot time:** 2026-05-23T11:15:18Z
**Runtime host:** `prod-app-1`
**Runtime release tag:** `stage2-public-rc.5`
**VPN node:** `de-1.cyber-vpn.org`
**Decision:** `REMAIN_PUBLIC_AND_CONTINUE_STABILIZATION`

---

## 1. Summary

This is the first S2 post-launch stabilization snapshot after `S2-STAGE-17` opened CyberVPN Public Release 1.0 with controlled residuals.

Result:

- customer-facing runtime remains healthy;
- public registration remains open;
- HTTP/3/QUIC remains enabled;
- VPN node remains node-only;
- payment/orphan/refund/dispute queues are empty;
- Alertmanager has zero active alerts;
- no P0/P1 launch blocker was found in this snapshot;
- S3 Partner/Reseller readiness is **not approved yet** because S2 needs more stabilization history and the pending outbox publication backlog should be resolved before growth expansion.

---

## 2. Runtime Configuration

Observed on `prod-app-1`:

```text
CYBERVPN_IMAGE_TAG=stage2-public-rc.5
```

Runtime flags:

```text
OAUTH_ENABLED_LOGIN_PROVIDERS=
PAYMENTS_ENABLED=false
TELEGRAM_STARS_ENABLED=true
PAYMENT_RECONCILIATION_ENABLED=false
PAYMENT_AUTORENEWAL_ENABLED=false
PAYMENT_ORPHAN_MAX_AGE_HOURS=24
REGISTRATION_ENABLED=true
REGISTRATION_INVITE_REQUIRED=false
```

Interpretation:

- public password/email registration remains open;
- OAuth remains intentionally disabled until production credentials and callback evidence exist;
- Telegram Stars remains enabled for Telegram/Mini App;
- generic payment providers remain disabled;
- autoprolongation remains disabled.

---

## 3. Runtime Health

Observed Docker health on `prod-app-1`:

```text
cybervpn-admin                running   healthy
cybervpn-backend              running   healthy
cybervpn-frontend             running   healthy
cybervpn-postgres             running   healthy
cybervpn-postgres-exporter    running   healthy
cybervpn-redis-exporter       running   healthy
cybervpn-remnawave            running   healthy
cybervpn-remnawave-postgres   running   healthy
cybervpn-remnawave-valkey     running   healthy
cybervpn-scheduler            running   healthy
cybervpn-telegram-bot         running   healthy
cybervpn-valkey               running   healthy
cybervpn-worker               running   healthy
```

Data services:

```text
postgres=/var/run/postgresql:5432 - accepting connections
valkey=PONG
remnawave_postgres=/var/run/postgresql:5432 - accepting connections
remnawave_valkey=PONG
```

---

## 4. Public Endpoint Probes

Observed public routes:

```text
https://cyber-vpn.net/ru-RU                              http=200
https://cyber-vpn.net/ru-RU/register                     http=200
https://cyber-vpn.net/ru-RU/pricing                      http=200
https://cyber-vpn.net/ru-RU/status                       http=200
https://cyber-vpn.net/ru-RU/help                         http=200
https://cyber-vpn.net/ru-RU/miniapp/home                 http=200
https://admin.cyber-vpn.net/ru-RU/login                  http=200
https://api.cyber-vpn.net/health                         http=200
https://api.cyber-vpn.net/docs                           http=404
https://cyber-vpn.org/api/sub/<redacted-invalid-token>   http=404
```

HTTP/3/QUIC and HSTS remained present:

```text
alt-svc: h3=":443"; ma=86400
strict-transport-security: max-age=31536000; includeSubDomains; preload
```

---

## 5. Payment, Refund, Dispute And Orphan Queues

Payment posture remains intentionally conservative:

```text
PAYMENTS_ENABLED=false
TELEGRAM_STARS_ENABLED=true
PAYMENT_RECONCILIATION_ENABLED=false
PAYMENT_AUTORENEWAL_ENABLED=false
```

Observed counters:

```text
payment_attempts_by_status|{}
payments_by_status|{}
payment_attempts_nonterminal_gt24h|0
payments_nonterminal_gt24h|0
refunds_by_refund_status|{}
payment_disputes_by_lifecycle_status|{}
payment_disputes_by_outcome_class|{}
refunds_open|0
payment_disputes_open|0
orders_by_order_status|{}
orders_by_settlement_status|{}
wallet_transactions_total|0
```

Interpretation:

- there is no paid-but-no-access backlog older than 24 hours;
- there are no open refunds or disputes;
- generic provider reconciliation remains gated because generic providers are not enabled.

---

## 6. Provisioning, Outbox And Worker State

Customer/VPN state:

```text
mobile_users_total|5
mobile_users_active|3
mobile_users_with_subscription_url|3
mobile_users_with_remnawave_uuid|3
mobile_users_trial_active|1
```

Worker queue logs show no backlog:

```text
email_depth=0
result_backend_depth=0
total_items=0
event=queue_depth_monitoring_complete
```

Open operational event backlog:

```text
outbox_events_by_event_status|{"pending_publication": 17}
outbox_events_open|17
outbox_pending_oldest|2026-05-21 13:40:34.967311+00
outbox_pending_latest|2026-05-22 18:57:48.998333+00
outbox_pending_by_event_family|{"invite": 5, "entitlement": 5, "growth_code": 7}
outbox_pending_by_event_name|{"invite.redeemed": 5, "growth_code.issued": 2, "growth_code.redeemed": 5, "entitlement.grant.activated": 5}
```

Decision:

- this is not a P0/P1 blocker for keeping S2 public because customer runtime, provisioning state and subscription URLs are healthy;
- this is a P2 stabilization item and must be resolved before S3 growth/partner expansion because it affects event publication around invite/growth/entitlement flows.

---

## 7. Support And Admin State

Observed auth/admin posture:

```text
admin_users_by_role|{"admin": 1, "viewer": 4}
admin_users_total|5
admin_users_totp_enabled|1
privileged_admins_without_totp|0
viewer_users_without_totp|3
admin_users_unverified|1
```

Interpretation:

- no privileged active admin without TOTP was observed;
- the unverified user is expected from the public registration smoke;
- public users are still represented in the auth table as `viewer`, so admin/RBAC monitoring must stay active during S2.

Support/ticket DB state:

```text
No dedicated support ticket table is active in this runtime snapshot.
support_profiles table exists.
```

Support remains operationally handled through the configured external support contacts.

---

## 8. VPN Node Health

Observed on `de-1.cyber-vpn.org`:

```text
cybervpn-remnawave-node   Up 3 days
listening ports: 22, 443, 8443, 22230
disk: /dev/sda1 72G total, 4.1G used, 68G available, 6% used
```

Boundary check:

```text
No app, database, GitLab, observability or payment containers were observed on the VPN node.
```

This preserves the rule that the VPN node remains node-only.

---

## 9. Observability And Alerts

Home observability status:

```text
Prometheus Server is Ready.
Alertmanager active_alerts=0
Sentry health=ok
Loki ready
```

Observed relevant containers:

```text
cybervpn-prometheus                 Up
cybervpn-alertmanager               Up
cybervpn-grafana                    Up
cybervpn-uptime-kuma                Up
cybervpn-loki                       Up
cybervpn-blackbox-exporter          Up
cybervpn-cadvisor                   Up
cybervpn-node-exporter              Up
cybervpn-gitlab-runner              Up
sentry-self-hosted-web              Up healthy
sentry-self-hosted-relay            Up
sentry-self-hosted-nginx            Up healthy
sentry-self-hosted-snuba-api        Up healthy
sentry-self-hosted-postgres         Up healthy
sentry-self-hosted-redis            Up healthy
sentry-self-hosted-clickhouse       Up healthy
```

Prometheus target snapshot:

```text
stage2-public-endpoints / cyber-vpn.net, api, admin, status, Mini App, home ops -> up
stage2-vpn-node-tcp / de-1.cyber-vpn.org:443 -> up
stage2-vpn-node-tcp / de-1.cyber-vpn.org:8443 -> up
cybervpn-local-backend -> up
cybervpn-telegram-bot -> up
cybervpn-worker -> up
postgres exporter -> up
redis exporter -> up
```

Loki sensitive-payload check:

```text
docker logs --since=2h cybervpn-loki | egrep -i "(token|password|secret|authorization|bearer|bot_token|private key)"
result=no matches in sampled Loki container logs
```

Home server capacity snapshot:

```text
uptime: 13 days
load average: 0.40, 0.57, 0.63
root disk: 10% used
/srv/storage: 1% used
memory: 46Gi total, 28Gi available
swap: 31Gi total, 933Mi used
```

---

## 10. Backup And Rollback

Recent backup artifacts on `prod-app-1`:

```text
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/cybervpn-20260523T050454Z.dump
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/remnawave-20260523T050454Z.dump
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-command.txt
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-dry-run.log
/srv/cybervpn/backups/daily-20260523T050928Z/cybervpn-20260523T050928Z.dump
/srv/cybervpn/backups/daily-20260523T050928Z/remnawave-20260523T050928Z.dump
/srv/cybervpn/backups/daily-20260523T085847Z/cybervpn-20260523T085847Z.dump
/srv/cybervpn/backups/daily-20260523T085847Z/remnawave-20260523T085847Z.dump
/srv/cybervpn/backups/daily-20260523T100609Z/cybervpn-20260523T100609Z.dump
/srv/cybervpn/backups/daily-20260523T100609Z/remnawave-20260523T100609Z.dump
```

Decision:

- backup presence is confirmed;
- rollback artifacts remain present;
- no new restore drill was executed during this stabilization snapshot.

---

## 11. Logs And Error Review

Sampled app logs for the last 2 hours:

```text
backend: health probes return 200; one expected 405 from GET /api/v1/auth/register probe
worker: queue_depth_monitoring_complete with total_items=0
scheduler: periodic schedule polling continues
telegram-bot: webhook mode running, bot_started, webhook_set
```

Error search:

```text
docker compose logs --since=2h backend/worker/scheduler/bot | egrep -i "traceback|critical|exception|failed|error|paid-but-no-access|orphan|provision"
result=only successful send_otp_email task with is_error=false was observed
```

---

## 12. S2 Success Metrics Snapshot

```text
auth_users_risk_level_total{risk_level="low"} 5
auth_users_risk_level_total{risk_level="medium"} 0
auth_users_risk_level_total{risk_level="high"} 0
auth_users_risk_level_total{risk_level="critical"} 0
auth_users_verification_state_total{verification_state="verified"} 4
auth_users_verification_state_total{verification_state="unverified"} 1
auth_failed_login_attempts_backlog_current 0
auth_bruteforce_attempts_current 0
auth_locked_users_db_current 0
telegram_oidc_user_created_total 0
bot_active_users_total 0
```

The low bot metric counts are expected after runtime restarts and do not indicate a customer-facing failure by themselves.

---

## 13. Known Issues

| Severity | Item | Current impact | Recommendation |
|---|---|---|---|
| Closed | `outbox_events` had 17 `pending_publication` events for invite/growth/entitlement | Closed after this snapshot with `accepted_no_transport` publication payloads because S2 production has `PARTNER_EVENT_BACKBONE_ENABLED=false` and no NATS service | Evidence: `docs/evidence/releases/s2-stage-18-outbox-backlog-closure-20260523.md`; before S3, prove real NATS/dispatcher publication and do not treat accepted-no-transport as broker delivery |
| P2 | Generic payment providers remain disabled | Public generic checkout is not available | Enable providers one by one only after live callback/reconciliation evidence |
| P2 | OAuth remains disabled | Google/GitHub login unavailable | Add credentials, prove callback routes, then enable |
| P2 | Payment reconciliation is disabled | Acceptable while generic payment rails are disabled; must change before broad provider rollout | Enable with provider evidence |
| P3 | `prod-app-1` reports 5 pending OS updates | Not an active runtime blocker | Schedule maintenance window during stabilization |
| P3 | Sentry critical issue count was not queried through application API in this snapshot | Health and alerts are OK, but event-level Sentry review should be performed in UI/API | Add Sentry API token or documented UI review screenshot for future daily evidence |

---

## 14. Stabilization Decision

```text
REMAIN_PUBLIC_AND_CONTINUE_STABILIZATION
```

S2 is stable enough to remain public under the current controlled residuals.

Do not start S3 Partner/Reseller Platform execution yet. Recommended next action is to continue at least one daily S2 stabilization cycle and close the outbox publication backlog before treating the platform as S3-ready.

---

## 15. Documentation And Security Checks

Local checks before committing this evidence:

```text
git diff --check
result=pass
```

```text
git diff --name-only
result=docs-only changes; no dependency manifests changed
```

```text
SECURITY_ARTIFACT_DIR=.tmp/s2-stage18-security-docs GITLEAKS_EXIT_CODE=1 bash scripts/security/scan-secrets.sh
result=no leaks found
scanned_bytes=159109277
```

# Stage 1 Observability Alert Runbook

Date: 2026-05-06
Scope: CyberVPN S1 Controlled Public Beta alert routing and delivery evidence

## Purpose

This runbook defines how S1 alerts are routed, tested and escalated before controlled public beta.

S1 alert delivery is accepted only when both channels are proven:

- Telegram private alert channel: `-5173727789`
- backup email: `backup@cyber-vpn.net`

Local static validation is not enough for go-live. It proves the configuration contract only.

## Runtime Receivers

Alertmanager routes S1 alerts by priority/severity:

| Route | Match | First notification | Repeat | Receiver |
|---|---|---:|---:|---|
| `stage1-p0` | `priority="p0"` | immediate | 30m | Telegram + backup email |
| `stage1-p1` | `priority="p1"` | 30s | 1h | Telegram + backup email |
| `stage1-critical` | `severity="critical"` | immediate | 30m | Telegram + backup email |
| `stage1-warning` | `severity="warning"` | 1m | 2h | Telegram + backup email |
| `stage1-default` | fallback | 30s | 4h | Telegram + backup email |

Production/staging must start Alertmanager with:

```bash
ALERTMANAGER_REQUIRE_LIVE_RECEIVERS=true
ALERTMANAGER_TELEGRAM_BOT_TOKEN=<real bot token>
ALERTMANAGER_TELEGRAM_CHAT_ID=-5173727789
ALERTMANAGER_BACKUP_EMAIL=backup@cyber-vpn.net
ALERTMANAGER_SMTP_FROM=alerts@cyber-vpn.net
ALERTMANAGER_SMTP_SMARTHOST=<smtp host:port>
ALERTMANAGER_SMTP_AUTH_USERNAME=<smtp username if required>
ALERTMANAGER_SMTP_PASSWORD=<smtp password if required>
ALERTMANAGER_SMTP_REQUIRE_TLS=true
```

Do not commit real receiver secrets.

## Local Validation

Run:

```bash
python3 scripts/validate-s1-alerting.py
bash scripts/validate-observability-tooling.sh
cd backend && uv run pytest tests/contract/test_stage1_alerting_assets_contract.py -q --no-cov
```

Expected result:

- S1 alert rule file is loaded by Prometheus.
- Alertmanager config renders with Telegram and email receivers.
- `amtool check-config` passes.
- Contract tests pass.

## Live Delivery Test

After Alertmanager is running with live receiver credentials:

```bash
amtool \
  --alertmanager.url=http://localhost:9093 \
  alert add Stage1AlertDeliveryTest \
  severity=critical \
  priority=p0 \
  service=observability \
  stage=s1 \
  --annotation=summary="S1 alert delivery test" \
  --annotation=description="Synthetic S1 alert delivery test for Telegram and backup email evidence" \
  --annotation=dashboard_path="/d/stage1-controlled-public-beta/stage-1-controlled-public-beta" \
  --annotation=runbook_path="docs/runbooks/STAGE1_OBSERVABILITY_ALERT_RUNBOOK.md"
```

Capture evidence:

- Alertmanager `/api/v2/alerts` response showing `Stage1AlertDeliveryTest`.
- Telegram message screenshot from channel `-5173727789`.
- Backup email screenshot or raw header from `backup@cyber-vpn.net`.
- Timestamp, environment and release commit/tag.

Resolve after evidence capture:

```bash
amtool --alertmanager.url=http://localhost:9093 alert query Stage1AlertDeliveryTest
```

The synthetic alert naturally resolves after its `EndsAt` expires or can be replaced by a short-lived API payload in a staging smoke script.

## P0/P1 Escalation

| Alert family | Escalation |
|---|---|
| Paid-but-no-access at 15m | P1 support/finance review |
| Paid-but-no-access at 1h | P1 owner-visible escalation |
| Paid-but-no-access at 24h | P0 launch blocker; pause paid beta until resolved |
| API/DB/Redis/Remnawave unavailable | P0 if launch flow cannot complete |
| Worker unavailable | P0 if reconciliation/provisioning retry/expiry jobs are impacted |
| Backup stale | P0 before go-live; do not launch without fresh backup evidence |

Primary on-call/support owner: `@Sasha_Beep`
Backup on-call/support owner: `@Sasha_Beep`

P0 acknowledgement target: `<=15m`
P1 acknowledgement target: `<=1h`

## Go-Live Rule

Go-live remains blocked until live alert delivery is proven for both Telegram and backup email.

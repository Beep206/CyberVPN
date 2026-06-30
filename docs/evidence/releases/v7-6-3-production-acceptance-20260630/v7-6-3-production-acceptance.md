# CyberVPN v7.6.3 Production Acceptance Evidence

Task: `CyberVPN_Growth_Codes_v7_6_3_Production_Acceptance_Hardening_TZ_RU.md`

Environment: production `prod-app-1` (`45.87.41.146`)

Evidence captured: 2026-06-30 UTC

This evidence pack contains only sanitized outputs. It must not contain raw
Telegram initData, cookies, JWTs, Remnawave tokens, Cloudflare tokens, private
keys, invite codes, subscription URLs or VPN links.

Related evidence:

- `remnawave-2-8-production-evidence.md`

## Summary

Production acceptance hardening covered:

- Remnawave 2.8.0 image/digest/health/API evidence.
- Real XHTTP host/profile/squad topology and Premium Smart RU config smoke.
- Remnawave node metrics in Prometheus plus a Grafana dashboard.
- Core-normalized Remnawave CPU recording rules and alert fallback text.
- Cabinet RSC/CORS redirect smoke for `my.cyber-vpn.net`.
- Mini App route availability and recent production log review.
- Multi-use invite and child-invite rollback smoke.
- Repository-controlled Remnawave 2.8 fixture tests.

## RSC/CORS Smoke

Command:

```text
HOST=https://my.cyber-vpn.net bash scripts/smoke/customer_site_rsc_routes.sh
```

Result:

```text
exit_code=0
locales=en-EN,ru-RU
affected routes include:
- /rewards
- /rewards/referral
- /rewards/gifts
- /rewards/invites
- /rewards/codes
- /rewards/notifications
- /messages

GET RSC statuses: 200 for existing cabinet routes, 404 for /onboarding
OPTIONS statuses: 400 for existing cabinet routes, 404 for /onboarding
cross-origin Location headers: 0
my.cyber-vpn.net -> cyber-vpn.net redirects: 0
```

Representative accepted lines:

```text
PASS RSC https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/en-EN/messages?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/en-EN/messages?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/rewards/invites?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/rewards/invites?_rsc=customer-site-smoke http=400
PASS RSC https://my.cyber-vpn.net/ru-RU/messages?_rsc=customer-site-smoke http=200
PASS OPTIONS https://my.cyber-vpn.net/ru-RU/messages?_rsc=customer-site-smoke http=400
```

Cloudflare purge:

```text
Agent-side purge: not executed.
Reason: no Cloudflare cache-purge token or Cloudflare env key was available in the local repository or on prod-app-1 app/caddy env paths.
Compensating evidence: external smoke through Cloudflare edge is green and shows no cross-origin redirect.
Required manual action if stale chunks reappear: purge cyber-vpn.net/*, my.cyber-vpn.net/*, api.cyber-vpn.net/* and both hosts' /_next/static/* from Cloudflare dashboard or provide a token with Cache Purge permission.
```

## Mini App Smoke

External route probe with browser-like headers:

```text
https://cyber-vpn.net/ru-RU/miniapp status=200 content_type=text/html; charset=utf-8 location=null
https://cyber-vpn.net/ru-RU/miniapp/home status=200 content_type=text/html; charset=utf-8 location=null
https://cyber-vpn.net/ru-RU/miniapp/health status=200 content_type=application/json location=null
https://cyber-vpn.net/ru-RU/miniapp/diagnostics status=200 content_type=text/html; charset=utf-8 location=null
https://cyber-vpn.net/ru-RU/miniapp/onboarding/code status=200 content_type=text/html; charset=utf-8 location=null
```

Recent production log review:

```text
frontend invalid_initdata matches=0
backend invalid_initdata matches=0
backend samples included one replay rejection, which is expected replay protection for reused Telegram initData
telegram-bot surface config: miniapp_url_host=cyber-vpn.net, miniapp_url_path=/ru-RU/miniapp
client telemetry ingestion: miniapp_client_error_ingested observed without raw initData
```

Telegram Bot menu API smoke:

```text
getMe: ok=true, username_present=true
getChatMenuButton: ok=true, type=web_app, text=Open CyberVPN, web_app_url=https://cyber-vpn.net/ru-RU/miniapp
```

Known evidence limit:

```text
Android Telegram, iOS Telegram and Telegram Desktop physical WebView QA were not executable from this headless production shell.
HTTP route, bot menu and production-log evidence are green; physical device visual confirmation remains manual.
```

## Multi-use Invite And Sorting Evidence

Production read-only snapshot before rollback smoke:

```text
total_invites=3
multi_use_invites=0
multi_use_capacity_invites=0
root_linked_invites=3
child_invites=0
generated_descendant_invites=0
total_redemptions=0
child_invites_issued_total=0
```

Because there were no durable multi-use rows in production, a rollback smoke was
executed in a transaction and rolled back.

Rollback smoke output:

```text
rollback_smoke=true
root_usage_mode=multi_use
root_max_redemptions=10
root_code_fingerprint=70ca4bc21444
redeemers=2
child_invites_total=4
redemptions_with_two_children=2
redeemer_a_visible_invites=2
redeemer_a_status_sort_order=[0,0]
redeemer_a_remaining_redemptions=[1,1]
rollback=completed
```

Repository regression test for client invite sorting:

```text
backend/.venv/bin/python -m pytest backend/tests/unit/api/v1/test_invite_batches.py::test_list_my_invites_sorts_redeemable_multi_use_before_terminal_states -q --no-cov
exit_code=0
result=1 passed

npm --prefix frontend run test -- sort-invite-codes
exit_code=0
result=1 test file passed, 2 tests passed
```

The regression verifies that `/invites/my` serializes a mixed unsorted invite
set as redeemable multi-use and active codes first, followed by used, expired
and revoked states, with `status_sort_order`, `remaining_redemptions` and
`is_redeemable` populated for the client.

## Repository Validation

Targeted checks:

```text
backend/.venv/bin/python -m pytest backend/tests/integration/remnawave backend/tests/unit/api/v1/test_invite_batches.py::test_list_my_invites_sorts_redeemable_multi_use_before_terminal_states backend/tests/unit/application/use_cases/subscriptions/test_generate_config.py backend/tests/unit/test_remnawave_responses.py -q --no-cov
exit_code=0
result=targeted suite passed

bash -n scripts/deploy/stage1-monitoring-deploy.sh
exit_code=0

shellcheck scripts/deploy/stage1-monitoring-deploy.sh
exit_code=0

jq empty infra/grafana/dashboards/remnawave-node-metrics-dashboard.json
exit_code=0

python YAML parse for Prometheus, Alertmanager and monitoring Compose files
exit_code=0
result=YAML_OK

GF_SECURITY_ADMIN_PASSWORD=<dummy> docker compose -f infra/deploy/stage1/monitoring/docker-compose.stage1-monitoring.yml config >/dev/null
exit_code=0
result=COMPOSE_CONFIG_OK
```

Previous broad backend coverage note:

```text
The Remnawave/unit test set passed with --no-cov. Running the same subset with the repository coverage gate failed only because global coverage was below the project threshold; the individual tests were passing.
```

## Monitoring Deployment Evidence

Monitoring deploy command:

```text
STAGE1_PROD_HOST=45.87.41.146 STAGE1_PROD_USER=root STAGE1_PROD_SSH_KEY_FILE=$HOME/.ssh/MainKey2_private_fixed.pem scripts/deploy/stage1-monitoring-deploy.sh
```

Result:

```text
PROMETHEUS_HEALTH=Prometheus Server is Healthy.
GRAFANA_HEALTH=ok 11.5.2
ALERTMANAGER_HEALTH=OK
REMNAWAVE_UP=1 1
```

Updated production monitoring snapshot after forced recreation:

```text
dashboard_title=CyberVPN / Remnawave Nodes
dashboard_uid=remnawave-node-metrics
dashboard_panel_count=10
stage1:remnawave_xhttp_capable_nodes:current=0
stage1:remnawave_premium_smart_ru_xhttp_policy_nodes:current=4
stage1:remnawave_healthy_nodes:current=5
stage1:remnawave_node_metrics_available:current=50
firing Stage1Remnawave* alerts=0
```

The deploy script now recreates `prometheus`, `grafana` and `alertmanager` on
each apply so rule/dashboard files are not left stale in running containers.

The monitoring deployment script was security-hardened:

```text
docker compose config output is discarded instead of written to /tmp
remote paths are strict-validated absolute Linux paths
SSH uses StrictHostKeyChecking=yes and a known_hosts file
temporary monitoring config from previous diagnostics was removed from /tmp on prod-app-1
```

## Rollback Plan

Remnawave provisioning failure:

```text
1. Keep CyberVPN app images unchanged.
2. Repoint Remnawave image tag in prod Compose to the previous known-good tag.
3. docker compose up -d cybervpn-remnawave.
4. Verify /api/system/health, backend Remnawave client health and backup availability.
```

XHTTP client failure:

```text
1. Set REMNAWAVE_FEATURE_XHTTP_FORCE_DISABLED=true in backend runtime env.
2. Recreate backend/worker if required.
3. Verify config smoke: xhttp_enabled=false and stable_fallback_count >= 1.
4. Leave Remnawave XHTTP host in place for later controlled canary.
```

Mini App failure:

```text
1. Roll frontend and telegram-bot images back to the previous accepted tag.
2. Keep TELEGRAM_MINIAPP_URL=https://cyber-vpn.net/ru-RU/miniapp.
3. Verify /ru-RU/miniapp/health and getChatMenuButton.
```

Persistent RSC/CORS redirect:

```text
1. Purge Cloudflare edge/static cache.
2. Roll frontend image back to previous accepted tag if redirect persists.
3. Re-run HOST=https://my.cyber-vpn.net bash scripts/smoke/customer_site_rsc_routes.sh.
4. Check Caddy and Next proxy route guards before reopening cabinet navigation.
```

## Security Notes

- Monitoring services bind only to loopback on prod-app-1.
- Prometheus uses Remnawave metrics credentials rendered on production with
  file permissions `0400`; credentials are not committed.
- Grafana anonymous access is disabled.
- Evidence uses counts, status codes and hash fingerprints instead of secrets.
- No mobile app, desktop app or browser extension source was changed.

## Known Limits At Evidence Time

- Cloudflare purge could not be performed by the agent because no token with
  Cache Purge permission was available.
- Physical Telegram WebView and Mihomo import QA require external devices.
- GitHub/GitLab CI status can only be recorded after the final commit is pushed.
- Runtime fingerprint still reflected the previous application images before
  the final v7.6.3 deploy step; final deploy evidence is generated separately.

## Final Decision

Decision at repository-evidence time: `PARTIAL`.

Repository-controlled hardening, production HTTP/API smokes and monitoring
deployment are complete. Full `VERIFIED` acceptance still depends on external
or post-push evidence:

```text
Cloudflare purge with Cache Purge permission
browser Network screenshot after purge
Android/iOS/Desktop Telegram WebView QA
Mihomo/client import QA on physical clients
GitHub/GitLab CI status for the final pushed commit
post-app-deploy runtime fingerprints for the final pushed commit
```

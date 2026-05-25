# Stage 3 Controlled External Pilot Partner/User Confirmation And Daily Watch

**Stage:** `S3-STAGE-17C`
**Status:** Passed for internal pilot watch; external expansion requires owner-provided pilot list
**Date:** 2026-05-25
**Parent stage:** `S3-STAGE-17: Controlled Partner Pilot`
**Runtime tag:** `s3-stage17-controlled-partner-pilot.3`

---

## 1. Purpose

`S3-STAGE-17C` starts the controlled watch loop after partner runtime, first workspace/code proof, code redemption proof and synthetic paid conversion/earning proof.

This stage is not broad partner expansion. It confirms that the current pilot can remain enabled while we collect evidence before inviting or onboarding external partners.

---

## 2. Current Pilot State

Pilot workspace:

```text
account_key=cybervpn-internal-pilot
workspace_id=95a59856-61ab-465f-8d56-fb10dc4e1d0b
status=active
```

Pilot code:

```text
code=S3PILOT1
is_active=true
markup_pct=0
```

Partner operator:

```text
login=s2_admin_ops
role=admin
workspace_role=owner
2FA=true
```

Controlled synthetic proof state:

```text
customer_binding=active
paid_conversion_fixture=present
paid_conversions=1
available_earnings=2.00 USD
payout_instructions=0
payout_executions=0
payout_accounts=0
outbox_pending_or_failed=0
```

---

## 3. Watch Checklist

Daily watch for the current pilot must cover:

1. production containers are running and healthy;
2. public frontend route returns a valid response;
3. admin route returns a valid response;
4. API health is `ok`;
5. partner workspace remains active;
6. partner code remains active;
7. binding count does not grow unexpectedly;
8. synthetic paid conversion remains clearly marked as synthetic;
9. reporting summary remains `green`;
10. settlement sandbox keeps `live_payout_allowed=false`;
11. payout instructions remain `0` unless explicitly approved;
12. payout executions remain `0` unless explicitly approved;
13. support cases are classified;
14. finance/profile review requests are classified;
15. postback readiness remains paused until credentials are approved;
16. outbox pending/failed remains `0`;
17. no P0/P1 alert is left unresolved.

---

## 4. First Watch Result

First production watch snapshot:

```text
container_count=14
unhealthy_services=0
api_health=ok
frontend_http_status=307
admin_http_status=307
pilot_workspace_active=1
pilot_code_active=1
active_partner_bindings=1
synthetic_paid_fixture_orders=1
synthetic_paid_fixture_earning_events=1
outbox_pending_or_failed=0
payout_instructions=0
payout_executions=0
payout_accounts=0
```

Partner surface snapshot:

```text
cases=1
review_requests=1
payout_history=0
traffic_declarations=0
postback_readiness=action_required
postback_delivery_status=paused
```

Open case:

```text
kind=finance_onboarding
status=waiting_on_partner
notes=Review request kind: finance_profile
```

Open review request:

```text
kind=finance_profile
status=open
available_action=submit_response
```

This is not a launch blocker for the internal pilot, but it blocks partner payout readiness and external partner expansion until classified or completed.

---

## 5. External Pilot Expansion Boundary

External partner/user expansion is allowed only after the owner provides:

1. pilot partner or partner-operator identity;
2. expected partner code or storefront label;
3. allowed cohort size;
4. support contact path;
5. payout expectation: none, sandbox-only, or manual review;
6. confirmation that synthetic paid fixture is not counted as real revenue.

Until then:

```text
EXPAND_EXTERNAL_PARTNER_COHORT=false
KEEP_PARTNER_PILOT_INTERNAL=true
LIVE_PAYOUT_ALLOWED=false
POSTBACK_DELIVERY=paused
```

---

## 6. Decision

```text
S3-STAGE-17C_INTERNAL_PILOT_DAILY_WATCH_PASSED
S3-STAGE-17C_EXTERNAL_PILOT_LIST_REQUIRED_BEFORE_EXPANSION
```

Recommended next working step:

```text
S3-STAGE-18: S3 Stabilization And Scale Decision
```


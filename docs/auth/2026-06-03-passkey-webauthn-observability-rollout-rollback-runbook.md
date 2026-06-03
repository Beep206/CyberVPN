# Passkey/WebAuthn observability, rollout и rollback runbook

Дата: 2026-06-03
Issue: [CYBA-392](/CYBA/issues/CYBA-392)
Parent: [CYBA-386](/CYBA/issues/CYBA-386)
Связанные handoff: [CYBA-388](/CYBA/issues/CYBA-388), [CYBA-389](/CYBA/issues/CYBA-389)
Статус: platform/NodeOps handoff, safe artifact only

## 1. Исполнительное резюме

Passkey/WebAuthn rollout нельзя включать шире sandbox/staging, пока перед
изменением не готовы метрики, scrubbed logs, Sentry privacy controls, dashboard,
alerts, support runbook и проверенный rollback flag path.

Этот документ фиксирует минимальный observability contract и операторский
rollout/rollback порядок для `frontend`, `admin`, `partner` и backend WebAuthn
ceremonies. Артефакт не выполняет production deploy, не меняет production
infrastructure exposure, не требует secrets/SSH и не оперирует customer/payment
data.

## 2. Sources и документация

Repo-local sources:

- `docs/api/2026-06-03-passkey-webauthn-api-contract.md`
- `docs/auth/2026-06-03-passkey-webauthn-ux-spec.md`
- `docs/observability/sentry/07-privacy-pii-scrubbing-and-replay-policy.md`
- `docs/observability/sentry/12-alerting-ownership-routing-and-severity-policy.md`
- `docs/auth/telegram-native-login/13-observability-and-runbook.md`
- `docs/auth/telegram-native-login/14-rollout-plan.md`
- `backend/src/config/settings.py`
- `backend/src/infrastructure/monitoring/metrics.py`

External/vendor docs checked:

- Context7 docs checked: unavailable - MCP returned monthly quota exceeded.
- MDN Web Authentication API
  (`https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API`):
  secure context, registration/authentication ceremonies, challenge, RP ID,
  discoverable credentials, Conditional UI and
  `autocomplete="username webauthn"`.
- W3C WebAuthn Level 3 (`https://www.w3.org/TR/webauthn-3/`):
  WebAuthn/FIDO2 protocol, challenge, origin/RP ID validation and user
  verification requirements.
- Sentry JavaScript options
  (`https://docs.sentry.io/platforms/javascript/configuration/options/`),
  filtering
  (`https://docs.sentry.io/platforms/javascript/guides/connect/configuration/filtering/`)
  and Session Replay privacy
  (`https://docs.sentry.io/platforms/javascript/session-replay/privacy/`):
  `sendDefaultPii` default is `false`; `beforeSend` can edit/drop events;
  Session Replay defaults include masked text and blocked media, with extra
  replay scrub hooks available.
- Prometheus alerting rules
  (`https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/`)
  and histograms (`https://prometheus.io/docs/practices/histograms/`): alerting
  rules use PromQL expressions, `for`, labels, annotations and Alertmanager for
  notification routing; histogram quantiles should be calculated from histogram
  buckets or native histograms.

## 3. Scope и non-goals

In scope:

- Metrics/events/log field contract for WebAuthn ceremonies.
- Sentry privacy and replay acceptance for passkey surfaces.
- Dashboard panels and alert definitions expected from implementation owners.
- Safe rollout phases, rollback decision tree and blast-radius notes.
- Staging/sandbox validation plan and evidence checklist.
- Handoff hooks for backend/frontend/admin/partner/QA/security owners.

Out of scope:

- Production access, deploy, SSH, OpenBao, Sentry org mutation, Caddy/exposure
  changes or live Prometheus/Grafana mutation.
- Direct code changes to auth/session/cookie, admin permissions, billing,
  provisioning, Remnawave, CI/CD or DB migrations.
- Production database downgrade execution. Passkey credential table downgrade is
  destructive for enrolled passkey metadata and must not be used as a normal
  production rollback.

## 4. Feature flags и config levers

Current backend settings expose the rollout levers below. Names are written in
settings style; environment variable spelling should follow the backend settings
loader convention used by the implementation branch.

| Lever | Rollout use | Rollback effect |
| --- | --- | --- |
| `passkey_enabled` | Master backend gate for WebAuthn ceremonies | Stops new passkey option/verify paths when disabled |
| `passkey_customer_enabled` | Customer `frontend` surface gate | Hides/stops customer passkey login/enrollment |
| `passkey_admin_enabled` | `admin` surface gate | Hides/stops admin passkey login/enrollment |
| `passkey_partner_enabled` | `partner` realm gate | Hides/stops partner operator passkey login/enrollment |
| `passkey_conditional_ui_enabled` | Browser Conditional UI/autofill gate | Stops passive autofill path while keeping explicit button possible |
| `passkey_customer_registration_prompt_enabled` | Post-login customer upgrade prompt | Removes prompt without disabling existing passkey sign-in |
| `passkey_admin_security_dashboard_enabled` | Admin compliance dashboard gate | Hides dashboard if metrics/compliance are noisy |
| `passkey_partner_workspace_policy_enabled` | Partner workspace policy/compliance gate | Hides partner workspace policy surface |
| `passkey_admin_counts_as_mfa` | MFA policy decision for admin passkeys | Roll back to TOTP-backed MFA requirement |
| `passkey_dev_enabled` | Local/sandbox enablement | Must remain false for production-like rollout unless explicitly approved |
| `passkey_rp_id` | Production RP ID, expected `cyber-vpn.net` | Rollback does not change RP ID; bad value requires stop and SecurityEngineer review |
| `passkey_allowed_origins` | Approved production origins | Rollback does not broaden origins |
| `passkey_challenge_ttl_seconds` | Challenge lifetime, currently 300 seconds | Tune only after evidence; not a fast rollback lever |
| `passkey_browser_timeout_ms` | Browser prompt timeout, currently 60000 ms | Tune only after UX/QA evidence |
| `passkey_fresh_auth_ttl_seconds` | Fresh-auth validity, currently 300 seconds | Tighten only with admin/partner support readiness |

Operator rule: rollback should prefer disabling narrow UX/surface flags before
touching the master gate. Config changes that broaden origins, loosen cookies,
disable security checks or mutate production exposure require Board and
SecurityEngineer approval.

## 5. Metrics contract

Implementation may either add dedicated passkey metrics or extend existing
auth metrics with bounded labels. The acceptance bar is that the dashboard and
alerts can answer success rate, failure reason, latency, challenge health,
policy posture and rollback flag state without high-cardinality labels.

### 5.1 Dedicated Prometheus metrics

Recommended counters:

| Metric | Labels | Purpose |
| --- | --- | --- |
| `passkey_ceremony_events_total` | `realm`, `surface`, `ceremony`, `entrypoint`, `step`, `status`, `reason` | Main funnel for registration/authentication/reauthentication |
| `passkey_challenge_events_total` | `realm`, `ceremony`, `operation`, `status`, `reason` | Challenge issued/consumed/expired/invalid pressure |
| `passkey_credential_mutations_total` | `realm`, `surface`, `operation`, `status`, `reason` | Add/rename/delete/revoke operations |
| `passkey_fresh_auth_events_total` | `realm`, `surface`, `action_class`, `status`, `method`, `reason` | Step-up success/failure for sensitive actions |
| `passkey_policy_events_total` | `realm`, `surface`, `policy_state`, `status` | Policy/compliance read and enforcement outcomes |
| `passkey_client_capability_events_total` | `surface`, `browser_family`, `capability`, `status` | Support and Conditional UI availability without user identifiers |

Recommended histograms/gauges:

| Metric | Labels | Purpose |
| --- | --- | --- |
| `passkey_ceremony_duration_seconds` | `realm`, `surface`, `ceremony`, `step`, `status` | p95/p99 ceremony and verify latency |
| `passkey_challenge_age_seconds` | `realm`, `ceremony`, `status` | Detect near-expiry or stale challenge verification |
| `passkey_credentials_current` | `realm`, `surface`, `policy_state` | Aggregate credential inventory, no user-level labels |
| `passkey_feature_flag_state` | `realm`, `surface`, `flag` | Dashboard proof of enabled/disabled state |
| `passkey_compliance_summary_current` | `realm`, `surface`, `policy_state` | Aggregate compliance posture for admin/partner |

Allowed label values must be bounded:

- `realm`: `customer`, `admin`, `partner`
- `surface`: `frontend`, `admin`, `partner`, `backend`
- `ceremony`: `registration`, `authentication`, `reauthentication`
- `entrypoint`: `explicit_button`, `conditional_ui`, `identifier_first`,
  `settings_add`, `policy_prompt`, `fresh_auth`
- `step`: `options`, `browser_prompt`, `verify`, `session_issue`,
  `credential_store`, `management`
- `status`: `started`, `success`, `failure`, `cancelled`, `blocked`,
  `unsupported`
- `reason`: `none`, `not_allowed`, `timeout`, `aborted`, `unsupported`,
  `security_error`, `challenge_expired`, `challenge_invalid`,
  `credential_not_found`, `already_registered`, `origin_mismatch`,
  `rp_id_mismatch`, `user_verification_failed`, `rate_limited`,
  `policy_required`, `fresh_auth_required`, `server_error`, `unknown`
- `browser_family`: `chromium`, `safari`, `firefox`, `webview`, `unknown`

### 5.2 Existing auth metric extension

If implementation reuses existing generic metrics, the minimum acceptable
mapping is:

- `auth_flow_events_total{method="passkey",provider="webauthn",step,status}`
- `auth_security_events_total{method="passkey",provider="webauthn",error_type}`
- `auth_request_duration_seconds{method="passkey"}`
- `route_operations_total{operation="<passkey_operation>",status}`

Dedicated metrics are still preferred for challenge health, credential
management and fresh-auth posture because generic auth counters cannot
separate browser cancellation from backend verification defects without
overloading labels.

### 5.3 Cardinality and privacy rules

Never use these as metric labels:

- `user_id`, email, username, phone, Telegram ID, workspace name or account ID
- `credential_id`, `rawId`, public key, `userHandle`, authenticator AAGUID
- raw `challenge`, `challengeId`, `clientDataJSON`, `attestationObject`,
  `authenticatorData`, `signature`
- IP address, user-agent string, request URL with query, payment/subscription
  identifiers or VPN provisioning identifiers
- raw browser exception message

Allowed with care:

- internal request/correlation ID in logs only, not labels
- stable low-cardinality `realm`, `surface`, `ceremony`, `step`, `status`,
  `reason`
- browser family after normalization, not full user-agent
- coarse challenge age bucket or histogram observation, not raw challenge ID

## 6. Structured log contract

All WebAuthn log events must use structured fields and sanitized normalized
reason codes. They must not include request bodies for passkey endpoints.

Recommended backend events:

- `passkey_registration_options_issued`
- `passkey_registration_verify_succeeded`
- `passkey_registration_verify_failed`
- `passkey_authentication_options_issued`
- `passkey_authentication_verify_succeeded`
- `passkey_authentication_verify_failed`
- `passkey_reauthentication_options_issued`
- `passkey_reauthentication_verify_succeeded`
- `passkey_reauthentication_verify_failed`
- `passkey_credential_created`
- `passkey_credential_renamed`
- `passkey_credential_deleted`
- `passkey_policy_read`
- `passkey_compliance_read`
- `passkey_feature_flag_snapshot`
- `passkey_rollout_gate_blocked`
- `passkey_rollback_flag_applied`

Allowed fields:

| Field | Example | Notes |
| --- | --- | --- |
| `event` | `passkey_authentication_verify_failed` | Required |
| `realm` | `customer` | Bounded |
| `surface` | `frontend` | Bounded |
| `ceremony` | `authentication` | Bounded |
| `entrypoint` | `conditional_ui` | Bounded |
| `status` | `failure` | Bounded |
| `reason` | `challenge_expired` | Normalized only |
| `request_id` | `req_...` | Internal correlation only |
| `release` | `backend@...` | Release correlation |
| `environment` | `staging` | No secrets |
| `duration_ms` | `184` | Numeric |
| `challenge_age_ms` | `20132` | Numeric, not identifier |
| `feature_flags` | `passkey_customer_enabled=true` | Flag names and booleans only |
| `policy_state` | `optional` | Bounded |

Forbidden fields:

- raw WebAuthn browser payloads: `clientDataJSON`, `attestationObject`,
  `authenticatorData`, `signature`, `rawId`
- credential public key, credential ID, full AAGUID, `userHandle`
- `Authorization`, `Cookie`, `Set-Cookie`, bearer/JWT/OAuth/TOTP/magic tokens
- payment, Remnawave, OpenBao, VPN config or QR payload material
- customer email/phone/username or workspace/customer names

## 7. Sentry acceptance

Sentry may be used for errors, release health and privacy-safe tags. It must not
be the source of passkey funnel truth; Prometheus/backend metrics remain the
rollout gate.

Required Sentry event tags:

- `auth.method=passkey`
- `webauthn.ceremony=registration|authentication|reauthentication`
- `webauthn.entrypoint=explicit_button|conditional_ui|identifier_first|settings_add|fresh_auth`
- `webauthn.reason=<normalized_reason>`
- `cybervpn.realm=customer|admin|partner`
- `surface=frontend|admin|partner|backend`
- `feature.passkey.enabled=true|false`

Required Sentry privacy controls:

- Keep `sendDefaultPii=false`.
- Use `beforeSend`/`beforeBreadcrumb` to remove passkey request/response bodies,
  query strings, headers, cookies and raw browser WebAuthn payloads.
- Normalize `DOMException` into safe reason codes; do not send raw exception
  message if it contains origin, RP ID, account or browser-specific details.
- Session Replay must keep text/input masking and media blocking. Auth forms,
  passkey management tables, compliance rows and admin/partner step-up modals
  should also use `data-sentry-mask`, `data-sentry-block` or
  `data-sentry-ignore` where the UI implementation exposes sensitive context.
- Network request/response body capture for passkey endpoints remains disabled.

Sentry issue grouping:

- Group `NotAllowedError` user cancellations separately from backend verify
  failures.
- Group `SecurityError`, `origin_mismatch`, `rp_id_mismatch` and repeated
  `challenge_invalid` as release-blocking until explained.
- Treat any event containing raw WebAuthn payload, token, cookie, customer
  identifier or payment/VPN data as a privacy incident and stop rollout.

## 8. Dashboard acceptance

Minimum dashboard sections:

1. Rollout flags and config posture
   - flag state by `realm`/`surface`
   - `rp_id` and allowed-origin proof as sanitized config metadata, not secrets
   - release/environment marker

2. Ceremony funnel
   - started, options issued, browser prompt started, verify success/failure
   - split by `realm`, `surface`, `ceremony`, `entrypoint`
   - success rate and cancellation rate

3. Failure reasons
   - `challenge_expired`, `challenge_invalid`, `origin_mismatch`,
     `rp_id_mismatch`, `unsupported`, `not_allowed`, `timeout`,
     `rate_limited`, `server_error`
   - no raw browser messages

4. Latency and challenge health
   - p95/p99 for options and verify
   - challenge age distribution
   - expired/invalid challenge trend

5. Credential inventory and policy
   - aggregate `passkey_credentials_current`
   - compliance summary for admin/partner surfaces
   - fresh-auth success/failure for sensitive action classes

6. Sentry and release health
   - passkey-tagged issue count
   - privacy scrub smoke status
   - release comparison between current and previous rollout phase

7. Rollback readiness
   - current flag states
   - last rollback drill timestamp/evidence
   - fallback auth path smoke status

Example PromQL patterns:

```promql
sum by (realm, surface, ceremony) (
  rate(passkey_ceremony_events_total{step="verify",status="success"}[5m])
)
/
sum by (realm, surface, ceremony) (
  rate(passkey_ceremony_events_total{step="verify",status=~"success|failure"}[5m])
)
```

```promql
sum by (realm, surface, reason) (
  rate(passkey_ceremony_events_total{step="verify",status="failure"}[5m])
)
```

```promql
histogram_quantile(
  0.95,
  sum by (le, realm, surface, ceremony) (
    rate(passkey_ceremony_duration_seconds_bucket{step="verify"}[5m])
  )
)
```

```promql
sum by (realm, surface, flag) (passkey_feature_flag_state)
```

## 9. Alerting acceptance

Prometheus alert rules should include `for`, severity labels, owner/team labels
and runbook annotations. Alertmanager owns routing, deduplication, silencing and
notification fanout.

Recommended alerts:

| Alert | Condition | Severity | First response |
| --- | --- | --- | --- |
| `PasskeyVerifyFailureRateHigh` | Verify failure rate above 10% for 15m with minimum traffic | high | Pause rollout phase, inspect failure reason split |
| `PasskeyChallengeInvalidSpike` | `challenge_invalid` or `challenge_expired` spikes for 10m | high | Check cache TTL, clock drift, challenge store and client retry loop |
| `PasskeyOriginOrRpMismatch` | Any sustained `origin_mismatch`/`rp_id_mismatch` in staging/prod | critical | Disable affected surface flag, escalate SecurityEngineer |
| `PasskeyAdminPartnerStepUpFailure` | Admin/partner fresh-auth failures above threshold for 10m | critical | Disable passkey step-up gate, keep TOTP fallback |
| `PasskeyCredentialMutationFailureHigh` | Add/delete/rename failure rate above threshold | medium | Pause enrollment prompts, inspect API/store errors |
| `PasskeyUnsupportedBrowserSpike` | Unsupported/secure-context failures spike after UI release | medium | Disable Conditional UI/prompt for affected surface |
| `PasskeySentryPrivacyLeakSuspected` | Scrub smoke or Sentry event sample finds forbidden fields | critical | Stop rollout, disable passkey flags, notify SecurityEngineer |
| `PasskeyRollbackFlagDrift` | Expected rollback flag state differs from observed dashboard state | high | Stop rollout, inspect config propagation |

Release-blocking alert evidence:

- alert rule file or dashboard panel link
- current pending/firing status
- `for` duration and threshold
- runbook annotation target
- owner/team label
- proof of silence/route behavior in staging if available

## 10. Rollout phases

### Phase -1: Observability readiness

Goal: prove that changes are observable before users can use passkeys.

Required gates:

- metrics implemented or generic auth metric mapping accepted
- structured logs scrubbed
- Sentry tags and scrub proof ready
- dashboard panels exist
- alert rules exist with runbook annotations
- rollback flags verified in sandbox
- QA matrix ready in [CYBA-394](/CYBA/issues/CYBA-394)
- final security review path exists in [CYBA-395](/CYBA/issues/CYBA-395)

Blast radius: none for users if flags remain disabled.

### Phase 0: Backend/API deployed with flags off

Goal: ship dormant backend/contracts safely.

Allowed:

- backend passkey endpoints present
- OpenAPI/client generation complete
- metrics/log hooks deployed
- all passkey feature flags disabled for public surfaces

Blocked:

- user-facing prompt
- Conditional UI
- passkey counts-as-MFA
- production enrollment

Blast radius: route availability only; no user flow should change.

### Phase 1: Sandbox/internal

Goal: prove ceremonies with synthetic accounts and no production data.

Allowed:

- `passkey_dev_enabled` only in dev/sandbox
- internal test accounts
- explicit passkey button
- registration/authentication/delete/fresh-auth ceremonies

Required evidence:

- metrics increments for every step
- Sentry sample contains no forbidden fields
- logs contain normalized reasons only
- rollback hides/stops passkey entrypoints

Blast radius: internal test accounts only.

### Phase 2: Staging

Goal: full end-to-end evidence on staging-like config.

Required:

- HTTPS/secure context
- approved staging `rp_id`/origins
- customer/admin/partner surface tests
- unsupported browser and cancellation tests
- challenge expiry/invalid tests
- dashboard and alerts visible
- fallback auth paths verified after rollback

Blast radius: staging users and synthetic test accounts.

### Phase 3: Admin/partner dogfood

Goal: test higher-risk operator surfaces before customer prompts.

Allowed:

- explicit passkey login for selected admin/partner operators
- passkey management
- fresh-auth with TOTP fallback

Blocked:

- `passkey_admin_counts_as_mfa=true` unless SecurityEngineer approves
- broad customer enrollment prompt
- forced passkey-only admin login

Blast radius: selected operators; failed rollout can block admin/partner access
if fallback is misconfigured, so TOTP/password recovery must be smoke-tested.

### Phase 4: Limited customer cohort

Goal: introduce customer passkeys without lockout risk.

Allowed:

- small allowlisted cohort or percentage
- explicit passkey login
- optional add-passkey prompt after non-passkey login
- Conditional UI only after explicit flow metrics are stable

Blocked:

- forced customer passkey enrollment
- removal of password/OAuth/magic-link recovery
- public claims beyond measured evidence

Blast radius: selected customer cohort and support volume.

### Phase 5: Broad rollout

Goal: expand after stable metrics and support readiness.

Required:

- passkey verify success rate is stable
- no release-blocking privacy issues
- support runbook signed off
- rollback drill repeated on current release
- QA and SecurityEngineer gates closed

Blast radius: all enabled surfaces.

## 11. Rollback decision tree

Prefer the narrowest safe rollback that stops the failing path.

1. UX prompt or Conditional UI noise only
   - disable `passkey_conditional_ui_enabled`
   - disable `passkey_customer_registration_prompt_enabled`
   - keep explicit passkey login only if verify success is healthy
   - verify cancellation/unsupported errors return to baseline

2. Customer surface failure
   - disable `passkey_customer_enabled`
   - keep admin/partner only if their metrics are healthy
   - verify password/OAuth/magic-link login and session refresh

3. Admin/partner step-up failure
   - disable passkey fresh-auth enforcement for affected surface
   - keep TOTP fallback
   - set `passkey_admin_counts_as_mfa=false`
   - verify sensitive action can proceed through approved fallback

4. Backend verify/challenge defect
   - disable affected surface flags
   - if cross-surface, disable `passkey_enabled`
   - keep credential table intact
   - verify no new options/challenges are issued

5. RP/origin mismatch or suspected phishing/security issue
   - disable affected surface flag immediately
   - disable `passkey_enabled` if reason is not isolated
   - escalate to SecurityEngineer and Orion CTO
   - do not broaden origins as an emergency workaround

6. Sentry/log privacy leak
   - disable passkey flags
   - stop rollout
   - preserve evidence without exposing raw sensitive values in comments
   - escalate to SecurityEngineer
   - patch scrub rules before any resume

7. Migration/storage defect
   - stop enrollment and verification through flags first
   - do not run production downgrade while credentials may exist
   - only consider DB rollback after Board and SecurityEngineer approval with
     explicit data-loss acknowledgement

Post-rollback verification:

- passkey buttons/prompts hidden or disabled according to chosen flag
- no new `passkey_challenge_events_total{operation="issued"}` for disabled
  surface
- fallback login works for customer/admin/partner as applicable
- existing non-passkey sessions remain valid
- Sentry issue rate returns to baseline
- dashboard flag panel matches intended rollback state
- support team has the affected scope and user-safe wording

## 12. Staging/sandbox validation plan

Use synthetic accounts only. Do not use production credentials, real customer
accounts, payment records, VPN provisioning data or production Sentry/Grafana
mutation.

Validation matrix:

| Scenario | Expected evidence |
| --- | --- |
| Flags off baseline | No passkey UI, no passkey challenge issued, fallback login works |
| Registration success | `registration` funnel success, sanitized log, no forbidden Sentry fields |
| Authentication success | session issued, `authentication` verify success, p95 visible |
| Reauthentication success | fresh-auth event success, sensitive action resumes only after backend success |
| User cancellation | normalized `not_allowed` or `aborted`, no incident alert |
| Challenge expired | `challenge_expired`, retry obtains new challenge |
| Challenge invalid/replay | verify fails, alert candidate increments, no session issued |
| RP/origin mismatch | blocked, critical alert candidate, no origin broadening |
| Unsupported browser | passkey hidden or neutral fallback, `unsupported` metric only |
| Conditional UI | `autocomplete="username webauthn"`, request aborts on route change/unmount |
| Credential delete last method | blocked or safe recovery path per surface policy |
| Rollback flags | UI hidden/stopped, no new challenge issued, fallback auth passes |
| Sentry privacy smoke | event sample and replay sample contain no forbidden fields |

Smallest meaningful commands when config exists:

```bash
rg -n "passkey_|webauthn|WebAuthn" backend/src frontend/src admin/src partner/src docs
```

```bash
uv run pytest tests/integration/test_passkey_webauthn_api.py tests/contract/test_passkey_openapi_contract.py -q --no-cov
```

```bash
promtool check rules infra/prometheus/rules/*.yml
```

```bash
curl -fsS http://localhost:9091/metrics | rg "passkey_|auth_flow_events_total|auth_security_events_total"
```

Commands requiring live/staging services should be run only in the approved
non-production environment by the owner of that environment.

## 13. Evidence checklist

Before any broader rollout, attach or link:

- OpenAPI export containing passkey paths
- targeted backend tests and contract tests
- frontend/admin/partner UX screenshots for desktop and mobile where UI changed
- metrics scrape excerpt for each ceremony and rollback state
- dashboard screenshot or JSON/panel links
- Prometheus alert rule check output
- sanitized structured log samples for success and failure
- Sentry event sample proving safe tags and scrubbed payload
- Session Replay privacy proof for auth/passkey surfaces if replay is enabled
- flag snapshot before rollout, during rollout and after rollback drill
- support runbook note with fallback guidance
- QA matrix result from [CYBA-394](/CYBA/issues/CYBA-394)
- SecurityEngineer review result from [CYBA-395](/CYBA/issues/CYBA-395)

## 14. Implementation handoff hooks

Backend owner for [CYBA-389](/CYBA/issues/CYBA-389):

- add metrics/log hooks around options, verify, credential management and
  fresh-auth branches
- ensure labels use only bounded normalized values
- make passkey request/response bodies excluded from logs and Sentry
- expose aggregate compliance and credential counts without raw credential IDs
- keep DB downgrade out of normal production rollback procedure

Frontend/admin/partner implementation owners:

- add client telemetry wrapper for capability checks, explicit passkey action,
  Conditional UI, cancellation and normalized failures
- abort Conditional UI on explicit flow start, route change and unmount
- add Sentry tags only from the allowed list
- mask/block passkey auth, management and compliance surfaces for replay
- verify fallback auth paths remain visible and usable after flags turn off

QA owner for [CYBA-394](/CYBA/issues/CYBA-394):

- convert the staging/sandbox validation matrix into browser/surface test cases
- include cancellation, unsupported browser, challenge expiry, invalid challenge,
  rollback and privacy evidence cases

SecurityEngineer owner for [CYBA-395](/CYBA/issues/CYBA-395):

- review RP/origin policy, passkey-as-MFA decision, privacy scrub proof and
  admin/partner lockout blast radius before broad rollout

Platform/NodeOps:

- verify dashboard/alert/runbook evidence before each rollout phase
- do not operate production or request production secrets
- escalate privacy, origin/RP mismatch or lockout risks immediately

## 15. Residual risks

- [CYBA-389](/CYBA/issues/CYBA-389) is still shown as `in_progress` in the issue
  dependency data during this heartbeat, so final metric names may need alignment
  with the accepted backend implementation.
- Existing repo has large unrelated worktree changes. This document intentionally
  avoids runtime/config edits.
- Browser WebAuthn support and Conditional UI behavior differ by browser and
  platform; QA evidence must cover the actually supported browser matrix.
- Sentry and Prometheus live project/rule mutation is not performed here.
- Production DB downgrade would delete enrolled passkey metadata/public keys in
  that environment and is not a normal rollback path.

## 16. Done criteria for this ops slice

- metrics/events/log fields are named and privacy bounded
- dashboard panels and alert classes are specified
- feature flags, rollout phases and rollback steps are defined
- blast radius and rollback verification are explicit
- staging/sandbox validation and evidence checklist are ready for QA/security
- no production access, secrets, deploy or infrastructure mutation was performed

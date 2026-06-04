# Passkey/WebAuthn release evidence and rollback pack

Date: 2026-06-04
Issue: [CYBA-439](/CYBA/issues/CYBA-439)
Parent: [CYBA-433](/CYBA/issues/CYBA-433)
Status: passed for non-production release-readiness evidence; production enablement remains blocked pending explicit Board/CTO approval
Runbook: `docs/auth/2026-06-03-passkey-webauthn-observability-rollout-rollback-runbook.md`
API contract: `docs/api/2026-06-03-passkey-webauthn-api-contract.md`

## 1. Executive summary

The Passkey/WebAuthn Stage 2 evidence chain is complete enough for Board/CTO
release review and for a staging-only rollout rehearsal with synthetic accounts.
The completed children referenced by this pack are:

- [CYBA-434](/CYBA/issues/CYBA-434): security architecture review and threat model delta.
- [CYBA-435](/CYBA/issues/CYBA-435): backend hardening and contract tests.
- [CYBA-436](/CYBA/issues/CYBA-436): customer frontend passkey parity and UX hardening.
- [CYBA-437](/CYBA/issues/CYBA-437): admin/partner passkey parity plus privileged-operation UX.
- [CYBA-438](/CYBA/issues/CYBA-438): QA and security validation matrix, final result `PASS`.

No production deploy, production feature enablement, production secrets, real
customer/payment data, VPN credentials or production Remnawave configuration
were used by this release-documentation work. CYBA-438 also states the same
boundary for the QA run.

Production rollout is still `no-go` until the Board/CTO approves the production
change, runtime flag state, owner handoff, rollback drill evidence and any
environment access needed by Platform/NodeOps.

Context7 docs checked: N/A for this CYBA-439 heartbeat because only
documentation was written; no framework/library-dependent code was changed.

## 2. Decisions needed from Board

1. Approve or reject moving from local/QA evidence to a staging-only rollout
   rehearsal using synthetic accounts.
2. Assign the owner for staging flag changes and rollback drill execution if the
   rehearsal is approved. Suggested owner: Platform/NodeOps with Orion CTO as
   technical evidence reviewer.
3. Confirm that production enablement requires a separate approval. This pack
   does not approve production deploy, production secrets access or production
   passkey flags.
4. Decide separately if future scope should include passkey-as-MFA for admin,
   internal-admin override for partner passkey policy, hardware-authenticator
   E2E, or partner-safe customer-specific payment history.

## 3. Proposed next tasks

| Task | Owner | Blocking? | Evidence expected |
| --- | --- | --- | --- |
| Staging rollout rehearsal with all passkey flags initially off | Platform/NodeOps | Yes, before production review | Flag snapshot, synthetic login/enrollment/fresh-auth results, rollback flag snapshot |
| Staging rollback drill | Platform/NodeOps + QA | Yes, before production review | Surface flag off -> UI hidden/stopped, no new challenge issued, fallback auth passes |
| Hardware authenticator E2E, if Board wants device-level confidence | QA/SecurityEngineer | Recommended, not proven here | Registration/authentication/reauthentication with physical authenticator |
| Admin/partner browser smoke screenshots | QA | Recommended | Screenshots or browser JSON for admin and partner surfaces |
| Production enablement request | Orion CTO / Board | Yes, before production | Approval linking this pack, staging evidence, owner list and rollback runbook |

No additional blocker issue is required from CYBA-439 because the remaining
items are gated next-phase approvals, not defects found in the completed QA
matrix.

## 4. Risks

- Real hardware authenticator E2E was not executed. QA coverage used backend
  ceremony/negative tests, `@simplewebauthn/browser` unit mocks and
  CDP/Playwright customer browser smoke.
- Dedicated admin/partner browser smoke harness was not found by QA. Admin and
  partner were covered by targeted unit tests plus conformance lint/build/
  TypeScript gates.
- Live Prometheus/Sentry dashboard and alert evidence was not executed in this
  documentation heartbeat. The runbook defines the required evidence before
  broader rollout.
- The implementation/QA worktree is dirty from completed child tasks. CYBA-439
  did not revert or normalize unrelated implementation changes.
- Production DB downgrade for `20260603_passkey_credentials` is destructive for
  enrolled passkey metadata/public keys and is not a normal rollback path.
- Partner customer-specific payment history is intentionally unavailable after
  the CYBA-437 safe unblock path. Re-enabling it needs separate approved
  product/API/security review.

## 5. Approval requests

No production approval is requested by this document.

Approval must be requested before any of the following:

- production deploy or production feature flag enablement;
- production secrets, real customer/payment data, VPN credentials or Remnawave
  production configuration access;
- broadening `PASSKEY_ALLOWED_ORIGINS`, changing production RP ID, disabling
  secure-cookie constraints or changing production exposure;
- enabling `PASSKEY_ADMIN_COUNTS_AS_MFA=true`;
- adding internal-admin override routes for partner passkey policy;
- running any production DB downgrade that can remove passkey credential data.

## 6. Verification evidence

### 6.1 Completed issue evidence

| Evidence source | Scope | Result |
| --- | --- | --- |
| [CYBA-434](/CYBA/issues/CYBA-434) | Security architecture review and threat model delta over backend/customer/admin/partner passkey surfaces | Done. Risks were mapped to backend/frontend/admin-partner implementation children and QA. No code changed by reviewer. |
| [CYBA-435](/CYBA/issues/CYBA-435) | Backend challenge consume, userHandle guard, kill-switch policy checks, partner realm policy, `adminCountsAsMfa` fail-secure behavior | Done after SecurityEngineer review [CYBA-442](/CYBA/issues/CYBA-442). Targeted backend lint/tests/contract/compile evidence recorded. |
| [CYBA-436](/CYBA/issues/CYBA-436) | Customer fresh-auth header/helper, rename/delete reauthentication, cancel/error/403 UX safety, conditional UI login smoke | Done after SecurityEngineer review [CYBA-441](/CYBA/issues/CYBA-441). Targeted tests, lint and customer browser smoke passed. |
| [CYBA-437](/CYBA/issues/CYBA-437) | Admin/partner WebAuthn helpers, action-scoped fresh-auth, partner policy API, safe removal of unsupported partner payment-history UUID calls | Done. Admin and partner targeted tests, lint and conformance passed. |
| [CYBA-438](/CYBA/issues/CYBA-438) | QA/security validation matrix across backend/customer/admin/partner/secret scan/patch hygiene | PASS. No critical blockers or new defects filed. |

### 6.2 QA matrix from CYBA-438

| Area | Evidence | Result |
| --- | --- | --- |
| Backend lint/compile | `uv run ruff check ...` -> `All checks passed`; `uv run python -m compileall -q ...` -> passed | PASS |
| Backend challenge/fresh-auth unit | Synthetic env `uv run pytest tests/unit/test_passkey_challenges.py tests/unit/test_passkey_fresh_auth.py -q --no-cov` -> `12 passed` | PASS |
| Backend integration negative/security | Synthetic env `uv run pytest tests/integration/test_passkey_webauthn_api.py -q --no-cov` -> `16 passed` | PASS |
| Backend OpenAPI contract | Synthetic env `uv run pytest tests/contract/test_passkey_openapi_contract.py -q --no-cov` -> `3 passed` | PASS |
| Customer API/helper/UI | `npm run test:run -w frontend -- ...login-client-passkeys.test.tsx` -> `4` files, `36` tests passed | PASS |
| Customer browser smoke | `npm run check:login-passkey-smoke -w frontend` at `http://127.0.0.1:9001/en-EN/login`; `identifier: null`, no page/console errors; JSON attachment `/api/attachments/d6097ace-64f2-450f-88e5-68fe5c7bbcba/content`, screenshot `/api/attachments/8c437f1b-fde8-4bf2-86e6-9853211b35f4/content` | PASS |
| Admin unit/API | `npm run test:run -w admin -- ...passkeys.test.ts` -> `3` files, `6` tests passed | PASS |
| Admin conformance | `npm run conformance:partner-admin:admin` -> generated API types in sync, lint passed, Next build passed | PASS |
| Partner unit/API/settings | `npm run test:run -w partner -- ...payments.test.ts` -> `5` files, `29` tests passed | PASS |
| Partner conformance | `npm run conformance:partner-admin:partner` -> generated API types in sync, lint passed, Next build passed | PASS |
| Secret/no-prod-data scan | Targeted secret regex found only synthetic docs env lines; no real secret exposure found | PASS |
| Patch hygiene/runtime cleanup | `git diff --check` -> passed; `ss -ltnp | rg ':9001' || true` -> no listener | PASS |

### 6.3 CYBA-439 documentation verification

Commands run for this pack:

```text
sed -n '1,240p' /home/beep/.local/lib/node_modules/paperclipai/node_modules/@paperclipai/server/skills/paperclip/SKILL.md
env | rg '^PAPERCLIP_(TASK_ID|AGENT_ID|COMPANY_ID|API_URL|RUN_ID|WAKE_REASON|WAKE_COMMENT_ID|APPROVAL_ID|APPROVAL_STATUS)='
curl -fsS ... /api/issues/$PAPERCLIP_TASK_ID/heartbeat-context | jq ...
curl -fsS ... /api/issues/383fbd91-5f4f-4f21-9f7f-5cc08e50a426/heartbeat-context | jq ...
curl -fsS ... /api/issues/ed1c8830-4c4e-4394-92e0-6189e709413b/heartbeat-context | jq ...
curl -fsS ... /api/issues/<CYBA-434..438>/comments?order=asc | jq ...
rg -n 'PASSKEY|WEBAUTHN|RP_ID|RP_NAME|ORIGIN|FRESH_AUTH|passkey|webauthn|fresh-auth|fresh_auth' backend/src backend/tests frontend/src admin/src partner/src docs/api
sed -n '240,690p' backend/src/config/settings.py
sed -n '1,160p' docs/api/2026-06-03-passkey-webauthn-api-contract.md
sed -n '1,740p' docs/auth/2026-06-03-passkey-webauthn-observability-rollout-rollback-runbook.md
git status --short
```

Result: issue blockers and child status were verified through Paperclip API;
runtime flags/RP/origin constraints were verified against `backend/src/config/
settings.py`; existing API contract and rollback runbook were inspected before
writing this release pack.

## 7. Feature flags, env constraints and production gates

Backend settings are defined in `backend/src/config/settings.py`. Environment
variables should use the uppercase names below under the existing settings
loader convention.

| Env/config lever | Default/current posture | Release gate |
| --- | --- | --- |
| `PASSKEY_ENABLED` / `passkey_enabled` | `false` | Master backend gate. Keep `false` in production until explicit approval. |
| `PASSKEY_CUSTOMER_ENABLED` / `passkey_customer_enabled` | `false` | Customer surface gate. Enable only after staging evidence and rollback path. |
| `PASSKEY_ADMIN_ENABLED` / `passkey_admin_enabled` | `false` | Admin surface gate. Requires TOTP/password fallback smoke before enabling. |
| `PASSKEY_PARTNER_ENABLED` / `passkey_partner_enabled` | `false` | Partner surface gate. Requires partner fallback and policy evidence. |
| `PASSKEY_CONDITIONAL_UI_ENABLED` / `passkey_conditional_ui_enabled` | `false` | Enable after explicit login path is stable; fastest rollback for autofill noise. |
| `PASSKEY_CUSTOMER_REGISTRATION_PROMPT_ENABLED` / `passkey_customer_registration_prompt_enabled` | `false` | Prompt-only lever; disable first if enrollment UX creates support load. |
| `PASSKEY_ADMIN_SECURITY_DASHBOARD_ENABLED` / `passkey_admin_security_dashboard_enabled` | `false` | Enable only when compliance data is privacy-safe and useful. |
| `PASSKEY_PARTNER_WORKSPACE_POLICY_ENABLED` / `passkey_partner_workspace_policy_enabled` | `false` | Partner policy/compliance surface gate. |
| `PASSKEY_ADMIN_COUNTS_AS_MFA` / `passkey_admin_counts_as_mfa` | `false` | Must stay `false` until separate enforcement approval. Backend rejects `true` policy update. |
| `PASSKEY_DEV_ENABLED` / `passkey_dev_enabled` | `false` | Must stay `false` in production. Validator rejects production `true`. |
| `PASSKEY_RP_ID` / `passkey_rp_id` | `cyber-vpn.net` | Production validator requires `cyber-vpn.net`; do not change as rollback. |
| `PASSKEY_ALLOWED_ORIGINS` / `passkey_allowed_origins` | `https://cyber-vpn.net`, `https://my.cyber-vpn.net`, `https://admin.cyber-vpn.net`, `https://partner.cyber-vpn.net` | Production origins must be approved HTTPS origins, no wildcard/path/query/fragment. |
| `PASSKEY_CHALLENGE_TTL_SECONDS` / `passkey_challenge_ttl_seconds` | `300` | Validator range `30..300`; tune only after evidence. |
| `PASSKEY_BROWSER_TIMEOUT_MS` / `passkey_browser_timeout_ms` | `60000` | Validator range `15000..120000`; tune only after UX/QA evidence. |
| `PASSKEY_FRESH_AUTH_TTL_SECONDS` / `passkey_fresh_auth_ttl_seconds` | `300` | Validator range `60..900`; tighten only with support readiness. |

Production validators also require `COOKIE_SECURE=true` when passkeys are
enabled in production and reject `PASSKEY_DEV_ENABLED=true`.

## 8. Exact disable and rollback path

Use the narrowest rollback that stops the failing path. Do not broaden origins,
weaken cookies, disable security checks, mutate production exposure or downgrade
the database as the first response.

1. Conditional UI or prompt-only problem:
   - set `PASSKEY_CONDITIONAL_UI_ENABLED=false`;
   - set `PASSKEY_CUSTOMER_REGISTRATION_PROMPT_ENABLED=false`;
   - verify customer fallback login still works and no new conditional UI
     challenge is issued.
2. Customer passkey failure:
   - set `PASSKEY_CUSTOMER_ENABLED=false`;
   - keep admin/partner unchanged only if their metrics are healthy;
   - verify password/OAuth/magic-link fallback and session refresh.
3. Admin or partner step-up failure:
   - disable the affected surface flag: `PASSKEY_ADMIN_ENABLED=false` or
     `PASSKEY_PARTNER_ENABLED=false`;
   - keep `PASSKEY_ADMIN_COUNTS_AS_MFA=false`;
   - verify approved fallback for privileged action, normally TOTP/password path.
4. Backend challenge/verify defect:
   - disable the affected surface flags;
   - if the defect is cross-surface or origin/RP related, set
     `PASSKEY_ENABLED=false`;
   - keep the credential table intact.
5. RP/origin mismatch or suspected security/privacy incident:
   - immediately disable the affected surface flag and escalate to
     SecurityEngineer and Orion CTO;
   - set `PASSKEY_ENABLED=false` if the issue is not isolated;
   - preserve sanitized evidence and do not put raw WebAuthn payloads, tokens,
     cookies, customer identifiers, payment data or VPN data in comments.
6. Migration/storage defect:
   - stop enrollment/verification with flags first;
   - do not run production downgrade while enrolled credentials may exist;
   - request Board and SecurityEngineer approval with explicit data-loss
     acknowledgement before any production DB downgrade.

Post-rollback verification:

- expected passkey buttons/prompts are hidden or disabled;
- disabled surface stops issuing new passkey options/challenges;
- fallback login and sensitive-action fallback pass for affected surface;
- existing non-passkey sessions remain valid;
- dashboard/metrics flag state matches the intended rollback state;
- Sentry/logs contain no raw WebAuthn payloads or secrets.

## 9. Owner handoff checklist

Before requesting production approval, the release owner must attach or link:

- this CYBA-439 pack and the CYBA-438 QA PASS comment;
- staging flag snapshots before rollout, during rollout and after rollback;
- customer/admin/partner fallback auth smoke evidence;
- staging metric scrape or dashboard panel proving ceremony and rollback flag
  state;
- Sentry/log scrub proof for passkey endpoints and UI surfaces;
- admin/partner lockout recovery note;
- support-facing wording for passkey disabled/fallback state;
- explicit confirmation that no real customer/payment/VPN data was used in the
  rehearsal.

## 10. What was not done

- No production deploy or production feature flag enablement.
- No production secrets, production credentials, real customer/payment data,
  VPN credentials or production Remnawave access.
- No production infrastructure, CI/CD, auth/session/cookie, payment, billing,
  subscription, admin-permission or DB-migration change by CYBA-439.
- No full workspace build/test by CYBA-439; this pack uses the completed
  CYBA-438 targeted QA matrix as the release evidence.
- No real hardware authenticator E2E.
- No admin/partner browser screenshot smoke.
- No live Prometheus/Sentry/Grafana mutation or production dashboard check.

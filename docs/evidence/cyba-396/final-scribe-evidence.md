# CYBA-396 Final Scribe evidence: Passkey/WebAuthn

Дата: 2026-06-03
Issue: [CYBA-396](/CYBA/issues/CYBA-396)
Parent: [CYBA-386](/CYBA/issues/CYBA-386)
Scope: release evidence and Board handoff for Passkey/WebAuthn 2.0

## Executive summary

[CYBA-396](/CYBA/issues/CYBA-396) is ready to close from Scribe scope.
All direct prerequisite child issues for [CYBA-386](/CYBA/issues/CYBA-386)
are done:

- [CYBA-387](/CYBA/issues/CYBA-387): security architecture and threat model.
- [CYBA-388](/CYBA/issues/CYBA-388): UX spec.
- [CYBA-389](/CYBA/issues/CYBA-389): backend WebAuthn core, API contracts and OpenAPI.
- [CYBA-390](/CYBA/issues/CYBA-390): customer frontend implementation.
- [CYBA-391](/CYBA/issues/CYBA-391): admin and partner implementation.
- [CYBA-392](/CYBA/issues/CYBA-392): observability, rollout and rollback runbook.
- [CYBA-393](/CYBA/issues/CYBA-393): localization review.
- [CYBA-394](/CYBA/issues/CYBA-394): QA matrix, final PASS.
- [CYBA-395](/CYBA/issues/CYBA-395): final SecurityEngineer review, approved.

Final recommendation: [CYBA-386](/CYBA/issues/CYBA-386) can leave the Scribe
evidence blocker after [CYBA-396](/CYBA/issues/CYBA-396) is marked done. This
does not approve production rollout or production feature-flag enablement.
Production deploy, production secrets, production customer/payment data,
required-mode rollout, direct production feature flags, Remnawave production
config and infrastructure exposure remain separate approval gates.

## Decisions and approvals recorded

| Decision | Evidence |
| --- | --- |
| Board/user moved execution to ТЗ 2.0 autonomous non-production work. | Parent comment [f25954c7](/CYBA/issues/CYBA-386#comment-f25954c7-171b-40a4-a46b-2d2ce1c8b10c); parent docs [ТЗ 2.0](/CYBA/issues/CYBA-386#document-passkey-webauthn-tz-cybervpn) and [plan](/CYBA/issues/CYBA-386#document-plan). |
| Security architecture allowed implementation to proceed with documented secure defaults. | [CYBA-387](/CYBA/issues/CYBA-387#comment-11c6042e-b3dc-4155-82ea-0fd23f55c92c). |
| UX design/spec handoff completed for customer, admin and partner surfaces. | Repo file `docs/auth/2026-06-03-passkey-webauthn-ux-spec.md`; [CYBA-388](/CYBA/issues/CYBA-388#comment-14c86c65-3a82-43a1-8888-5426dc2cbac7). |
| Backend policy endpoints were completed after Board comment rejected read-only-only scope. | [CYBA-389](/CYBA/issues/CYBA-389#comment-6a992024-0f11-4020-a842-15353b33e2f3); repo file `docs/api/2026-06-03-passkey-webauthn-api-contract.md`. |
| QA final rerun passed after blockers [CYBA-428](/CYBA/issues/CYBA-428) and [CYBA-431](/CYBA/issues/CYBA-431). | [CYBA-394](/CYBA/issues/CYBA-394#comment-285614e2-3e56-4e09-8b03-31eded9b594e); repo file `docs/evidence/cyba-394/qa-matrix.md`. |
| Final SecurityEngineer approve was granted after blockers [CYBA-427](/CYBA/issues/CYBA-427) and [CYBA-432](/CYBA/issues/CYBA-432). | [CYBA-395](/CYBA/issues/CYBA-395#comment-8d7ec084-e73a-49ce-9e83-d603fd1f63fd). |

## Release evidence index

| Area | Artifact or source |
| --- | --- |
| Parent requirements | [ТЗ 2.0](/CYBA/issues/CYBA-386#document-passkey-webauthn-tz-cybervpn), [plan](/CYBA/issues/CYBA-386#document-plan). |
| Security architecture | [CYBA-387 document](/CYBA/issues/CYBA-387#document-security-architecture-threat-model). |
| UX spec | `docs/auth/2026-06-03-passkey-webauthn-ux-spec.md`; [CYBA-388 document](/CYBA/issues/CYBA-388#document-ux-spec). |
| Backend API contract | `docs/api/2026-06-03-passkey-webauthn-api-contract.md`; `backend/docs/api/openapi.json`. |
| Observability/runbook | `docs/auth/2026-06-03-passkey-webauthn-observability-rollout-rollback-runbook.md`. |
| Localization review | `docs/evidence/cyba-393/passkey-webauthn-localization-review.md`. |
| QA matrix | `docs/evidence/cyba-394/qa-matrix.md`. |
| QA screenshots | `docs/evidence/cyba-394/screenshots/admin-login-desktop.png`, `admin-login-mobile.png`, `partner-portal-login-desktop.png`, `partner-portal-login-mobile.png`, `partner-login-desktop.png`, `partner-login-mobile.png`, `frontend-login-desktop-post-cyba-431.png`, `frontend-login-mobile-post-cyba-431.png`. |
| Security final review | [CYBA-395 approve comment](/CYBA/issues/CYBA-395#comment-8d7ec084-e73a-49ce-9e83-d603fd1f63fd). |

## Verification summary

| Owner issue | Commands/results recorded |
| --- | --- |
| [CYBA-389](/CYBA/issues/CYBA-389) backend | `uv run ruff check ...` passed; `uv run python -m compileall -q ...` passed; targeted pytest for passkey integration and OpenAPI contract returned `8 passed`; `scripts/export_openapi.py` passed; `git diff --check` passed. |
| [CYBA-390](/CYBA/issues/CYBA-390) customer frontend | `npm run test:run -w frontend -- ...` passed, 4 files / 30 tests; targeted lint passed; JSON parse check passed. Workspace `tsc --noEmit` was attempted and failed on unrelated existing frontend test fixture drift. |
| [CYBA-391](/CYBA/issues/CYBA-391) admin/partner | Current heartbeat tests passed: admin 3 files / 4 tests, partner 2 files / 3 tests, `git diff --check` passed. Earlier checks recorded admin lint/build passed and partner lint passed; partner full build failed only on unrelated commerce `user_uuid` generated params mismatch. |
| [CYBA-392](/CYBA/issues/CYBA-392) runbook | Artifact existence and required sections verified with `test -s`, `wc -l` and `rg` for Context7/vendor docs, metrics, rollback and evidence checklist sections. |
| [CYBA-393](/CYBA/issues/CYBA-393) localization | JSON flatten/compare and placeholder parity passed for reviewed keys; `npm run check:i18n:s1 -w frontend` passed with 39 enabled locales and 73359 runtime fallback-merged checks. |
| [CYBA-394](/CYBA/issues/CYBA-394) QA | Final rerun passed: targeted frontend passkey bundle 4 files / 30 tests; Playwright Chromium desktop/mobile smoke passed for `/en-EN/login`; password submit hydration smoke passed. Previous matrix records admin, partner and backend checks as PASS. |
| [CYBA-395](/CYBA/issues/CYBA-395) security | Backend targeted Passkey/WebAuthn suite returned 23 passed in 55.72s; targeted backend ruff returned all checks passed; admin frontend targeted tests returned 2 files / 2 tests; partner frontend targeted tests returned 3 files / 22 tests. |
| [CYBA-396](/CYBA/issues/CYBA-396) Scribe | Read Paperclip skill; fetched heartbeat context, issue details, comments, child issue list, document list, relevant repo docs, QA matrix, security review, localization review and git status; created this evidence artifact. |

## Security evidence highlights

SecurityEngineer approval confirms:

- `backend/src/infrastructure/cache/passkey_fresh_auth.py` normalizes grant IDs,
  consumes grants one time, checks expiry, principal subject/class, auth realm
  ID, realm key, exact action and endpoint scope.
- `backend/src/presentation/dependencies/passkey_fresh_auth.py` requires
  `X-Fresh-Auth-Grant-Id`; missing or invalid grant returns `403 Fresh passkey
  reauthentication required`.
- `backend/src/presentation/api/v1/auth/passkeys.py` consumes WebAuthn
  challenges before verification and checks realm, audience, principal and
  challenge action before session or fresh-grant issuance.
- Protected admin/partner mutations call fresh-auth guard before state changes
  in `auth/passkey_policy.py`, `partners/routes.py` and `partner_bots/routes.py`.
- Frontend wrappers in admin/partner pass `X-Fresh-Auth-Grant-Id` only after
  passkey reauthentication flow; partner client preserves `X-Auth-Realm`.
- No direct raw passkey challenge/assertion logging path was found in reviewed
  backend/frontend source. Logs use reason codes and credential hashes, not
  raw `challenge`, `clientDataJSON`, `authenticatorData`, `signature` or full
  assertion payloads.

## QA evidence highlights

Final QA PASS confirms:

- Customer `frontend /en-EN/login` requests passkey policy, renders explicit
  `Sign in with passkey`, sets username autocomplete to `username webauthn`,
  keeps password fallback and uses hydrated React submit for password login.
- Admin login desktop/mobile render passkey CTA and `username webauthn`.
- Partner portal login desktop/mobile render passkey CTA and `username webauthn`.
- Partner storefront login desktop/mobile does not expose partner operator
  passkey controls.
- Backend registration/login/reauthentication/session/OpenAPI contract tests
  passed in the QA matrix.

## Missing evidence and residual risks

The following are explicit limitations, not hidden blockers for Scribe closure:

- MR links and pipeline links were not present in wake context, issue comments
  or child issue handoffs. At least [CYBA-390](/CYBA/issues/CYBA-390) records
  that no MR was opened and no branch was pushed. Final evidence therefore
  relies on current worktree, issue comments, repo docs and command outputs,
  not GitLab MR/pipeline artifacts.
- No production deploy, production secrets, production customer/payment data,
  direct push to `main/master`, Remnawave production config or infrastructure
  exposure was used.
- No real browser hardware authenticator ceremony was executed by QA; backend
  ceremony behavior is covered by synthetic integration/security tests.
- No authenticated live CRUD screenshots for customer/admin/partner settings
  were captured because QA had no logged-in backend/account fixture.
- Browser evidence is Chromium headless only; Chrome/Edge/Safari/Firefox
  hardware matrix was not run.
- Rollback behavior is documented and partially covered through flags/contracts;
  no destructive DB downgrade or production/staging flag toggle was executed.
- Direct cross-origin browser backend calls would need CORS header validation
  for `X-Auth-Realm` and `X-Fresh-Auth-Grant-Id`. Current reviewed admin/partner
  clients use same-origin `/api/v1` rewrites, so SecurityEngineer accepted this
  as non-blocking.
- `PasskeyChallengeStore.consume()` normal path relies on Redis/Valkey `GETDEL`;
  older Redis-compatible stores without `GETDEL` would need a Lua fallback
  before entering support scope.
- Sentry hardening can add explicit scrubber marker/tests for
  `X-Fresh-Auth-Grant-Id`, `challengeId`, `rawId`, `clientDataJSON`,
  `authenticatorData` and `signature`.
- Localization: admin/partner source coverage is complete for `en-EN`/`ru-RU`;
  customer frontend has direct Passkey source coverage for `en-EN`/`ru-RU` and
  runtime fallback support for other enabled locales. Russian terminology
  polish remains a non-blocking Mira/Luma decision.
- Partner full build had an unrelated commerce `user_uuid` generated params
  mismatch. It is outside Passkey/WebAuthn scope but should remain tracked
  separately if not already covered.

## Final handoff

Scribe finds no remaining evidence blocker on [CYBA-396](/CYBA/issues/CYBA-396).
The parent [CYBA-386](/CYBA/issues/CYBA-386) may proceed to the parent owner for
final governance disposition after this issue closes.

Context7 docs checked: N/A for this Scribe artifact; no code/library/API/tooling
implementation was changed in [CYBA-396](/CYBA/issues/CYBA-396).

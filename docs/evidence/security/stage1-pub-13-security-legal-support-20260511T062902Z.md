# STAGE1-PUB-13 Security, Legal And Support Gate Evidence

Date: 2026-05-11T06:29:02Z

Result: PASS WITH NOTES for the Stage 1 Controlled Public Beta.

Scope:

- Stage: `STAGE1-PUB-13`
- Current repo commit at check time: `cb042eb77fbc71bec69f4410149e44b4986960bd`
- Runtime image tag in use for Stage 1 app stack: `stage1-beta-rc.2`
- Rebuilt/deployed frontend image digest: `sha256:eadf9769f1c70c9ba73527afadda34101a181f48feb6d8acf202a0a1387d1142`
- Frontend image size: `835388448` bytes

## Decision

The security/legal/support gate can move forward for a controlled beta cohort.

The gate is not a broad-public-launch approval. The remaining operational note is that inbound mailbox DNS for `support@cyber-vpn.net` and `refund@cyber-vpn.net` was not proven during this gate. Telegram/on-call support remains the proven operational path for the first controlled beta users.

## Public Copy Fix Applied

During the gate, stale marketing/support copy was found in non-primary locale bundles and generated frontend bundles.

Removed or replaced launch-unsafe public wording:

- `99.99% UPTIME`
- `99.9`
- `military-grade`
- `zero-day`
- `zero-logs policies`
- `Zero-Log`
- `absolute anonymity`
- `Unlimited Bandwidth`
- `8,000+`
- `All systems operational`

Applied S1-safe wording:

- availability is evidence-bound, not guaranteed as an uptime promise;
- privacy claims are bounded by S1 legal copy and telemetry constraints;
- secondary locales use conservative English fallback copy for the affected marketing/support/status/footer namespaces until real translations are approved.

Files changed:

- `frontend/messages/*/Status.json`
- `frontend/messages/*/Pricing.json`
- `frontend/messages/*/HelpCenter.json`
- `frontend/messages/*/footer.json`
- `frontend/messages/*/landing.json`
- `frontend/src/i18n/messages/generated/*.json`
- `frontend/src/widgets/__tests__/help-faq-server.test.tsx`

## Live Legal Page Verification

Public legal pages returned HTTP `200` after redeploy:

| URL | Result |
|---|---:|
| `https://cyber-vpn.net/en-EN/terms` | 200 |
| `https://cyber-vpn.net/en-EN/privacy-policy` | 200 |
| `https://cyber-vpn.net/en-EN/acceptable-use` | 200 |
| `https://cyber-vpn.net/en-EN/refund-policy` | 200 |
| `https://cyber-vpn.net/en-EN/cookie-policy` | 200 |
| `https://cyber-vpn.net/ru-RU/terms` | 200 |
| `https://cyber-vpn.net/ru-RU/privacy-policy` | 200 |
| `https://cyber-vpn.net/ru-RU/acceptable-use` | 200 |
| `https://cyber-vpn.net/ru-RU/refund-policy` | 200 |
| `https://cyber-vpn.net/ru-RU/cookie-policy` | 200 |

Source evidence read:

- `docs/cybervpn_stage1_launch_docs/72_STAGE1_LEGAL_001_TERMS_OF_SERVICE_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/73_STAGE1_LEGAL_002_PRIVACY_POLICY_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/74_STAGE1_LEGAL_003_ACCEPTABLE_USE_POLICY_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/75_STAGE1_LEGAL_004_REFUND_POLICY_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/76_STAGE1_LEGAL_005_COOKIE_POLICY_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/79_STAGE1_LEGAL_TEXT_OWNER_APPROVAL_EVIDENCE.md`

## Mirror And Admin Host Verification

Mirror redirects were verified without following redirects:

| URL | Result |
|---|---|
| `https://cyber-vpn.org/en-EN/status` | 301 to `https://cyber-vpn.net/en-EN/status` |
| `https://admin.cyber-vpn.org/ru-RU/login` | 301 to `https://admin.cyber-vpn.net/ru-RU/login` |
| `https://admin.cyber-vpn.org/api/v1/admin/audit-log` | 301 to `https://admin.cyber-vpn.net/api/v1/admin/audit-log` |

Protected admin/API checks:

| URL | Result |
|---|---:|
| `https://cyber-vpn.net/api/v1/admin/audit-log` | 404 |
| `https://admin.cyber-vpn.net/api/v1/admin/audit-log` | 401 |
| `https://admin.cyber-vpn.net/ru-RU/login` | 200 |
| `https://cyber-vpn.net/docs` | 404 |
| `https://cyber-vpn.net/openapi.json` | 404 |

Interpretation:

- Public domain does not expose admin audit API.
- Canonical admin host reaches auth guard.
- Admin mirror is redirect-only before auth.
- Public OpenAPI/Swagger routes are hidden.

## Support Gate

Source evidence read:

- `docs/cybervpn_stage1_launch_docs/69_STAGE1_SUP_001_SUPPORT_TICKET_PATH_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/70_STAGE1_SUP_002_SUPPORT_TEMPLATES_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/71_STAGE1_SUP_003_ESCALATION_PROCESS_EVIDENCE.md`

Confirmed S1 support rules:

- `paid-but-no-access` enters `s1_paid_no_access_review`.
- No paid-but-no-access/orphan case may remain older than 24 hours.
- P0 ack target: `<=15m`.
- P1 ack target: `<=1h`.
- Beta support first response target: `<=12h`.
- Refund/support public contacts are present in legal/support copy.

Support template privacy constraints:

- Do not request passwords.
- Do not request 2FA/TOTP seeds.
- Do not request full payment card data, CVV/CVC or private keys.
- Do not paste raw VPN subscription URLs, raw config links or QR payloads into tickets.

Operational note:

- `support@cyber-vpn.net` and `refund@cyber-vpn.net` are present in public copy.
- DNS MX/DMARC evidence for `cyber-vpn.net` and `cyber-vpn.org` returned empty during this gate.
- For controlled beta, Telegram/on-call support is the proven path. Inbound mailbox routing must be proven before widening the public cohort or relying on email-only support.

## Admin/RBAC/2FA/Audit Gate

Source evidence read:

- `docs/cybervpn_stage1_launch_docs/62_STAGE1_ADM_001_ADMIN_ACCESS_PROTECTION_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/63_STAGE1_ADM_002_RBAC_MATRIX_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/64_STAGE1_ADM_003_ADMIN_2FA_ENFORCEMENT_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/65_STAGE1_ADM_004_PRIVILEGED_AUDIT_LOG_EVIDENCE.md`
- `docs/cybervpn_stage1_launch_docs/68_STAGE1_ADM_007_CREDENTIAL_REGENERATION_ADMIN_EVIDENCE.md`

Validated by local security tests:

```text
58 passed in 4.53s
```

Test files:

- `backend/tests/security/test_stage1_admin_access_protection.py`
- `backend/tests/security/test_stage1_admin_rbac_matrix.py`
- `backend/tests/security/test_stage1_admin_2fa_enforcement.py`
- `backend/tests/security/test_stage1_admin_audit_log.py`
- `backend/tests/security/test_stage1_credential_regeneration.py`
- `backend/tests/security/test_stage1_support_ticket_path.py`
- `backend/tests/security/test_stage1_support_templates.py`
- `backend/tests/security/test_stage1_support_escalation.py`

Confirmed constraints:

- Admin routes are host-gated.
- Admin API requires auth on the canonical admin host.
- Production admin access requires 2FA by configuration contract.
- Privileged admin actions are audit logged.
- Audit payloads redact raw subscription/config URLs, invite tokens, passwords and TOTP secrets.
- Support/finance roles are bounded by RBAC and do not receive unsafe privileged actions.

## Secret Scan

Tools:

- `gitleaks`: not installed in the local environment.
- `trivy`: not installed in the local environment.
- Fallback high-confidence repository scan was executed against tracked/untracked files excluding lockfiles, SBOMs and binary/build outputs.

Result:

```text
no high-confidence secret matches
```

Patterns included:

- private key blocks;
- Telegram bot token assignments;
- Cloudflare token assignments;
- Resend/SMTP key assignments;
- Sentry auth token assignments;
- GitHub tokens;
- AWS access keys;
- common runtime secret assignments.

## Dependency Scan

Node production audit:

| Scope | Command result | Finding summary |
|---|---|---|
| root | exit 0 at `--audit-level=high` | no high/critical; residual moderate `postcss` through current Next.js |
| frontend | exit 0 at `--audit-level=high` | no high/critical; residual moderate `postcss` through current Next.js |
| admin | exit 0 at `--audit-level=high` | no high/critical; residual low/moderate `next-intl`/`icu-minify` and moderate `postcss` |

Python runtime audit:

| Scope | Result |
|---|---|
| backend runtime export | no known vulnerabilities |
| Telegram bot runtime export | no known vulnerabilities |
| task worker runtime export | no known vulnerabilities |

Notes:

- `npm audit fix --force` proposes a breaking/downgrade path for Next.js and is not acceptable under the repository version policy.
- Residual moderate/low findings are tracked as non-blocking for the controlled beta.

## Frontend Bundle And Env Scan

Frontend image:

```text
local/cybervpn-frontend:stage1-beta-rc.2
sha256:eadf9769f1c70c9ba73527afadda34101a181f48feb6d8acf202a0a1387d1142
```

One-off smoke:

```text
GET /en-EN/status -> 200
```

Private-marker scan result:

```text
PASS frontend image private-marker scan: no private markers found
```

Route-level public copy scan:

```text
PASS route-level public copy scan: no unsafe promise markers on checked status/pricing/help routes for all locales
```

Frontend copy regression test:

```text
frontend/src/widgets/__tests__/help-faq-server.test.tsx
1 passed, 2 tests passed
```

Raw minified bundle note:

- A raw `99.9` numeric token still appears in the minified frontend bundle.
- It was not present on the checked live public routes and was not treated as public copy evidence.
- The source message files and generated route output are the launch-relevant checks for this wording gate.

## Runtime Health

Stage 1 app containers on the deployment host were checked after the frontend redeploy.

Result:

```text
cybervpn-stage1-cybervpn-admin-1                  running   healthy
cybervpn-stage1-cybervpn-backend-1                running   healthy
cybervpn-stage1-cybervpn-frontend-1               running   healthy
cybervpn-stage1-cybervpn-postgres-1               running   healthy
cybervpn-stage1-cybervpn-postgres-exporter-1      running   healthy
cybervpn-stage1-cybervpn-redis-exporter-1         running   healthy
cybervpn-stage1-cybervpn-remnawave-1              running   healthy
cybervpn-stage1-cybervpn-remnawave-node-local-1   running   healthy
cybervpn-stage1-cybervpn-remnawave-postgres-1     running   healthy
cybervpn-stage1-cybervpn-remnawave-valkey-1       running   healthy
cybervpn-stage1-cybervpn-scheduler-1              running   healthy
cybervpn-stage1-cybervpn-telegram-bot-1           running   healthy
cybervpn-stage1-cybervpn-valkey-1                 running   healthy
cybervpn-stage1-cybervpn-worker-1                 running   healthy
```

## Final Notes

Non-blocking for controlled beta:

- Inbound support/refund mailbox DNS was not proven.
- Low/moderate dependency findings remain below the high/critical gate.
- Secondary locale copy is conservative fallback copy, not final human translation.

Must not be deferred past cohort expansion:

- Prove inbound support/refund mailbox delivery.
- Add full `gitleaks`/`trivy` scans to CI or the release host.
- Replace fallback translations with approved localized copy if non-English cohorts are targeted.

Next stage:

```text
STAGE1-PUB-14: Backup, Restore And Rollback Gate
```

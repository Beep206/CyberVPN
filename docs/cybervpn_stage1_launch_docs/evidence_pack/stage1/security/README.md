# Security Evidence

## Local Evidence Indexed

| Area | Evidence |
|---|---|
| Secrets inventory/policy | `../../../26_STAGE1_INFRA_006_SECRETS_INVENTORY_AND_POLICY.md` |
| Secrets scan | `../../../27_STAGE1_INFRA_007_SECRETS_SCAN_EVIDENCE.md` |
| API route boundary | `../../../30_STAGE1_BE_003_API_ROUTE_BOUNDARY_EVIDENCE.md` |
| Swagger/OpenAPI public-off | `../../../31_STAGE1_BE_004_SWAGGER_PUBLIC_OFF_EVIDENCE.md` |
| CORS/cookie config | `../../../32_STAGE1_BE_005_CORS_COOKIE_CONFIG_EVIDENCE.md` |
| CSRF assessment | `../../../33_STAGE1_BE_006_CSRF_ASSESSMENT_EVIDENCE.md` |
| Rate-limit policy | `../../../34_STAGE1_BE_007_RATE_LIMIT_POLICY_EVIDENCE.md` |
| Edge WAF/rate-limit baseline | `../../../119_STAGE1_INFRA_008_EDGE_WAF_RATE_LIMITING_EVIDENCE.md` |
| Canonical status/error contract | `../../../35_STAGE1_BE_008_STATUS_ERROR_CONTRACT_EVIDENCE.md` |
| Admin access/RBAC/2FA/audit | `../../../62_STAGE1_ADM_001_ADMIN_ACCESS_PROTECTION_EVIDENCE.md`, `../../../63_STAGE1_ADM_002_RBAC_MATRIX_EVIDENCE.md`, `../../../64_STAGE1_ADM_003_ADMIN_2FA_ENFORCEMENT_EVIDENCE.md`, `../../../65_STAGE1_ADM_004_PRIVILEGED_AUDIT_LOG_EVIDENCE.md` |
| Registration kill switch | `../../../113_STAGE1_AUTH_001_REGISTRATION_KILL_SWITCH_EVIDENCE.md` |
| Email/password auth flow | `../../../114_STAGE1_AUTH_002_EMAIL_PASSWORD_FLOW_EVIDENCE.md` |
| Magic link/OTP auth flow | `../../../115_STAGE1_AUTH_003_MAGIC_LINK_OTP_EVIDENCE.md` |
| Admin 2FA auth gate | `../../../116_STAGE1_AUTH_004_ADMIN_2FA_EVIDENCE.md` |
| OAuth provider scope | `../../../117_STAGE1_AUTH_006_OAUTH_PROVIDER_SCOPE_EVIDENCE.md` |
| Delete/export privacy request path | `../../../118_STAGE1_AUTH_007_DELETE_EXPORT_DATA_PATH_EVIDENCE.md` |
| Targeted CVE remediation | `../../../61_STAGE1_DEPENDENCY_CVE_FIX_EVIDENCE.md` |
| Frontend bundle/env scan | `../../../80_STAGE1_FE_010_FRONTEND_BUNDLE_ENV_SCAN_EVIDENCE.md` |
| Local dependency audit | `../../../89_STAGE1_QA_002_DEPENDENCY_AUDIT_EVIDENCE.md` |

## Required Before Go-Live

- Production secret-store evidence and rotation/ownership proof.
- Remote history/token rotation decision where applicable.
- RC lockfile/image/artifact scans.
- Deployed HTTPS CORS/cookie/CSRF proof.
- Real edge WAF/rate-limit/security-event proof for primary/admin/API domains.
- Deployed admin domain/private-access/2FA/persona proof.
- Deployed registration freeze proof for all public account-creation channels.
- Deployed register/verify/login/refresh/logout browser proof for email/password auth.
- Deployed magic-link/OTP browser proof and real email-provider/sender-domain delivery proof.
- Deployed admin browser/API persona proof for mandatory TOTP.
- Deployed Google/GitHub OAuth app/callback/browser proof; non-S1 providers must remain disabled.
- Deployed privacy request mailbox/support queue proof and identity-verification evidence.
- PII/log/Sentry scrubbing evidence.

Current status: local security baseline is strong enough for continued implementation, not production clearance.

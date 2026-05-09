# 117_STAGE1_AUTH_006_OAUTH_PROVIDER_SCOPE_EVIDENCE

Backlog ID: `S1-AUTH-006`  
Status: completed locally; revalidated on 2026-05-09  
Date: 2026-05-08  
Scope: Stage 1 OAuth provider boundary for Controlled Public Beta

## Decision

For S1 Controlled Public Beta, only Google and GitHub may be active OAuth login providers.

The S1 boundary is:

```text
enabled OAuth login providers: google, github
trusted email auto-link providers: google, github
deferred providers: apple, discord, facebook, microsoft, twitter
```

Deferred provider implementations may remain in code for later stages, but they must not become active in S1 through accidental runtime configuration.

Revalidated on 2026-05-09 as the active execution step after `S1-AUTH-004`. The local contract remains valid: only Google and GitHub can pass the S1 OAuth login gate, deferred providers fail closed even if accidentally configured, trusted email auto-linking is limited to Google/GitHub and the S1 provider map requires PKCE for both active providers. This local proof does not imply real Google/GitHub OAuth app credentials, callbacks or browser evidence.

## Covered Behavior

| Area | Local proof |
|---|---|
| Default backend settings | `oauth_enabled_login_providers` and `oauth_trusted_email_link_providers` default to `google,github` |
| Runtime OAuth login gate | Non-S1 providers are rejected even if accidentally added to `OAUTH_ENABLED_LOGIN_PROVIDERS` |
| Trusted email auto-link gate | Non-S1 providers cannot auto-link existing local accounts by email even if misconfigured as trusted |
| PKCE | Google and GitHub login providers require PKCE in the backend provider map |
| Web callback URI | Default web callback resolves to `https://cyber-vpn.net/api/oauth/callback/{provider}` when S1 production origin is configured |
| Native callback URI | Explicit callback override is allowed only for exact allowlisted native URI such as `cybervpn://oauth/callback` |
| Legacy Facebook link endpoints | Facebook authorize/callback endpoints now fail closed before state validation, provider token exchange or account linking |
| Local runtime config | Local backend `.env` OAuth provider lists were reduced to `["google","github"]`; no secret values are recorded here |
| Documentation | OAuth setup guide now documents S1-only Google/GitHub and defers other providers |

## Local Implementation

Changed files:

- `backend/src/config/settings.py`
- `backend/.env.example`
- `backend/src/presentation/api/v1/oauth/routes.py`
- `backend/src/application/use_cases/auth/oauth_login.py`
- `backend/tests/security/test_stage1_oauth_provider_scope.py`
- `backend/tests/security/test_oauth_security.py`
- `backend/tests/unit/api/v1/test_oauth_facebook_linking.py`
- `backend/tests/integration/api/v1/oauth/test_oauth_login.py`
- `backend/tests/unit/application/use_cases/auth/test_oauth_login.py`
- `backend/tests/e2e/auth/test_oauth_e2e.py`
- `docs/auth/oauth-setup-guide.md`

Implementation notes:

1. `settings.oauth_enabled_login_providers` and `settings.oauth_trusted_email_link_providers` now default to `["google", "github"]`.
2. `routes._is_oauth_login_provider_enabled()` now intersects runtime config with the S1 hard allowlist `{"google", "github"}`.
3. Legacy code OAuth linking helpers now call the same provider gate, so Facebook routes fail closed in S1.
4. `OAuthLoginUseCase` only trusts verified email auto-linking for S1-approved providers: Google and GitHub.
5. `.env.example` and `docs/auth/oauth-setup-guide.md` now show Google/GitHub as the S1 baseline and mark other providers deferred.

## Verification

Commands:

```bash
cd backend
PYENV_VERSION=3.13.11 uv run ruff check src/presentation/api/v1/oauth/routes.py src/application/use_cases/auth/oauth_login.py tests/security/test_stage1_oauth_provider_scope.py tests/security/test_oauth_security.py tests/unit/api/v1/test_oauth_facebook_linking.py tests/integration/api/v1/oauth/test_oauth_login.py tests/unit/application/use_cases/auth/test_oauth_login.py tests/e2e/auth/test_oauth_e2e.py tests/unit/config/test_settings.py
PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_oauth_provider_scope.py tests/security/test_oauth_security.py tests/unit/api/v1/test_oauth_facebook_linking.py tests/integration/api/v1/oauth/test_oauth_login.py tests/unit/application/use_cases/auth/test_oauth_login.py -q --no-cov
PYENV_VERSION=3.13.11 pip-audit --skip-editable backend
npm audit --omit=dev --audit-level=high
rg -n '(BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]+|ghp_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9_]{20,}|AIza[0-9A-Za-z_-]{35})' backend/src/config/settings.py backend/.env.example backend/src/presentation/api/v1/oauth/routes.py backend/src/application/use_cases/auth/oauth_login.py backend/tests/security/test_stage1_oauth_provider_scope.py backend/tests/security/test_oauth_security.py backend/tests/unit/api/v1/test_oauth_facebook_linking.py backend/tests/integration/api/v1/oauth/test_oauth_login.py backend/tests/unit/application/use_cases/auth/test_oauth_login.py backend/tests/e2e/auth/test_oauth_e2e.py docs/auth/oauth-setup-guide.md docs/cybervpn_stage1_launch_docs/117_STAGE1_AUTH_006_OAUTH_PROVIDER_SCOPE_EVIDENCE.md
rg -n '(verify=False|ssl=False|eval\(|exec\(|subprocess|shell=True|pickle\.loads|jwt\.decode\([^\n]*verify=False|allow_origins=\["\*"\])' backend/src/config/settings.py backend/.env.example backend/src/presentation/api/v1/oauth/routes.py backend/src/application/use_cases/auth/oauth_login.py backend/tests/security/test_stage1_oauth_provider_scope.py backend/tests/security/test_oauth_security.py backend/tests/unit/api/v1/test_oauth_facebook_linking.py backend/tests/integration/api/v1/oauth/test_oauth_login.py backend/tests/unit/application/use_cases/auth/test_oauth_login.py backend/tests/e2e/auth/test_oauth_e2e.py backend/tests/unit/config/test_settings.py docs/auth/oauth-setup-guide.md
git diff --check -- backend/src/config/settings.py backend/.env.example backend/src/presentation/api/v1/oauth/routes.py backend/src/application/use_cases/auth/oauth_login.py backend/tests/security/test_stage1_oauth_provider_scope.py backend/tests/security/test_oauth_security.py backend/tests/unit/api/v1/test_oauth_facebook_linking.py backend/tests/integration/api/v1/oauth/test_oauth_login.py backend/tests/unit/application/use_cases/auth/test_oauth_login.py backend/tests/e2e/auth/test_oauth_e2e.py docs/auth/oauth-setup-guide.md
```

Results:

| Check | Result |
|---|---|
| Ruff touched OAuth/settings files | PASS: all checks passed |
| OAuth provider scope/security/integration/use-case regression | PASS: 87 passed in 0.55s |
| Backend runtime dependency audit | PASS: no known vulnerabilities found |
| Root npm production dependency audit at high threshold | PASS for high/critical: exit 0; residual moderate `postcss <8.5.10` via `next`, fix currently suggests breaking `npm audit fix --force` |
| High-confidence secret scan over touched S1-AUTH-006 files | PASS: no matches |
| Dangerous-pattern scan over touched S1-AUTH-006 runtime/test/docs files | PASS: no matches; historical evidence command transcript excluded to avoid self-match |
| `git diff --check` on touched files | PASS |
| Docker/container usage | PASS: no containers were running or started for this no-Docker auth boundary task |

## Documentation / Provider References Used

Context7 MCP is not available in this local tool session, so official documentation was used as the required fallback and rechecked on 2026-05-09.

| Reference | Use |
|---|---|
| <https://developers.google.com/identity/protocols/oauth2/web-server> | Confirmed Google web-server OAuth requires registered redirect URIs, client credentials and secure secret handling |
| <https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps> | Confirmed GitHub recommends `state`, exact `redirect_uri` handling and PKCE `code_challenge` / `code_verifier` for OAuth apps |
| <https://www.rfc-editor.org/rfc/rfc7636> | Confirmed PKCE verifier/challenge flow and S256 verification model |

## Remaining Go-Live Evidence

Local `S1-AUTH-006` is complete. Before beta go-live, still capture target-environment evidence:

1. Staging Google OAuth app exists with callback `https://<staging-origin>/api/oauth/callback/google`.
2. Staging GitHub OAuth app exists with callback `https://<staging-origin>/api/oauth/callback/github`.
3. Production Google OAuth app exists with callback `https://cyber-vpn.net/api/oauth/callback/google`.
4. Production GitHub OAuth app exists with callback `https://cyber-vpn.net/api/oauth/callback/github`.
5. Provider client IDs/secrets are stored through the approved secret process, not committed.
6. Browser evidence proves Google login success and invalid/tampered state rejection.
7. Browser evidence proves GitHub login success, PKCE code-verifier exchange and invalid/tampered state rejection.
8. Deployed evidence proves `apple`, `discord`, `facebook`, `microsoft` and `twitter` return disabled-provider responses.
9. Audit/support evidence proves account conflict and linking cases do not silently merge untrusted identities.

## Acceptance

`S1-AUTH-006` is accepted locally because the backend defaults, runtime route gate, trusted-email auto-link gate, tests and documentation now restrict S1 OAuth to Google/GitHub only while keeping deferred provider code unavailable to public S1 flows.

Next ID superseded by `118_STAGE1_AUTH_007_DELETE_EXPORT_DATA_PATH_EVIDENCE.md`; current next ID to execute is `S1-OBS-004` - live alert delivery evidence follow-up.

## 2026-05-09 Ordered Batch Revalidation

`S1-AUTH-006` was re-run as item 12 in the owner-requested ordered batch.

Verification:

```text
cd backend
PYENV_VERSION=3.13.11 uv run ruff check src/presentation/api/v1/oauth/routes.py src/application/use_cases/auth/oauth_login.py tests/security/test_stage1_oauth_provider_scope.py tests/security/test_oauth_security.py tests/unit/api/v1/test_oauth_facebook_linking.py tests/integration/api/v1/oauth/test_oauth_login.py tests/unit/application/use_cases/auth/test_oauth_login.py tests/e2e/auth/test_oauth_e2e.py tests/unit/config/test_settings.py
Result: All checks passed

PYENV_VERSION=3.13.11 uv run pytest tests/security/test_stage1_oauth_provider_scope.py tests/security/test_oauth_security.py tests/unit/api/v1/test_oauth_facebook_linking.py tests/integration/api/v1/oauth/test_oauth_login.py tests/unit/application/use_cases/auth/test_oauth_login.py -q --no-cov
Result: 87 passed in 0.55s
```

Local acceptance remains unchanged. Real Google/GitHub provider apps, secrets, callbacks and browser evidence remain required before public OAuth enablement.

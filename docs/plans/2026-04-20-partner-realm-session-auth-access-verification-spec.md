# CyberVPN Partner Realm, Session, Auth And Access Verification Spec

**Date:** 2026-04-20  
**Status:** Integration closure specification  
**Purpose:** define and verify the runtime rules for partner-host realm resolution, token audience separation, session isolation, cookie isolation, and final access-truth for the external partner portal.

---

## 1. Document Role

This document closes the auth and access seam between:

- partner portal frontend
- backend auth realm model
- admin portal
- official customer frontend
- workspace membership and permission enforcement

It is the runtime verification spec for the separate partner realm.

It must be read with:

- `2026-04-17-storefront-identity-and-access-model-spec.md`
- `2026-04-17-partner-platform-target-state-architecture.md`
- `2026-04-17-partner-platform-api-specification-package.md`
- `2026-04-18-partner-portal-prd.md`
- `2026-04-19-partner-frontend-implementation-and-pre-backend-integration-assessment.md`

---

## 2. Verification Principles

1. Partner portal is a separate realm, not a visual theme over admin or customer sessions.
2. Frontend access checks are not a security boundary.
3. Host-to-realm resolution must be deterministic and testable.
4. Token audience, cookie namespace, principal class, and workspace membership must align.
5. Wrong-host token reuse must fail explicitly.
6. Same identity data across realms must not silently create cross-login.

---

## 3. Canonical Realm Model

The system uses the canonical realm families already present in backend:

- `customer`
- `partner`
- `admin`
- `service`

For the partner portal, the required runtime identity is:

- `realm_type = partner`
- `audience = cybervpn:partner`
- `principal_class = partner_operator`
- `cookie_namespace = partner`

The partner portal must never authenticate against:

- `cybervpn:admin`
- `cybervpn:customer`

unless the request is explicitly going to an internal admin surface or official customer surface outside the partner portal runtime.

---

## 4. Host-To-Realm Mapping

## 4.1 Canonical Mapping Table

| Surface | Host Class | Realm | Audience | Cookie Namespace | Allowed Principal Class | Notes |
|---|---|---|---|---|---|---|
| Partner portal production | partner public host | `partner` | `cybervpn:partner` | `partner` | `partner_operator` | Separate partner workspace surface |
| Partner portal local dev | local partner app host | `partner` | `cybervpn:partner` | `partner` | `partner_operator` | Used by `partner` workspace local runtime |
| Admin portal | admin public host | `admin` | `cybervpn:admin` | `admin` | `admin` | Internal operators only |
| Official customer frontend | customer public host | `customer` | `cybervpn:customer` | `customer` | `customer` | Consumer-facing surface |
| Service integrations | no public UI host | `service` | `cybervpn:service` | none | `service` | Non-browser service tokens |

## 4.2 Host Registration Requirements

The following requirements are mandatory:

1. Every public host must map to exactly one auth realm.
2. Partner host mapping must exist in the auth-realm/storefront host registry before production cutover.
3. Admin and customer hosts must not resolve to the partner realm.
4. Partner host fallback to `admin` is forbidden in production.
5. Realm resolution by explicit header is allowed only for trusted internal flows and must not bypass host policy on public browser traffic.

## 4.3 Done Condition

Host-to-realm mapping is considered verified only when:

- the production partner host resolves to `partner`;
- a valid partner login receives `aud = cybervpn:partner`;
- admin and customer tokens fail on partner host;
- browser cookies issued on partner host do not authenticate admin or customer surfaces.

---

## 5. Token And Cookie Contract

## 5.1 Required Token Claims

Every partner browser session token must contain:

- `sub` or equivalent principal id
- `aud = cybervpn:partner`
- `realm_key = partner`
- `realm_id`
- `principal_type = partner_operator`
- `jti`
- `exp`

If refresh tokens are used, they must carry equivalent realm and audience separation semantics.

## 5.2 Required Cookie Namespaces

The final browser runtime must use realm-separated cookie families.

Recommended canonical names:

- `partner_access_token`
- `partner_refresh_token`
- `partner_session_marker`

Equivalent names are acceptable only if:

- they are namespaced to `partner`;
- they cannot collide with admin or customer cookie names;
- automated tests can assert them deterministically.

## 5.3 Wrong-Host Rules

The following behavior is mandatory:

- partner token on admin host -> reject
- partner token on customer host -> reject
- admin token on partner host -> reject
- customer token on partner host -> reject
- wrong audience with correct subject id -> reject
- wrong realm key with correct audience -> reject

The denial response must be explicit and observable in tests.

---

## 6. Browser Security Contract

The partner portal browser security model must be fixed before implementation.

## 6.1 Cookie Security Rules

Partner session cookies must:

- be `HttpOnly`
- be `Secure` in every non-local environment
- use an explicit `SameSite` policy
- use a realm-specific cookie namespace
- use host and path scoping that prevents accidental reuse by admin or customer surfaces

Recommended default:

- `SameSite=Lax` for primary browser auth cookies unless a stricter policy is compatible with flows
- no shared wildcard cookie domain across partner, admin, and customer browser surfaces

## 6.2 CORS And Origin Rules

Partner-authenticated endpoints must not use wildcard CORS.

Required:

- explicit allowed origins for partner browser traffic
- origin or referrer validation for unsafe browser mutations where cookie auth is used
- no admin-origin browser mutations against partner endpoints unless explicitly allowed by policy

## 6.3 CSRF Strategy

If partner browser auth uses `HttpOnly` cookies, unsafe methods must use a defined CSRF mitigation strategy.

Acceptable patterns:

- CSRF token double-submit or header strategy
- strict same-site plus origin validation if the team standard supports it

The chosen strategy must be consistent across:

- partner login-protected browser mutations
- settings updates
- application draft mutations
- case and review replies
- payout-account mutations

## 6.4 Browser Storage Rules

Partner access and refresh tokens must not be stored in `localStorage` in the cookie-based browser flow.

Frontend may store:

- temporary non-sensitive UI state
- optimistic UI markers
- unsaved draft buffers

Frontend may not store:

- bearer access token
- refresh token
- long-lived session secrets

## 6.5 Refresh Token Rotation Rules

If refresh tokens are used, the implementation must define:

- token family rotation policy
- replay invalidation behavior
- revocation propagation for the refresh token family
- behavior when refresh token is used from the wrong host or realm

## 6.6 Done Condition

Browser security contract is complete only when:

- cookie policy is documented
- CORS/origin strategy is documented
- CSRF strategy is documented
- browser storage restrictions are documented
- refresh token rotation and revocation behavior are documented

---

## 7. Flow Verification Spec

## 7.1 Registration

Partner registration verification must prove:

- registration happens in `partner` realm;
- account creation does not implicitly create an admin session;
- registration does not silently reuse existing customer cookies;
- same email in customer realm does not auto-authenticate partner realm;
- initial session after registration is partner-scoped only if policy allows auto-login;
- otherwise email verification gate is enforced in the partner realm only.

## 7.2 Email Verification

Must prove:

- verification token resolves to partner realm;
- partner email verification cannot verify admin or customer identity by accident;
- post-verification session or redirect returns to partner host;
- verified state is reflected in partner portal bootstrap payload.

## 7.3 Login

Must prove:

- partner login on partner host issues partner-scoped tokens only;
- `aud = cybervpn:partner`;
- partner login does not bootstrap admin cookies;
- wrong-host login with partner credentials does not create a customer or admin session;
- same principal id under a different realm does not bypass audience validation.

## 7.4 Refresh

Must prove:

- refresh token respects `partner` realm;
- refresh on wrong host fails;
- revoked session cannot refresh;
- refreshed access token preserves `aud`, `realm_key`, and `principal_type`.

## 7.5 Logout

Must prove:

- partner logout revokes partner session only;
- admin or customer sessions remain untouched;
- cookies for partner host are cleared;
- revoked partner token no longer works against partner APIs.

## 7.6 Forgot Password And Reset Password

Must prove:

- password reset request is realm-aware;
- reset token is valid only for partner realm;
- reset completion returns user to partner host;
- reset does not issue admin or customer cookies.

## 7.7 MFA

Must prove:

- MFA challenge is executed in partner realm;
- MFA completion upgrades partner session only;
- failed MFA does not create a partial authenticated state;
- backup code use and revocation remain realm-scoped.

## 7.8 Session Revocation

Must prove:

- partner session revocation invalidates all partner access paths;
- revocation is enforced on API and page bootstrap;
- revoked partner token cannot call workspace APIs even if membership is valid.

---

## 8. Final Access Gate Truth

Frontend route guards are UX gates only.

Final access truth is determined by all of the following:

1. host-to-realm resolution
2. session audience
3. session realm key
4. principal class
5. workspace membership
6. workspace role
7. permission keys
8. route/surface policy
9. workspace status
10. lane status and readiness overlays where required

No frontend-only role heuristic may be treated as final authorization.

---

## 9. Access Enforcement Matrix

| Check Layer | Owner | Required For | Failure Result |
|---|---|---|---|
| Host-to-realm resolution | backend auth realm resolver | every browser request | deny or resolve to correct realm |
| Token audience validation | backend auth dependency | every authenticated API call | `401` |
| Principal class validation | backend auth dependency | realm-specific endpoints | `403` |
| Workspace membership lookup | partner workspace dependency | workspace-scoped routes | `403` |
| Permission key enforcement | partner workspace dependency | route action or resource family | `403` |
| Route/surface UX hiding | frontend runtime | menus, navigation, page affordances | hidden or read-only |

---

## 10. Negative Verification Matrix

The following tests are mandatory.

| Test | Expected Result |
|---|---|
| Partner token used on admin portal | rejected |
| Partner token used on customer frontend runtime | rejected |
| Admin token used on partner portal | rejected |
| Customer token used on partner portal | rejected |
| Partner cookie not present on admin host | verified |
| Partner cookie not present on customer host | verified |
| Same email exists in customer and partner realm | no cross-login |
| Wrong realm header on public browser request | does not bypass host mapping |
| Valid partner token with wrong audience | rejected |
| Valid partner audience with no workspace membership | authenticated but workspace APIs denied |
| Valid workspace membership with missing permission key | route/resource denied |

---

## 11. Required Test Evidence

The following evidence must be captured before integration closure:

- auth bootstrap response from partner host
- decoded partner access token claims
- cookie inventory by host
- negative test logs for wrong-host token usage
- revoked token rejection evidence
- workspace permission rejection evidence
- E2E screenshot or API evidence for partner login and session bootstrap

---

## 12. Closure Conditions

This spec is complete only when:

1. partner host is mapped to the partner realm in every target environment;
2. partner browser sessions issue and validate `cybervpn:partner` tokens;
3. cookie namespace separation is enforced;
4. wrong-host and wrong-audience token use is blocked;
5. workspace membership and permission keys are the final authorization boundary after auth;
6. E2E auth tests can be written and executed without product clarification.

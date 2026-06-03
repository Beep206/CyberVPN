# Passkey/WebAuthn UX spec для frontend, admin, partner

Дата: 2026-06-03
Issue: [CYBA-388](/CYBA/issues/CYBA-388)
Parent: [CYBA-386](/CYBA/issues/CYBA-386)
Статус: UX handoff, готово для implementation follow-up
Scope: design/spec only, без production code, secrets, customer/payment data и deploy

## 1. Исполнительное резюме

Passkey/WebAuthn вводится как phishing-resistant способ входа и step-up, но не как замена всех существующих способов входа в первом rollout. UX обязан поддержать три поверхности с разными trust expectations:

- `frontend`: customer-friendly passwordless login, post-login upgrade, passkey management и recovery guard.
- `admin`: более строгий login, TOTP-aware policy, fresh auth step-up для sensitive actions, compliance dashboard и break-glass states.
- `partner`: partner-operator login в realm `partner`, workspace policy, compliance table, finance/compliance/team/API step-up и четкая storefront boundary.

Основной design decision: passkey должен быть видимым явным действием и одновременно работать через Conditional UI/browser autofill. Только скрытый autofill недостаточен для recognition, а только отдельная кнопка не покрывает user expectation современных passkeys.

## 2. Sources и evidence

Primary repo requirements:

- Parent issue document: [passkey-webauthn-tz-cybervpn](/CYBA/issues/CYBA-386#document-passkey-webauthn-tz-cybervpn), revision 2.
- Current auth state: `docs/auth/2026-04-21-registration-auth-current-state.md`.
- Existing surfaces inspected:
  - `frontend/src/app/[locale]/(auth)/login/login-client.tsx`
  - `admin/src/app/[locale]/(auth)/login/login-client.tsx`
  - `partner/src/app/[locale]/(auth)/login/login-client.tsx`
  - `frontend/src/app/[locale]/(dashboard)/settings/sections/SecuritySection.tsx`
  - `admin/src/features/security/components/security-two-factor-console.tsx`
  - `partner/src/features/partner-settings/components/settings-foundation-page.tsx`

External documentation checked:

- MDN Web Authentication API: secure context, discoverable credentials, Conditional UI and `autocomplete="username webauthn"`.
- W3C WebAuthn Level 3: discoverable credentials, user verification, RP/origin constraints.
- FIDO Alliance passkey design guidelines: passkey UX must be understandable, recoverable and avoid lockout.
- SimpleWebAuthn docs attempted through Context7 and `ctx7`, both blocked by monthly quota. Official site `https://simplewebauthn.dev/docs/packages/browser` was checked as fallback for the recommended client package, but this UX spec does not define production API signatures beyond the parent TZ contract.

Context7 docs checked: unavailable - MCP and `ctx7` returned monthly quota exceeded. No code was written or changed in this task.

Visual-truth gate: this issue is spec-only and did not render new UI. Implementation issues must provide desktop and mobile screenshots/previews before UX verdict.

## 3. Design lenses used

- Cognitive Load: keep one primary passkey action per state, do not make users choose between five auth methods at once.
- Jakob's Law: use expected passkey patterns: "Sign in with passkey", username autofill, platform authenticator prompt, explicit fallback.
- Fitts's Law: primary passkey buttons use existing comfortable touch target and remain reachable in mobile thumb zones.
- Progressive Disclosure: expose policy, recovery and compliance complexity only after the user enters security settings or admin/partner management surfaces.
- Recognition over Recall: show passkey status, last used, device/type labels, policy mode and next action; do not ask users to remember whether an account has a passkey.
- WCAG POUR: keyboard, focus, ARIA live regions, reduced motion, RTL and non-icon-only status.
- Information Scent: labels must lead to expected places: "Passkeys" under Security, "Workspace security" for partner policy.
- Forms & Errors: inline validation, retry paths, no dead-end `NotAllowedError` or challenge-expired states.
- Trust & Safety: state that CyberVPN does not store biometrics/private keys without using fear-based copy.
- Ethics: no forced passkey enrollment for customers, no hidden downgrade, no confirmshaming for fallback.
- Platform Context: customer login, desktop admin dashboard, partner workspace and storefront routes have different expectations.

## 4. IA и surface placement

### 4.1 Shared IA

All three apps need the same conceptual surfaces:

| Surface | Purpose | Required placement |
|---|---|---|
| Login passkey entry | Passwordless/discoverable credential login | Existing `AuthFormCard` in each app |
| Conditional UI | Browser autofill passkey suggestion | Existing username/email field with `autocomplete="username webauthn"` |
| Passkey management | List/add/rename/delete current user's passkeys | Security settings/profile area |
| Fresh auth step-up | Confirm sensitive action | Modal or interstitial before action retry |
| Policy/compliance | Admin/partner visibility over posture | Existing Security/Organization surfaces |
| Unsupported/recovery | Fallback without dead end | Inline alert and existing auth methods |

### 4.2 Customer `frontend`

Use existing customer auth hierarchy:

- In `LoginClient`, place explicit `Sign in with passkey` button at the top of `AuthFormCard`, before `SocialAuthButtons`.
- Keep `SocialAuthButtons`, password form, magic-link link and registration link as fallbacks.
- Use the current identifier input as Conditional UI anchor and set `autocomplete="username webauthn"` when passkey flags/capabilities allow it.
- Add passkey card in `Settings / Security`, between `Two-Factor Authentication` and `Password`, because passkey is an auth method and should be seen before credential maintenance.
- Add optional post-login `PasskeyUpgradePrompt` after successful non-passkey login. It must be dismissible, cooldown-limited and never block VPN onboarding/payment/config retrieval.

### 4.3 Admin `admin`

Use existing security console patterns:

- In admin login, place `Sign in with passkey` above the password form. If policy is `required`, label it as the primary route and show password/TOTP only as allowed recovery/fallback.
- Add personal passkeys under `Admin / Security / Passkeys` or equivalent profile security entry using `SecurityPageShell`.
- Add admin compliance dashboard as a separate permission-gated tab/page, not mixed into personal settings.
- Sensitive actions must either open a fresh auth modal before submit or handle backend `FRESH_AUTH_REQUIRED` by launching step-up and replaying the pending action once.
- Break-glass states are visible as warnings/runbook links, not as a normal CTA.

### 4.4 Partner `partner`

Respect partner realm and workspace IA:

- In partner login, add explicit passkey button above the password form and preserve `X-Auth-Realm=partner` or host-based realm resolution for every passkey request.
- Add operator passkey management under `Partner Portal / Settings / Security / Passkeys`.
- Add workspace policy under `Partner Portal / Organization / Security`, near team/access controls rather than generic notifications settings.
- Add compliance table for partner owner/admin roles.
- Do not expose partner passkey UI on public storefront routes. Storefront customer passkeys require separate principal/policy review.

## 5. Shared interaction specifications

### 5.1 Capability detection

On client mount only:

1. Check feature flags from frontend env and backend capabilities endpoint.
2. Check browser support for WebAuthn and Conditional UI.
3. If unsupported, hide the passkey primary button only when the layout would otherwise imply a broken action. Show a small inline fallback note when the user explicitly tries passkey.
4. If non-secure context, show dev/staging warning and keep password/OAuth/magic link available.
5. Never run WebAuthn APIs during SSR.

Acceptance:

- Unsupported browser does not create a blank space or disabled primary CTA.
- Secure-context warning is not scary and points to existing fallback.
- Capability checks must not send credential IDs, raw challenges or full user objects to telemetry.

### 5.2 Explicit passkey login

Flow:

1. User clicks `Sign in with passkey`.
2. UI requests authentication options from backend.
3. Browser authenticator prompt opens.
4. User verifies with device unlock/biometric/PIN/security key.
5. UI sends assertion to verify endpoint.
6. Backend issues existing httpOnly cookie session.
7. If backend returns `requires_2fa`, reuse existing pending 2FA flow.
8. Redirect to safe `redirect` target or default dashboard.

UX rules:

- Button label: `Sign in with passkey` / `Войти с passkey`.
- Loading label: `Checking passkey...` / `Проверяем passkey...`.
- Cancel is neutral: "Operation cancelled. Try again or use another sign-in method."
- Challenge expired gets a retry CTA.
- Unknown/realm mismatch errors remain generic before authentication to reduce enumeration.

### 5.3 Identifier-first passkey login

Flow:

1. User enters email/login.
2. User clicks passkey action near the form or submits passkey mode.
3. Backend options may use identifier to narrow credentials.
4. Browser prompt opens.
5. Verify and redirect as above.

UX rules:

- Do not require identifier for discoverable credential flow.
- If identifier does not match a passkey, message must not confirm account existence.
- Keep password submit visible unless policy says passkey required.

### 5.4 Conditional UI/browser autofill

Flow:

1. Login form loads with username field using `autocomplete="username webauthn"`.
2. UI starts conditional mediation only when supported and enabled.
3. Browser shows saved passkeys alongside saved passwords when user interacts with the field.
4. Selection completes authentication and follows the same verify/redirect path.

UX rules:

- Conditional UI is additive. It must not replace the visible passkey button.
- Abort conditional request when explicit passkey login starts, when route changes, or when component unmounts.
- Do not show custom fake dropdowns that mimic browser passkey UI.
- Track only availability/used/succeeded/failed, never credential details.

### 5.5 Registration/enrollment after login

Entry points:

- Security settings primary action: `Add passkey`.
- Post-login upgrade prompt for customers with zero passkeys.
- Admin/partner policy prompt when recommended/required/grace period applies.

Flow:

1. User starts `Add passkey`.
2. UI checks fresh session. If not fresh, open fresh auth step-up first.
3. Backend returns registration options.
4. Browser creates credential.
5. Backend verifies and stores credential.
6. UI asks for a friendly passkey name if not captured before creation.
7. Success state returns to list and highlights the new passkey.
8. UI suggests adding a second method if user has weak recovery posture.

UX rules:

- Do not claim "biometric saved" or "fingerprint stored".
- Recommended copy: "CyberVPN stores a public key, not your biometrics or device unlock data."
- Default name can be device/browser-derived only if backend provides safe metadata. Otherwise use `Passkey added Jun 3, 2026`.
- Registration failure must preserve context and offer retry.

### 5.6 Management CRUD

List fields:

- Friendly name.
- Type: platform, security key, synced passkey, unknown.
- Created date.
- Last used date or `Never used`.
- Current device hint if safely known.
- Policy status: optional, recommended, required, grace period, revoked.

Actions:

- Rename inline or in small dialog.
- Delete/revoke with fresh auth.
- Add another passkey.
- Add/review recovery methods.

Delete guard:

- Customer: block deletion of last login/recovery method and offer alternatives.
- Admin: require fresh auth and warn for `super_admin`.
- Partner: honor workspace policy, role requirements and grace exceptions.

### 5.7 Fresh auth step-up

Step-up modal content:

- Title: `Confirm it is you`.
- Body explains the target action, not WebAuthn internals.
- Primary: `Use passkey`.
- Secondary: `Use TOTP` only when backend policy allows it.
- Cancel returns to the previous screen with the pending action unsubmitted.

Rules:

- UI may preflight step-up before submit, but backend remains source of truth.
- Fresh auth marker should have visible expiry where relevant, e.g. "Confirmed for this session action window".
- Do not silently downgrade from passkey to password for admin/partner sensitive actions.

## 6. State and error model

| State/code | UX treatment | Retry/fallback |
|---|---|---|
| Feature disabled | Hide passkey entry; no empty layout gap | Existing auth methods |
| Unsupported browser | Inline neutral note after attempt | Password/OAuth/magic link/TOTP |
| Non-secure context | Inline warning for dev/staging | HTTPS or fallback |
| User cancelled | Neutral status, no red alert unless repeated with policy required | Retry or fallback |
| Challenge expired | Warning with retry CTA | Request new challenge |
| Invalid response | Error alert with retry | Retry or fallback |
| Credential not found | Generic pre-auth message | Try another method |
| Already registered | Inline conflict in add flow | Rename existing or add another device |
| Policy required | Blocking message with exact next step | Add passkey, contact admin/support |
| Realm mismatch | Generic auth failure, mention correct portal only after safe context | Use correct portal |
| Credential revoked | Error with safe recovery path | Other method/support |
| Suspected clone | Blocking security alert | Support/runbook |
| Rate limited | Existing `RateLimitCountdown` pattern | Wait |

## 7. Components, tokens and implementation handoff

Use existing components first:

- `AuthFormCard` for login and auth interstitials.
- `CyberInput` for auth form fields.
- `Button` with `touchTarget="comfortable"` for primary auth actions.
- `RateLimitCountdown` for rate-limit state.
- `SecurityPageShell`, `SecurityStatusChip`, `SecurityEmptyState` for admin/partner security consoles.
- Existing customer `SecuritySection` card pattern for passkey management entry.
- Existing partner `ToggleField` pattern for workspace passkey preferences.

Suggested icons from `lucide-react`:

- `KeyRound` or `Fingerprint` for passkeys.
- `ShieldCheck` for protected/enforced status.
- `AlertCircle` for blocking errors.
- `Clock` for grace period/last used.
- `Pencil`, `Trash2`, `Copy`, `Plus` for management actions.

Token guidance:

- Keep existing cyberpunk tokens: `neon-cyan`, `matrix-green`, `neon-pink`, `terminal-surface`, `terminal-bg`, `grid-line`, `muted-foreground`.
- Success: matrix green. Warning/grace: amber/yellow if available, otherwise existing warning tone. Danger/revoked: neon pink/red.
- Do not introduce a new passkey-only color family.
- Do not add decorative biometric imagery or fear-based security artwork.

Density:

- Customer settings can use simple cards and short explanations.
- Admin/partner dashboards should be denser: summary metrics, tables, filters and action menus.
- Mobile login must keep the primary passkey button and password fields within reachable vertical rhythm; avoid pushing fallback links below unreachable scroll depth.

## 8. Copy inventory

Do not hardcode strings in components. Use existing namespaces and add keys near current auth/security keys.

### 8.1 Shared auth keys

Recommended key group under `Auth.login`:

| Key | EN default | RU default |
|---|---|---|
| `passkeyButton` | Sign in with passkey | Войти с passkey |
| `passkeyChecking` | Checking passkey... | Проверяем passkey... |
| `passkeyFallbackHint` | You can still use your password or another sign-in method. | Можно войти по паролю или другим способом. |
| `passkeyUnsupported` | This browser or device does not support passkeys. | Этот браузер или устройство не поддерживает passkey. |
| `passkeyCancelled` | Operation cancelled. Try again or use another sign-in method. | Операция отменена. Попробуйте еще раз или используйте другой способ входа. |
| `passkeyExpired` | Confirmation expired. Try again. | Время подтверждения истекло. Повторите попытку. |
| `passkeyGenericError` | Could not verify this passkey. | Не удалось проверить этот passkey. |
| `passkeyRequired` | A passkey is required for this access area. | Для этой области доступа требуется passkey. |

### 8.2 Customer settings keys

Recommended group under `Settings.passkeys`:

- `title`: `Passkeys` / `Passkeys`
- `description`: `Use a device unlock, biometric check, or security key to sign in without a password.` / `Используйте разблокировку устройства, биометрию или security key для входа без пароля.`
- `privacyNote`: `CyberVPN stores a public key, not your biometrics or device unlock data.` / `CyberVPN хранит публичный ключ, а не биометрию или данные разблокировки устройства.`
- `addAction`, `renameAction`, `deleteAction`, `lastUsed`, `createdAt`, `neverUsed`
- `lastRecoveryWarning`: copy must explain the next safe action, not shame the user.

### 8.3 Admin security keys

Recommended group under `AdminSecurity.passkeys`:

- Login policy: optional, recommended, required, grace period.
- Compliance metrics: total admins, with passkey, without passkey, super admins without passkey, revoked credentials.
- Step-up modal: target action, passkey action, TOTP fallback, expiry.
- Break-glass warning and runbook link text.

### 8.4 Partner keys

Recommended groups:

- `Auth.login.passkey*` for partner login.
- `PartnerSettings.security.passkeys.*` for operator management.
- `PartnerOrganization.security.passkeyPolicy.*` for workspace policy and compliance table.

RTL/localization notes:

- Do not concatenate "passkey" with role/status fragments. Use complete ICU messages.
- Long German/French/Turkish strings must wrap inside buttons and table cells.
- Arabic/Hebrew/Farsi must be verified for logical icon placement and focus order.
- Dates should use existing locale date formatting, not raw ISO in UI.

## 9. Surface-specific acceptance criteria

### 9.1 Customer frontend acceptance

- Login page shows passkey button only when backend and browser capability allow it.
- Username field supports Conditional UI with `autocomplete="username webauthn"`.
- Password, OAuth, Telegram and magic link remain available as fallback.
- Successful passkey login restores session through existing httpOnly cookie model and safe redirect.
- Post-login prompt appears only for eligible users, is dismissible and cooldown-limited.
- Settings security has passkey list/add/rename/delete.
- Deleting last viable login/recovery method is blocked with next-step guidance.
- Unsupported/cancel/expired/rate-limit states are visible and recoverable.
- Desktop and mobile screenshots are provided for login, settings empty/list, add success and delete guard.

### 9.2 Admin acceptance

- Admin login supports explicit passkey and Conditional UI.
- Passkey login does not silently bypass required TOTP policy.
- Personal passkey management requires fresh auth for delete.
- Admin security dashboard shows metrics and compliance table without raw credential data.
- Sensitive action flows launch step-up before submit or after backend `FRESH_AUTH_REQUIRED`.
- Break-glass UI is warning/runbook oriented and audit-aware.
- Error states include revoked credential, account disabled/locked, host/origin mismatch and policy/TOTP requirement.
- Desktop/mobile screenshots are provided for login, TOTP-after-passkey, personal passkeys, compliance dashboard and step-up modal.

### 9.3 Partner acceptance

- Partner login passkey requests preserve `X-Auth-Realm=partner` or host-based realm resolution.
- Realm mismatch errors are generic and do not disclose account existence in another realm.
- Operator passkey management is available in Settings/Security.
- Workspace owner/admin can set recommended/required/grace policy and role/action requirements.
- Compliance table shows member, role, passkey status, last used, grace period and exceptions.
- Step-up is required for payout, settlement, webhook/API key, team role and legal/compliance actions when policy requires it.
- Public storefront routes do not show partner operator passkey controls.
- Desktop/mobile screenshots are provided for login, operator settings, workspace policy, compliance table and storefront boundary.

## 10. Accessibility and visual quality

Required:

- Every passkey action is keyboard accessible and has visible focus state.
- Authenticator prompt launch is announced through button loading text and `aria-busy`.
- Errors use `role="alert"` or existing assertive live region pattern.
- Success and passive status use `role="status"` where appropriate.
- Dialogs have title, description, focus trap, Escape/close behavior and focus return.
- Status is text plus icon/color, never color-only.
- Reduced-motion users must not get tilt/glow-only cues. Existing motion can remain, but state changes need static cues.
- Mobile buttons meet at least existing `touchTarget="comfortable"` standards.
- Tables have responsive overflow, accessible headers and no clipped action labels.
- RTL layouts use logical spacing and verified icon direction where directional icons appear.

Visual quality bar:

- Login remains calm and scannable, not a wall of auth choices.
- Security settings show current protection posture before actions.
- Admin/partner dashboards prioritize scan density and operational confidence.
- No nested cards inside cards for new dashboard sections.
- Loading, empty and error states must be designed, not left as raw text.

## 11. QA scenarios

Quill/browser QA must cover synthetic accounts only:

1. Customer desktop: login with explicit passkey succeeds and redirects.
2. Customer mobile: passkey unsupported fallback does not block password login.
3. Customer desktop: Conditional UI appears from username field and completes login.
4. Customer settings: empty state -> add passkey -> list -> rename -> delete.
5. Customer recovery guard: delete last method blocked.
6. Admin login: passkey succeeds, then TOTP required state is shown when policy requires it.
7. Admin sensitive action: role change triggers step-up and action resumes after success.
8. Admin compliance: dashboard renders metrics/table and hides raw credential details.
9. Admin break-glass: warning path visible, no normal daily-use shortcut.
10. Partner login: passkey request carries partner realm context.
11. Partner realm mismatch: generic error copy.
12. Partner workspace policy: recommended -> required -> grace exception states.
13. Partner sensitive action: payout/API/team step-up.
14. Storefront route: no partner passkey management/action controls.
15. RTL smoke: `ar-SA`, `he-IL`, `fa-IR` login and settings do not overlap.
16. Reduced motion smoke: core state remains understandable.
17. Browser matrix: current Chrome/Edge/Safari/Firefox behavior documented, including unsupported Conditional UI where applicable.

Automated tests expected by implementation issues:

- Vitest/MSW for each app's login, capability, unsupported, cancel, expired, management CRUD and policy states.
- No raw credential/challenge/public key logging tests where feasible.
- Existing auth regressions for password, OAuth, Telegram, magic link and TOTP remain green.

## 12. Security handoff

Security-sensitive decisions must be validated by SecurityEngineer before final approve:

- Whether passkey counts as MFA for admin and under which flags.
- Fresh auth TTL and replay/action-resume model.
- Admin/partner required-mode grace period and break-glass recovery.
- Credential metadata allowed in UI, logs, telemetry and audit.
- Partner realm/audience/principal checks and storefront boundary.
- User enumeration protection for identifier-first and realm mismatch states.

This spec intentionally does not approve production enablement. Production feature flags, required mode and any break-glass operational procedure need separate security/Board decision.

## 13. Что не было сделано

- Production code was not written.
- Dependencies were not installed.
- No library versions were changed.
- No production secrets, real customer/payment data or production deploy were used.
- No direct push to `main/master`.
- No rendered UI evidence was captured because this issue is spec-only; implementation issues must provide screenshots.

# Implementation Plan — Telegram Native Login

## Purpose

This plan is derived from the documents in this folder and assumes the recommended decisions there remain valid.

For the current post-implementation tail list, use [16-post-implementation-open-items.md](16-post-implementation-open-items.md).

## Dependency Order

1. Final decisions and config freeze
2. Backend OIDC validation foundation
3. Identity and session policy implementation
4. Flutter abstraction
5. iOS native SDK integration
6. Android native SDK integration
7. Testing, observability and rollout

## Phase 0 — Final Decisions And Config

### Tasks

- [x] Freeze endpoint path convention using `/api/v1/...` in all public contracts.
- [x] Clarify BotFather `Web Login` / `Login Widget` naming.
- [x] Confirm iOS bundle IDs from the repository.
- [x] Confirm current iOS Associated Domains baseline from the repository.
- [ ] Confirm Apple Team ID per environment.
- [x] Confirm Android application IDs from the repository.
- [x] Confirm current Android deep link and App Link baseline from the repository.
- [ ] Obtain staging and production Android signing SHA-256 fingerprints.
- [x] Confirm Telegram-only storage policy for Phase 1.
- [x] Freeze current `nonce` or `state` position based on official public SDK examples.
- [x] Confirm current mobile Telegram config contract is legacy-widget-based.
- [ ] Confirm Android GitHub Packages CI access.
- [x] Freeze Phase 1 strategy as validation-only `id_token` exchange, not backend-side code exchange.

### Exit Criteria

- no critical `TBD` remains in the environment matrix
- blockers are either resolved or explicitly accepted

## Phase 1 — Backend OIDC Foundation

### Tasks

- [ ] Add Telegram OIDC settings for validation-only flow and keep Client Secret optional or reserved.
- [ ] Add OIDC discovery and JWKS client with caching.
- [ ] Add Telegram `id_token` validator.
- [ ] Add JWT header validation.
- [ ] Add JWKS unknown-`kid` refresh behavior.
- [ ] Add `POST /api/v1/mobile/auth/telegram/oidc`.
- [ ] Add response branches for success and `requires_2fa`.
- [ ] Add `POST /api/v1/mobile/auth/2fa/complete`.
- [ ] Add rate limiting.
- [ ] Add structured validation failure reasons.
- [ ] Keep legacy endpoint intact.

### Exit Criteria

- backend validates real Telegram `id_token`
- success and pending 2FA branches are implemented
- legacy endpoint still works

## Phase 2 — Identity And Device Policy

### Tasks

- [ ] Add `telegram_subject` and any approved Telegram profile fields to mobile user storage.
- [ ] Implement identity resolution by `telegram_subject`.
- [ ] Implement fallback lookup by legacy `telegram_id`.
- [ ] Add `POST /api/v1/mobile/auth/telegram/link`.
- [ ] Implement safe linking conflict handling.
- [ ] Implement the chosen Telegram-only storage strategy.
- [ ] Block password login for synthetic Telegram-only accounts until credential setup.
- [ ] Integrate device registration and session issuance.

### Exit Criteria

- no duplicate account creation for already-linked users
- device-aware refresh still works

## Phase 3 — Flutter Abstraction

### Tasks

- [ ] Create `TelegramNativeAuthClient`.
- [ ] Create method-channel bridge.
- [ ] Add provider/service orchestration for native login.
- [ ] Add backend exchange call for `/api/v1/mobile/auth/telegram/oidc`.
- [ ] Add UI states and errors.
- [ ] Add pending 2FA routing support.

### Exit Criteria

- Flutter auth layer can start native login and exchange `id_token` with backend

## Phase 4 — iOS Native SDK

### Tasks

- [ ] Add Swift Package dependency.
- [ ] Configure `TelegramLogin.configure(...)`.
- [ ] Add environment-aware redirect URI.
- [ ] Add Associated Domains capability.
- [ ] Handle callback via `.onOpenURL` or `SceneDelegate`.
- [ ] Return `idToken` to Flutter.

### Exit Criteria

- iOS real device login works end-to-end

## Phase 5 — Android Native SDK

### Tasks

- [ ] Add GitHub Packages Maven repository.
- [ ] Add GitHub Packages credentials to CI secret storage.
- [ ] Verify Android SDK artifact availability in CI.
- [ ] Add `org.telegram:login-sdk:1.0.0`.
- [ ] Configure `TelegramLogin.init(...)`.
- [ ] Add App Link intent-filter.
- [ ] Handle callback through `onNewIntent` or `onCreate`.
- [ ] Return `idToken` to Flutter.

### Exit Criteria

- Android real device login works end-to-end

## Phase 6 — Testing And QA

### Tasks

- [ ] Add backend unit tests.
- [ ] Add backend integration tests.
- [ ] Add Flutter tests.
- [ ] Run iOS manual QA checklist.
- [ ] Run Android manual QA checklist.
- [ ] Verify legacy fallback behavior.

### Exit Criteria

- all planned tests pass
- staging checklist passes

## Phase 7 — Observability And Rollout

### Tasks

- [ ] Add metrics and structured logging.
- [ ] Add dashboards and alerts.
- [ ] Enable internal rollout flag.
- [ ] Enable staging flag.
- [ ] Enable limited production rollout.
- [ ] Expand to broad production rollout.

### Exit Criteria

- rollout metrics are stable
- rollback path is verified

## Known Blockers To Resolve Early

- final product decision on `phone` scope
- final storage policy for Telegram-only users in `mobile_users`
- final `nonce` or `state` support position for the official native SDKs
- final environment-specific BotFather configuration ownership
- final platform signing artifacts for staging and production
- final migration contract from legacy `TELEGRAM_BOT_USERNAME` config to native SDK `clientId` and `redirectUri`
- Android GitHub Packages CI access and artifact availability

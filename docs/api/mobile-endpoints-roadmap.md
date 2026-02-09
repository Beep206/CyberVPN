# Mobile Endpoints Roadmap (ARCH-02.1)

> **Audit Date:** 2026-02-10
>
> **Source Files:**
> - Mobile: `cybervpn_mobile/lib/core/constants/api_constants.dart`
> - Backend Routes: `backend/src/presentation/api/v1/*/routes.py`
> - Backend Router: `backend/src/presentation/api/v1/router.py`

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Full Endpoint Inventory](#full-endpoint-inventory)
3. [Missing Endpoints (No Backend Implementation)](#missing-endpoints-no-backend-implementation)
4. [Method / Path Mismatches](#method--path-mismatches)
5. [Aligned Endpoints (Working)](#aligned-endpoints-working)
6. [Priority Classification](#priority-classification)
7. [Must-Have (MVP) API Contracts](#must-have-mvp-api-contracts)
8. [Nice-to-Have (Post-MVP) API Contracts](#nice-to-have-post-mvp-api-contracts)
9. [Implementation Roadmap](#implementation-roadmap)

---

## Executive Summary

The mobile app (`cybervpn_mobile`) defines **38 endpoint constants** in `api_constants.dart`. After auditing all backend route files, the alignment breakdown is:

| Status | Count | Percentage |
|--------|------:|------------|
| Aligned | 22 | 58% |
| Partial (method/path mismatch) | 6 | 16% |
| Missing (no backend implementation) | 7 | 18% |
| WebSocket (TBD) | 3 | 8% |

**Critical finding:** 7 endpoints the mobile app expects have zero backend implementation. An additional 6 endpoints exist but with wrong HTTP methods or different URL paths, requiring either backend or mobile changes to align.

---

## Full Endpoint Inventory

### Legend

| Symbol | Meaning |
|--------|---------|
| PASS | Endpoint exists in backend with matching path and method |
| PARTIAL | Endpoint exists but with a different HTTP method or URL path |
| MISSING | Endpoint does not exist in backend at all |
| WS | WebSocket endpoint (implementation status tracked separately) |

### Inventory Table

| # | Mobile Constant | Mobile Path | Method | Backend Status | Backend File | Notes |
|---|----------------|-------------|--------|---------------|--------------|-------|
| 1 | `login` | `/api/v1/auth/login` | POST | PASS | `auth/routes.py` | |
| 2 | `register` | `/api/v1/auth/register` | POST | PASS | `auth/registration.py` | Separate file from main auth routes |
| 3 | `refresh` | `/api/v1/auth/refresh` | POST | PASS | `auth/routes.py` | |
| 4 | `logout` | `/api/v1/auth/logout` | POST | PASS | `auth/routes.py` | |
| 5 | `biometricEnroll` | `/api/v1/mobile/auth/biometric/enroll` | POST | MISSING | -- | No biometric routes in backend |
| 6 | `biometricLogin` | `/api/v1/mobile/auth/biometric/login` | POST | MISSING | -- | No biometric routes in backend |
| 7 | `forgotPassword` | `/api/v1/auth/forgot-password` | POST | PASS | `auth/routes.py` | |
| 8 | `resetPassword` | `/api/v1/auth/reset-password` | POST | PASS | `auth/routes.py` | |
| 9 | `servers` | `/api/v1/servers` | GET | PASS | `servers/routes.py` | |
| 10 | `serverById` | `/api/v1/servers/:id` | GET | PASS | `servers/routes.py` | |
| 11 | `serverStatus` | `/api/v1/servers/:id/status` | GET | MISSING | -- | Backend has no per-server status endpoint |
| 12 | `plans` | `/api/v1/plans` | GET | PASS | `plans/routes.py` | |
| 13 | `subscriptions` | `/api/v1/subscriptions` | POST | PASS | `subscriptions/routes.py` | Admin only |
| 14 | `activeSubscription` | `/api/v1/subscriptions/active` | GET | MISSING | -- | No user-facing active subscription endpoint |
| 15 | `cancelSubscription` | `/api/v1/subscriptions/cancel` | POST | MISSING | -- | No cancellation endpoint |
| 16 | `me` | `/api/v1/auth/me` | GET | PASS | `auth/routes.py` | |
| 17 | `registerFcmToken` | `/api/v1/auth/me/fcm-token` | POST | MISSING | -- | No FCM token registration |
| 18 | `updateMe` | `/api/v1/auth/me` | PATCH | MISSING | -- | Backend only has GET and DELETE on `/auth/me` |
| 19 | `deleteAccount` | `/api/v1/auth/me` | DELETE | PASS | `auth/routes.py` | Implemented as soft-delete (FEAT-03) |
| 20 | `referralStatus` | `/api/v1/referral/status` | GET | MISSING | -- | No referral system in backend |
| 21 | `referralCode` | `/api/v1/referral/code` | GET | MISSING | -- | No referral system in backend |
| 22 | `referralStats` | `/api/v1/referral/stats` | GET | MISSING | -- | No referral system in backend |
| 23 | `referralRecent` | `/api/v1/referral/recent` | GET | MISSING | -- | No referral system in backend |
| 24 | `createPayment` | `/api/v1/payments/create` | POST | PARTIAL | `payments/routes.py` | Backend uses `/payments/crypto/invoice` |
| 25 | `paymentHistory` | `/api/v1/payments/history` | GET | PASS | `payments/routes.py` | |
| 26 | `paymentStatus` | `/api/v1/payments/:id/status` | GET | PARTIAL | `payments/routes.py` | Backend uses `/payments/crypto/invoice/:id` |
| 27 | `setup2fa` | `/api/v1/2fa/setup` | POST | PASS | `two_factor/routes.py` | |
| 28 | `verify2fa` | `/api/v1/2fa/verify` | POST | PASS | `two_factor/routes.py` | |
| 29 | `validate2fa` | `/api/v1/2fa/validate` | POST | PASS | `two_factor/routes.py` | |
| 30 | `disable2fa` | `/api/v1/2fa/disable` | POST | PARTIAL | `two_factor/routes.py` | Backend uses DELETE, not POST |
| 31 | `oauthTelegramAuth` | `/api/v1/oauth/telegram/authorize` | GET | PASS | `oauth/routes.py` | |
| 32 | `oauthTelegramCallback` | `/api/v1/oauth/telegram/callback` | GET | PARTIAL | `oauth/routes.py` | Backend uses POST, not GET |
| 33 | `telegramBotLink` | `/api/v1/auth/telegram/bot-link` | POST | PASS | `auth/routes.py` | |
| 34 | `oauthGithubAuth` | `/api/v1/oauth/github/authorize` | GET | PASS | `oauth/routes.py` | |
| 35 | `oauthGithubCallback` | `/api/v1/oauth/github/callback` | GET | PARTIAL | `oauth/routes.py` | Backend uses POST, not GET |
| 36 | `oauthUnlink` | `/api/v1/oauth/:provider` | DELETE | PASS | `oauth/routes.py` | |
| 37 | `health` | `/api/v1/monitoring/health` | GET | PASS | `monitoring/routes.py` | |
| 38 | `monitoringStats` | `/api/v1/monitoring/stats` | GET | PASS | `monitoring/routes.py` | |
| 39 | `bandwidth` | `/api/v1/monitoring/bandwidth` | GET | PASS | `monitoring/routes.py` | |
| 40 | `subscriptionConfig` | `/api/v1/subscriptions/config/:uuid` | GET | PASS | `subscriptions/routes.py` | |
| 41 | `configProfiles` | `/api/v1/config-profiles` | GET | PASS | `config_profiles/routes.py` | |
| 42 | `billing` | `/api/v1/billing` | GET | PASS | `billing/routes.py` | |
| 43 | `wsMonitoring` | `/ws/monitoring` | WS | WS | `ws/monitoring.py` | Implemented with topic auth |
| 44 | `wsTicket` | `/api/v1/ws/ticket` | POST | PASS | `ws/tickets.py` | Single-use WS ticket |
| 45 | `wsNotifications` | `/ws/notifications` | WS | WS | `ws/notifications.py` | Implemented |

### Backend-Only Endpoints (Not in Mobile Constants)

The backend also exposes endpoints the mobile app does not currently reference:

| Backend Path | Method | File | Purpose |
|--------------|--------|------|---------|
| `/api/v1/auth/logout-all` | POST | `auth/routes.py` | Revoke all sessions |
| `/api/v1/auth/verify-otp` | POST | `auth/routes.py` | Email OTP verification |
| `/api/v1/auth/resend-otp` | POST | `auth/routes.py` | Resend OTP code |
| `/api/v1/auth/magic-link` | POST | `auth/routes.py` | Request magic link |
| `/api/v1/auth/magic-link/verify` | POST | `auth/routes.py` | Verify magic link |
| `/api/v1/auth/telegram/miniapp` | POST | `auth/routes.py` | Telegram Mini App auth |
| `/api/v1/auth/telegram/generate-login-link` | POST | `auth/routes.py` | Generate bot login link |
| `/api/v1/mobile/auth/*` | various | `mobile_auth/routes.py` | Full mobile auth suite |
| `/api/v1/2fa/reauth` | POST | `two_factor/routes.py` | Password re-auth for 2FA |
| `/api/v1/2fa/status` | GET | `two_factor/routes.py` | Get 2FA status |
| `/api/v1/oauth/{provider}/login` | GET | `oauth/routes.py` | OAuth login (no auth required) |
| `/api/v1/oauth/{provider}/login/callback` | POST | `oauth/routes.py` | OAuth login callback |

---

## Missing Endpoints (No Backend Implementation)

These endpoints are defined in mobile `api_constants.dart` but have absolutely no corresponding backend route.

### 1. PATCH /api/v1/auth/me -- Update User Profile

- **Mobile constant:** `updateMe`
- **Current backend state:** `/auth/me` supports GET and DELETE only
- **Priority:** Must-have (MVP)
- **Reason:** Users need to update their display name, email, and notification preferences

### 2. POST /api/v1/auth/me/fcm-token -- FCM Token Registration

- **Mobile constant:** `registerFcmToken`
- **Current backend state:** No endpoint exists; no `fcm_tokens` table in database
- **Priority:** Must-have (MVP)
- **Reason:** Push notifications are essential for mobile; without this, no server alerts, payment confirmations, or subscription expiry warnings

### 3. GET /api/v1/subscriptions/active -- Active Subscription

- **Mobile constant:** `activeSubscription`
- **Current backend state:** Subscriptions routes are admin-only templates; no user-facing "active subscription" query
- **Priority:** Must-have (MVP)
- **Reason:** Mobile dashboard needs to display current subscription status, traffic usage, and expiry

### 4. POST /api/v1/subscriptions/cancel -- Cancel Subscription

- **Mobile constant:** `cancelSubscription`
- **Current backend state:** No cancellation endpoint
- **Priority:** Must-have (MVP)
- **Reason:** Required for App Store / Play Store compliance and user self-service

### 5. GET /api/v1/servers/:id/status -- Server Status

- **Mobile constant:** `serverStatus(id)`
- **Current backend state:** `GET /servers/:id` returns full server detail including status field
- **Priority:** Nice-to-have (post-MVP)
- **Reason:** The existing `GET /servers/:id` already returns `status`, `is_connected`, and `users_online`. A dedicated lightweight status endpoint is an optimization, not a blocker. Mobile can use the existing detail endpoint.

### 6. POST /api/v1/mobile/auth/biometric/enroll -- Biometric Enrollment

- **Mobile constant:** `biometricEnroll`
- **Current backend state:** No biometric routes exist
- **Priority:** Nice-to-have (post-MVP)
- **Reason:** Biometric auth (Face ID / fingerprint) enhances UX but is not required for core functionality. Standard JWT login works.

### 7. POST /api/v1/mobile/auth/biometric/login -- Biometric Login

- **Mobile constant:** `biometricLogin`
- **Current backend state:** No biometric routes exist
- **Priority:** Nice-to-have (post-MVP)
- **Reason:** Same as biometric enrollment -- convenience feature, not a blocker

### 8. Referral System (4 endpoints)

| Endpoint | Mobile Constant |
|----------|----------------|
| `GET /api/v1/referral/status` | `referralStatus` |
| `GET /api/v1/referral/code` | `referralCode` |
| `GET /api/v1/referral/stats` | `referralStats` |
| `GET /api/v1/referral/recent` | `referralRecent` |

- **Current backend state:** No referral module exists (no routes, no models, no migrations)
- **Priority:** Nice-to-have (post-MVP)
- **Reason:** Referral is a growth feature. The mobile UI can hide the referral tab until backend is ready.

### 9. Planned/Commented Endpoints

These are mentioned in mobile comments but have no constants defined yet:

| Endpoint | Mobile Comment | Priority |
|----------|---------------|----------|
| `/api/v1/users/usage-stats` | "Future: usage-stats endpoint" | Nice-to-have |
| `/api/v1/payments/methods` | "Future: payment-methods endpoint" | Nice-to-have |
| `/api/v1/trial/*` | "Future: trial endpoints" | Nice-to-have |

---

## Method / Path Mismatches

These endpoints exist in both mobile and backend but use different HTTP methods or URL paths. Resolution requires changing one side (recommended direction noted).

### 1. POST vs DELETE -- /api/v1/2fa/disable

| | Mobile | Backend |
|-|--------|---------|
| Method | POST | DELETE |
| Path | `/api/v1/2fa/disable` | `/api/v1/2fa/disable` |

**Recommended fix:** Update mobile to use DELETE. The backend design is semantically correct (disabling is a destructive action).

### 2. GET vs POST -- /api/v1/oauth/telegram/callback

| | Mobile | Backend |
|-|--------|---------|
| Method | GET | POST |
| Path | `/api/v1/oauth/telegram/callback` | `/api/v1/oauth/telegram/callback` |

**Recommended fix:** Update mobile to use POST. OAuth callbacks carry sensitive data in the body (CSRF state, auth hash), which should not be in query parameters.

### 3. GET vs POST -- /api/v1/oauth/github/callback

| | Mobile | Backend |
|-|--------|---------|
| Method | GET | POST |
| Path | `/api/v1/oauth/github/callback` | `/api/v1/oauth/github/callback` |

**Recommended fix:** Update mobile to use POST. Same rationale as Telegram callback.

### 4. Path mismatch -- Create Payment

| | Mobile | Backend |
|-|--------|---------|
| Path | `/api/v1/payments/create` | `/api/v1/payments/crypto/invoice` |
| Method | POST | POST |

**Recommended fix:** Either update mobile to use `/payments/crypto/invoice`, or add a backend alias route at `/payments/create` that delegates to the same use case. The mobile path is more generic (future payment methods), so adding a backend alias is preferred.

### 5. Path mismatch -- Payment Status

| | Mobile | Backend |
|-|--------|---------|
| Path | `/api/v1/payments/:id/status` | `/api/v1/payments/crypto/invoice/:id` |
| Method | GET | GET |

**Recommended fix:** Same approach as create payment -- add a backend alias or update mobile.

### 6. Mobile Auth Path Overlap

The mobile app defines auth endpoints under `/api/v1/auth/*` but the backend also has a separate mobile auth module at `/api/v1/mobile/auth/*`. The mobile app currently references the admin auth paths (`/auth/login`, `/auth/me`) rather than the mobile-specific paths (`/mobile/auth/login`, `/mobile/auth/me`).

**Recommended fix:** Mobile app should use `/api/v1/mobile/auth/*` endpoints for register, login, refresh, logout, and me. The mobile auth module has device-aware session management, subscription info in responses, and mobile-specific rate limiting that the admin auth routes lack.

---

## Aligned Endpoints (Working)

These endpoints are fully aligned between mobile and backend:

| # | Path | Method | Backend File |
|---|------|--------|--------------|
| 1 | `/api/v1/auth/login` | POST | `auth/routes.py` |
| 2 | `/api/v1/auth/register` | POST | `auth/registration.py` |
| 3 | `/api/v1/auth/refresh` | POST | `auth/routes.py` |
| 4 | `/api/v1/auth/logout` | POST | `auth/routes.py` |
| 5 | `/api/v1/auth/forgot-password` | POST | `auth/routes.py` |
| 6 | `/api/v1/auth/reset-password` | POST | `auth/routes.py` |
| 7 | `/api/v1/auth/me` | GET | `auth/routes.py` |
| 8 | `/api/v1/auth/me` | DELETE | `auth/routes.py` |
| 9 | `/api/v1/auth/telegram/bot-link` | POST | `auth/routes.py` |
| 10 | `/api/v1/servers` | GET | `servers/routes.py` |
| 11 | `/api/v1/servers/:id` | GET | `servers/routes.py` |
| 12 | `/api/v1/plans` | GET | `plans/routes.py` |
| 13 | `/api/v1/subscriptions` | POST | `subscriptions/routes.py` |
| 14 | `/api/v1/subscriptions/config/:uuid` | GET | `subscriptions/routes.py` |
| 15 | `/api/v1/payments/history` | GET | `payments/routes.py` |
| 16 | `/api/v1/2fa/setup` | POST | `two_factor/routes.py` |
| 17 | `/api/v1/2fa/verify` | POST | `two_factor/routes.py` |
| 18 | `/api/v1/2fa/validate` | POST | `two_factor/routes.py` |
| 19 | `/api/v1/oauth/telegram/authorize` | GET | `oauth/routes.py` |
| 20 | `/api/v1/oauth/github/authorize` | GET | `oauth/routes.py` |
| 21 | `/api/v1/oauth/:provider` | DELETE | `oauth/routes.py` |
| 22 | `/api/v1/monitoring/health` | GET | `monitoring/routes.py` |
| 23 | `/api/v1/monitoring/stats` | GET | `monitoring/routes.py` |
| 24 | `/api/v1/monitoring/bandwidth` | GET | `monitoring/routes.py` |
| 25 | `/api/v1/config-profiles` | GET | `config_profiles/routes.py` |
| 26 | `/api/v1/billing` | GET | `billing/routes.py` |
| 27 | `/api/v1/ws/ticket` | POST | `ws/tickets.py` |

---

## Priority Classification

### Must-Have (MVP) -- Required for mobile app launch

| # | Endpoint | Reason |
|---|----------|--------|
| 1 | `PATCH /api/v1/auth/me` | User profile updates (display name, notification prefs) |
| 2 | `POST /api/v1/auth/me/fcm-token` | Push notification token registration |
| 3 | `GET /api/v1/subscriptions/active` | Display current subscription in mobile dashboard |
| 4 | `POST /api/v1/subscriptions/cancel` | App Store / Play Store compliance |
| 5 | Fix method mismatches (3 endpoints) | 2FA disable, OAuth callbacks must work |
| 6 | Fix payment path mismatches (2 endpoints) | Create payment, check payment status |

**Estimated effort:** 3-5 dev days

### Nice-to-Have (Post-MVP) -- Can launch without these

| # | Endpoint | Reason |
|---|----------|--------|
| 7 | `GET /api/v1/servers/:id/status` | Lightweight optimization; `GET /servers/:id` already works |
| 8 | `POST /api/v1/mobile/auth/biometric/enroll` | UX enhancement; standard login works |
| 9 | `POST /api/v1/mobile/auth/biometric/login` | UX enhancement; standard login works |
| 10 | Referral system (4 endpoints) | Growth feature; can hide UI until ready |
| 11 | `/api/v1/users/usage-stats` | Analytics feature |
| 12 | `/api/v1/payments/methods` | Multi-payment-method support |
| 13 | `/api/v1/trial/*` | Trial subscription management |
| 14 | WebSocket verification (`/ws/monitoring`, `/ws/notifications`) | Already implemented, need mobile integration testing |

**Estimated effort:** 8-12 dev days (referral system is the largest item)

---

## Must-Have (MVP) API Contracts

### 1. PATCH /api/v1/auth/me -- Update User Profile

**File:** `backend/src/presentation/api/v1/auth/routes.py`

**Auth:** JWT Bearer token (current authenticated user)

**Request:**
```json
{
  "login": "new_username",          // optional, 3-50 chars, alphanumeric + underscore
  "email": "new@example.com",       // optional, valid email
  "display_name": "John Doe",       // optional, 1-100 chars
  "locale": "en-EN"                 // optional, 2-10 chars
}
```

All fields are optional. Only provided fields are updated.

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "login": "new_username",
  "email": "new@example.com",
  "role": "viewer",
  "telegram_id": null,
  "is_active": true,
  "is_email_verified": true,
  "created_at": "2026-01-15T10:30:00Z"
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 401 | Not authenticated |
| 409 | Email or login already taken |
| 422 | Validation error (invalid email format, login too short, etc.) |

**Pydantic Schema:**
```python
class UpdateProfileRequest(BaseModel):
    login: str | None = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr | None = None
    display_name: str | None = Field(None, min_length=1, max_length=100)
    locale: str | None = Field(None, max_length=10)
```

**Notes:**
- If `email` changes, set `is_email_verified=False` and trigger OTP verification flow
- `role` and `is_active` are NOT user-modifiable (admin only)
- Reuse the existing `AdminUserResponse` schema for the response

---

### 2. POST /api/v1/auth/me/fcm-token -- Register FCM Token

**File:** `backend/src/presentation/api/v1/auth/routes.py` (or new file `backend/src/presentation/api/v1/auth/fcm.py`)

**Auth:** JWT Bearer token (current authenticated user)

**Request:**
```json
{
  "fcm_token": "dGVzdC10b2tlbi1mb3ItZmlyZWJhc2U...",
  "platform": "ios",
  "device_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response (204 No Content):** Empty body

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 401 | Not authenticated |
| 422 | Validation error (missing fcm_token, invalid platform) |

**Pydantic Schema:**
```python
class RegisterFcmTokenRequest(BaseModel):
    fcm_token: str = Field(..., min_length=1, max_length=512)
    platform: Literal["ios", "android"] = Field(...)
    device_id: str = Field(..., min_length=36, max_length=36)
```

**Database requirement:** New `fcm_tokens` table:
```sql
CREATE TABLE fcm_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    fcm_token VARCHAR(512) NOT NULL,
    platform VARCHAR(10) NOT NULL,
    device_id VARCHAR(36) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(user_id, device_id)
);
```

**Notes:**
- Upsert behavior: if `(user_id, device_id)` already exists, update the token
- Old tokens for the same device should be replaced, not accumulated
- Consider a cleanup job for tokens older than 90 days

---

### 3. GET /api/v1/subscriptions/active -- Get Active Subscription

**File:** New route in `backend/src/presentation/api/v1/subscriptions/routes.py`

**Auth:** JWT Bearer token (current authenticated user)

**Request:** No body. No query parameters.

**Response (200 OK):**
```json
{
  "subscription_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "plan_name": "Premium Monthly",
  "status": "active",
  "started_at": "2026-01-01T00:00:00Z",
  "expires_at": "2026-02-01T00:00:00Z",
  "traffic_limit_bytes": 107374182400,
  "used_traffic_bytes": 21474836480,
  "auto_renew": true,
  "days_remaining": 19,
  "traffic_remaining_percent": 80.0
}
```

**Response (200 OK, no active subscription):**
```json
{
  "subscription_uuid": null,
  "plan_name": null,
  "status": "none",
  "started_at": null,
  "expires_at": null,
  "traffic_limit_bytes": null,
  "used_traffic_bytes": null,
  "auto_renew": false,
  "days_remaining": 0,
  "traffic_remaining_percent": 0.0
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 401 | Not authenticated |

**Pydantic Schema:**
```python
class ActiveSubscriptionResponse(BaseModel):
    subscription_uuid: UUID | None = None
    plan_name: str | None = None
    status: Literal["active", "expired", "trial", "cancelled", "none"] = "none"
    started_at: datetime | None = None
    expires_at: datetime | None = None
    traffic_limit_bytes: int | None = None
    used_traffic_bytes: int | None = None
    auto_renew: bool = False
    days_remaining: int = 0
    traffic_remaining_percent: float = 0.0
```

**Notes:**
- Must query Remnawave API to get the user's current subscription data
- The user is identified by their linked Remnawave user UUID
- Consider caching with a short TTL (30-60 seconds) since this is a frequent call

---

### 4. POST /api/v1/subscriptions/cancel -- Cancel Subscription

**File:** New route in `backend/src/presentation/api/v1/subscriptions/routes.py`

**Auth:** JWT Bearer token (current authenticated user)

**Request:**
```json
{
  "reason": "too_expensive",
  "feedback": "Optional user feedback text"
}
```

**Response (200 OK):**
```json
{
  "status": "cancelled",
  "effective_until": "2026-02-01T00:00:00Z",
  "message": "Subscription cancelled. You retain access until the current period ends."
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| 400 | No active subscription to cancel |
| 401 | Not authenticated |
| 422 | Validation error |

**Pydantic Schema:**
```python
class CancelSubscriptionRequest(BaseModel):
    reason: str | None = Field(None, max_length=50)
    feedback: str | None = Field(None, max_length=1000)

class CancelSubscriptionResponse(BaseModel):
    status: Literal["cancelled"] = "cancelled"
    effective_until: datetime | None = None
    message: str = "Subscription cancelled. You retain access until the current period ends."
```

**Notes:**
- Cancellation should set `auto_renew=False` rather than immediately revoking access
- The subscription remains active until `expires_at`
- Store the cancellation reason for analytics
- Must coordinate with Remnawave API to update the subscription state

---

### 5. Fix Method Mismatches

These require no new use cases, just route-level changes.

**5a. 2FA Disable -- Accept POST in addition to DELETE:**

Add to `backend/src/presentation/api/v1/two_factor/routes.py`:
```python
@router.post("/disable", response_model=TwoFactorStatusResponse)
async def disable_2fa_post(...):  # Same handler as DELETE
```

Or update mobile to use DELETE (preferred).

**5b. OAuth Callbacks -- Mobile should use POST:**

No backend change needed. Update mobile `api_constants.dart` to document that these are POST endpoints and update the Dio/HTTP client calls accordingly.

---

### 6. Fix Payment Path Mismatches

**Option A (Recommended):** Add backend alias routes:

```python
# In payments/routes.py
@router.post("/create", response_model=InvoiceResponse, status_code=201)
async def create_payment_alias(...):
    """Alias for /crypto/invoice -- mobile compatibility."""
    return await create_crypto_invoice(...)

@router.get("/{payment_id}/status", response_model=InvoiceResponse)
async def get_payment_status_alias(payment_id: str, ...):
    """Alias for /crypto/invoice/{id} -- mobile compatibility."""
    return await get_crypto_invoice(invoice_id=payment_id, ...)
```

**Option B:** Update mobile to use `/payments/crypto/invoice` and `/payments/crypto/invoice/:id`.

---

## Nice-to-Have (Post-MVP) API Contracts

### Server Status (Lightweight)

```
GET /api/v1/servers/:id/status
```

**Response:**
```json
{
  "uuid": "...",
  "status": "connected",
  "is_connected": true,
  "users_online": 42,
  "last_checked_at": "2026-02-10T12:00:00Z"
}
```

**Alternative:** Mobile uses `GET /api/v1/servers/:id` and extracts status fields.

---

### Biometric Authentication

```
POST /api/v1/mobile/auth/biometric/enroll
```
Request: `{ "device_id": "uuid" }`
Response: `{ "device_token": "opaque-token", "expires_at": "..." }`

```
POST /api/v1/mobile/auth/biometric/login
```
Request: `{ "device_token": "opaque-token", "device_id": "uuid" }`
Response: Standard `TokenResponse`

**Implementation notes:**
- Generate a long-lived, device-bound token stored in Redis or DB
- Token is refreshed on each successful biometric login
- Revoked on logout, password change, or account deletion

---

### Referral System

| Endpoint | Response Summary |
|----------|-----------------|
| `GET /referral/status` | `{ "referral_code": "ABC123", "is_active": true, "total_referrals": 5, "reward_balance": 10.00 }` |
| `GET /referral/code` | `{ "code": "ABC123", "share_url": "https://cybervpn.com/r/ABC123" }` |
| `GET /referral/stats` | `{ "total": 5, "active": 3, "expired": 2, "total_earned": 15.00 }` |
| `GET /referral/recent` | `[{ "referral_id": "...", "referred_email": "j***@example.com", "status": "active", "earned": 5.00, "created_at": "..." }]` |

**Implementation notes:**
- Requires new domain entities: `ReferralCode`, `Referral`
- New database tables: `referral_codes`, `referrals`
- Integration with subscription system for reward credits

---

### Payment Methods

```
GET /api/v1/payments/methods
```

**Response:**
```json
[
  { "id": "crypto_bot", "name": "CryptoBot", "type": "crypto", "enabled": true },
  { "id": "stripe", "name": "Card Payment", "type": "card", "enabled": false }
]
```

---

## Implementation Roadmap

### Phase 1: MVP Alignment (Week 1-2)

**Goal:** All must-have endpoints working. Mobile app can ship.

| Day | Task | Files |
|-----|------|-------|
| 1 | PATCH `/auth/me` route + use case + migration (if display_name column needed) | `auth/routes.py`, `auth/schemas.py`, new use case |
| 2 | POST `/auth/me/fcm-token` route + `fcm_tokens` table + Alembic migration | New route, new model, new repo |
| 3 | GET `/subscriptions/active` route + Remnawave integration | `subscriptions/routes.py`, new use case |
| 4 | POST `/subscriptions/cancel` route + Remnawave integration | `subscriptions/routes.py`, new use case |
| 5 | Payment alias routes (`/payments/create`, `/payments/:id/status`) | `payments/routes.py` |
| 5 | Optional: Add POST alias for `/2fa/disable` | `two_factor/routes.py` |

### Phase 2: Method/Path Alignment (Week 2)

**Goal:** Coordinate with mobile team to fix HTTP method mismatches.

| Task | Owner |
|------|-------|
| Update mobile OAuth callbacks from GET to POST | Mobile team |
| Update mobile 2FA disable from POST to DELETE (or add backend POST alias) | Backend or Mobile |
| Update mobile payment paths or confirm backend aliases work | Both |
| Migrate mobile to use `/mobile/auth/*` endpoints | Mobile team |

### Phase 3: Nice-to-Have Features (Week 3-6)

| Week | Feature | Effort |
|------|---------|--------|
| 3 | Biometric auth (enroll + login) | 2 days |
| 3 | Server status lightweight endpoint | 0.5 days |
| 4-5 | Referral system (domain, DB, 4 endpoints) | 5 days |
| 6 | Payment methods endpoint | 1 day |
| 6 | Usage stats endpoint | 1 day |
| 6 | Trial system endpoints | 2 days |

### Phase 4: WebSocket Verification (Ongoing)

- Verify `/ws/monitoring` works with mobile WebSocket client
- Verify `/ws/notifications` push delivery to mobile
- Test ticket-based WebSocket auth flow from mobile

---

## Appendix: Backend Route File Index

| Route Module | File Path | Prefix |
|--------------|-----------|--------|
| Auth | `backend/src/presentation/api/v1/auth/routes.py` | `/auth` |
| Registration | `backend/src/presentation/api/v1/auth/registration.py` | `/auth` |
| Mobile Auth | `backend/src/presentation/api/v1/mobile_auth/routes.py` | `/mobile/auth` |
| OAuth | `backend/src/presentation/api/v1/oauth/routes.py` | `/oauth` |
| Two-Factor | `backend/src/presentation/api/v1/two_factor/routes.py` | `/2fa` |
| Users | `backend/src/presentation/api/v1/users/routes.py` | `/users` |
| Servers | `backend/src/presentation/api/v1/servers/routes.py` | `/servers` |
| Subscriptions | `backend/src/presentation/api/v1/subscriptions/routes.py` | `/subscriptions` |
| Plans | `backend/src/presentation/api/v1/plans/routes.py` | `/plans` |
| Payments | `backend/src/presentation/api/v1/payments/routes.py` | `/payments` |
| Billing | `backend/src/presentation/api/v1/billing/routes.py` | `/billing` |
| Config Profiles | `backend/src/presentation/api/v1/config_profiles/routes.py` | `/config-profiles` |
| Monitoring | `backend/src/presentation/api/v1/monitoring/routes.py` | `/monitoring` |
| WS Monitoring | `backend/src/presentation/api/v1/ws/monitoring.py` | `/ws/monitoring` |
| WS Notifications | `backend/src/presentation/api/v1/ws/notifications.py` | `/ws/notifications` |
| WS Tickets | `backend/src/presentation/api/v1/ws/tickets.py` | `/ws` |

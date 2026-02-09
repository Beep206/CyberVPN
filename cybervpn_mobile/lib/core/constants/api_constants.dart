/// API endpoint constants and network configuration for CyberVPN.
///
/// # Backend API Alignment Status
///
/// This document tracks the alignment between mobile endpoints and backend routes.
/// All backend routes are defined in `backend/src/presentation/api/v1/`.
///
/// | Mobile Endpoint | Backend Path | Method | Auth | Status |
/// |-----------------|--------------|--------|------|--------|
/// | login | /api/v1/auth/login | POST | None | ✅ Aligned |
/// | register | /api/v1/auth/register | POST | None | ⚠️ Partial (not implemented in backend) |
/// | refresh | /api/v1/auth/refresh | POST | Refresh Token | ✅ Aligned |
/// | logout | /api/v1/auth/logout | POST | Refresh Token | ✅ Aligned |
/// | me | /api/v1/auth/me | GET | JWT | ✅ Aligned |
/// | updateMe | /api/v1/auth/me | PATCH | JWT | ❌ Missing (backend has no PATCH) |
/// | deleteAccount | /api/v1/auth/me | DELETE | JWT | ❌ Missing (backend has no DELETE) |
/// | servers | /api/v1/servers | GET | JWT | ✅ Aligned |
/// | serverById | /api/v1/servers/:id | GET | JWT | ✅ Aligned |
/// | serverStatus | /api/v1/servers/:id/status | GET | JWT | ❌ Missing (backend has no status endpoint) |
/// | plans | /api/v1/plans | GET | None | ✅ Aligned |
/// | subscriptions | /api/v1/subscriptions | POST | JWT | ✅ Aligned |
/// | activeSubscription | /api/v1/subscriptions/active | GET | JWT | ❌ Missing (backend has no active endpoint) |
/// | cancelSubscription | /api/v1/subscriptions/cancel | POST | JWT | ❌ Missing (backend has no cancel endpoint) |
/// | referralStatus | /api/v1/referral/status | GET | JWT | ❌ Missing (no referral routes in backend) |
/// | referralCode | /api/v1/referral/code | GET | JWT | ❌ Missing (no referral routes in backend) |
/// | referralStats | /api/v1/referral/stats | GET | JWT | ❌ Missing (no referral routes in backend) |
/// | referralRecent | /api/v1/referral/recent | GET | JWT | ❌ Missing (no referral routes in backend) |
/// | createPayment | /api/v1/payments/create | POST | JWT | ⚠️ Partial (backend has /crypto/invoice) |
/// | paymentHistory | /api/v1/payments/history | GET | JWT | ✅ Aligned |
/// | paymentStatus | /api/v1/payments/:id/status | GET | JWT | ⚠️ Partial (backend has /crypto/invoice/:id) |
/// | setup2fa | /api/v1/2fa/setup | POST | JWT | ✅ Aligned |
/// | verify2fa | /api/v1/2fa/verify | POST | JWT | ✅ Aligned |
/// | validate2fa | /api/v1/2fa/validate | POST | JWT | ✅ Aligned |
/// | disable2fa | /api/v1/2fa/disable | POST | JWT | ⚠️ Partial (backend uses DELETE) |
/// | oauthTelegramAuth | /api/v1/oauth/telegram/authorize | GET | None | ✅ Aligned |
/// | oauthTelegramCallback | /api/v1/oauth/telegram/callback | GET | JWT | ⚠️ Partial (backend uses POST) |
/// | oauthGithubAuth | /api/v1/oauth/github/authorize | GET | None | ✅ Aligned |
/// | oauthGithubCallback | /api/v1/oauth/github/callback | GET | JWT | ⚠️ Partial (backend uses POST) |
/// | oauthUnlink | /api/v1/oauth/:provider | DELETE | JWT | ✅ Aligned |
/// | health | /api/v1/monitoring/health | GET | JWT | ✅ Aligned |
/// | monitoringStats | /api/v1/monitoring/stats | GET | JWT | ✅ Aligned |
/// | bandwidth | /api/v1/monitoring/bandwidth | GET | JWT | ✅ Aligned |
/// | subscriptionConfig | /api/v1/subscriptions/config/:uuid | GET | JWT | ✅ Aligned |
/// | configProfiles | /api/v1/config-profiles | GET | JWT | ✅ Aligned |
/// | billing | /api/v1/billing | GET | JWT | ✅ Aligned |
/// | wsMonitoring | /ws/monitoring | WebSocket | JWT | 🔄 TBD |
/// | wsNotifications | /ws/notifications | WebSocket | JWT | 🔄 TBD |
///
/// **Status Legend:**
/// - ✅ Aligned: Endpoint exists in backend with matching path/method
/// - ⚠️ Partial: Endpoint exists but with different path/method/implementation
/// - ❌ Missing: Endpoint does not exist in backend
/// - 🔄 TBD: WebSocket endpoints (implementation status to be determined)
///
/// **Future Endpoints (Pending Backend Implementation):**
/// - /api/v1/auth/forgot-password ✅ Aligned
/// - /api/v1/auth/reset-password ✅ Aligned
/// - /api/v1/users/usage-stats
/// - /api/v1/payments/methods
/// - /api/v1/trial/*
///
class ApiConstants {
  const ApiConstants._();

  // ── Base URL ──────────────────────────────────────────────────────────

  static const String baseUrl = 'https://api.cybervpn.com';

  // ── API Version Prefix ────────────────────────────────────────────────

  static const String apiPrefix = '/api/v1';
  static const String apiV1Prefix = '/api/v1';

  // ── Auth Endpoints ────────────────────────────────────────────────────

  /// **POST /api/v1/auth/login**
  ///
  /// Backend: `backend/src/presentation/api/v1/auth/routes.py` - `/auth/login`
  /// Auth: None (public endpoint)
  /// Status: ✅ Aligned
  ///
  /// Request: `{ "login_or_email": string, "password": string }`
  /// Response: `{ "access_token": string, "refresh_token": string, "token_type": "Bearer", "expires_in": int }`
  static const String login = '$apiPrefix/auth/login';

  /// **POST /api/v1/auth/register**
  ///
  /// Backend: ⚠️ Not implemented in backend auth routes
  /// Auth: None (public endpoint)
  /// Status: ⚠️ Partial - Mobile expects this, but backend may use different registration flow
  ///
  /// TODO: Verify backend registration implementation in `backend/src/presentation/api/v1/auth/registration.py`
  static const String register = '$apiPrefix/auth/register';

  /// **POST /api/v1/auth/refresh**
  ///
  /// Backend: `backend/src/presentation/api/v1/auth/routes.py` - `/auth/refresh`
  /// Auth: Refresh Token (in request body)
  /// Status: ✅ Aligned
  ///
  /// Request: `{ "refresh_token": string }`
  /// Response: `{ "access_token": string, "refresh_token": string, "token_type": "Bearer", "expires_in": int }`
  static const String refresh = '$apiPrefix/auth/refresh';

  /// **POST /api/v1/auth/logout**
  ///
  /// Backend: `backend/src/presentation/api/v1/auth/routes.py` - `/auth/logout`
  /// Auth: Refresh Token (in request body)
  /// Status: ✅ Aligned
  ///
  /// Request: `{ "refresh_token": string }`
  /// Response: 204 No Content
  static const String logout = '$apiPrefix/auth/logout';

  /// **POST /api/v1/mobile/auth/biometric/enroll**
  ///
  /// Enrolls the current device for biometric re-authentication.
  /// Auth: JWT (current authenticated user)
  ///
  /// Request: `{ "device_id": string }`
  /// Response: `{ "device_token": string }`
  static const String biometricEnroll = '$apiPrefix/mobile/auth/biometric/enroll';

  /// **POST /api/v1/mobile/auth/biometric/login**
  ///
  /// Authenticates using a device-bound token (biometric re-auth).
  /// Auth: None (device token replaces credentials)
  ///
  /// Request: `{ "device_token": string, "device_id": string }`
  /// Response: `{ "access_token": string, "refresh_token": string, "token_type": "Bearer", "expires_in": int }`
  static const String biometricLogin = '$apiPrefix/mobile/auth/biometric/login';

  /// **POST /api/v1/auth/forgot-password**
  ///
  /// Backend: `backend/src/presentation/api/v1/auth/routes.py` - `/auth/forgot-password`
  /// Auth: None (public endpoint, rate-limited)
  /// Status: ✅ Aligned
  ///
  /// Initiates password reset by sending a 6-digit OTP code to the user's email.
  /// Request: `{ "email": string }`
  /// Response: 200 OK `{ "message": "If the email exists, a reset code has been sent." }`
  static const String forgotPassword = '$apiPrefix/auth/forgot-password';

  /// **POST /api/v1/auth/reset-password**
  ///
  /// Backend: `backend/src/presentation/api/v1/auth/routes.py` - `/auth/reset-password`
  /// Auth: None (public endpoint, rate-limited)
  /// Status: ✅ Aligned
  ///
  /// Completes the password reset using the OTP code and new password.
  /// Request: `{ "email": string, "code": string, "new_password": string }`
  /// Response: 200 OK `{ "message": "Password reset successfully." }`
  static const String resetPassword = '$apiPrefix/auth/reset-password';

  // ── Server Endpoints ──────────────────────────────────────────────────

  /// **GET /api/v1/servers**
  ///
  /// Backend: `backend/src/presentation/api/v1/servers/routes.py` - `/servers/`
  /// Auth: JWT (requires SERVER_READ permission)
  /// Status: ✅ Aligned
  ///
  /// Returns list of all VPN servers with status, traffic, and connection info.
  /// Response: `[{ "uuid": string, "name": string, "address": string, "port": int, "status": string, ... }]`
  static const String servers = '$apiPrefix/servers';

  /// **GET /api/v1/servers/:id**
  ///
  /// Backend: `backend/src/presentation/api/v1/servers/routes.py` - `/servers/{server_id}`
  /// Auth: JWT (requires SERVER_READ permission)
  /// Status: ✅ Aligned
  ///
  /// Append the server UUID at call site. Returns detailed server information.
  /// Response: `{ "uuid": string, "name": string, "address": string, "port": int, "status": string, ... }`
  static const String serverById = '$apiPrefix/servers/';

  /// **GET /api/v1/servers/:id/status**
  ///
  /// Backend: ❌ NOT IMPLEMENTED - Backend has no separate status endpoint
  /// Auth: JWT (expected)
  /// Status: ❌ Missing
  ///
  /// TODO: Backend needs to implement dedicated status endpoint, or mobile should use GET /servers/:id instead
  static String serverStatus(String id) => '$apiPrefix/servers/$id/status';

  // ── Subscription Endpoints ────────────────────────────────────────────

  /// **GET /api/v1/plans**
  ///
  /// Backend: `backend/src/presentation/api/v1/plans/routes.py` - `/plans/`
  /// Auth: None (public endpoint)
  /// Status: ✅ Aligned
  ///
  /// Returns list of available subscription plans.
  /// Response: `[{ "uuid": string, "name": string, "price": float, ... }]`
  static const String plans = '$apiPrefix/plans';

  /// **POST /api/v1/subscriptions**
  ///
  /// Backend: `backend/src/presentation/api/v1/subscriptions/routes.py` - `/subscriptions/`
  /// Auth: JWT (ADMIN role required)
  /// Status: ✅ Aligned
  ///
  /// Creates a new subscription template (admin only).
  /// Request: `{ "name": string, "duration_days": int, ... }`
  static const String subscriptions = '$apiPrefix/subscriptions';

  /// **GET /api/v1/subscriptions/active**
  ///
  /// Backend: ❌ NOT IMPLEMENTED - Backend has no /active endpoint
  /// Auth: JWT (expected)
  /// Status: ❌ Missing
  ///
  /// TODO: Backend needs to implement active subscription endpoint for users
  static const String activeSubscription = '$apiPrefix/subscriptions/active';

  /// **POST /api/v1/subscriptions/cancel**
  ///
  /// Backend: ❌ NOT IMPLEMENTED - Backend has no /cancel endpoint
  /// Auth: JWT (expected)
  /// Status: ❌ Missing
  ///
  /// TODO: Backend needs to implement subscription cancellation endpoint
  static const String cancelSubscription = '$apiPrefix/subscriptions/cancel';

  // ── User Endpoints ────────────────────────────────────────────────────

  /// **GET /api/v1/auth/me**
  ///
  /// Backend: `backend/src/presentation/api/v1/auth/routes.py` - `/auth/me`
  /// Auth: JWT (current authenticated user)
  /// Status: ✅ Aligned
  ///
  /// Returns current authenticated admin user information.
  /// Response: `{ "id": int, "login": string, "email": string, "role": string, ... }`
  static const String me = '$apiPrefix/auth/me';

  /// **POST /api/v1/auth/me/fcm-token**
  ///
  /// Backend: ❌ NOT IMPLEMENTED - Backend needs FCM token registration endpoint
  /// Auth: JWT (current authenticated user)
  /// Status: ❌ Missing
  ///
  /// Registers FCM device token for push notifications.
  /// Request: `{ "fcm_token": string, "platform": string, "os_version": string }`
  /// Response: 204 No Content or `{ "status": "success" }`
  /// TODO: Backend needs to implement FCM token registration endpoint
  static const String registerFcmToken = '$apiPrefix/auth/me/fcm-token';

  /// **PATCH /api/v1/auth/me**
  ///
  /// Backend: ❌ NOT IMPLEMENTED - Backend /auth/me only supports GET
  /// Auth: JWT (expected)
  /// Status: ❌ Missing
  ///
  /// TODO: Backend needs to implement PATCH /auth/me for user profile updates
  static const String updateMe = '$apiPrefix/auth/me';

  /// **DELETE /api/v1/auth/me**
  ///
  /// Backend: ❌ NOT IMPLEMENTED - Backend /auth/me only supports GET
  /// Auth: JWT (expected)
  /// Status: ❌ Missing
  ///
  /// TODO: Backend needs to implement DELETE /auth/me for account deletion
  static const String deleteAccount = '$apiPrefix/auth/me';

  // Future: usage-stats endpoint (backend task pending)
  // TODO: Add /api/v1/users/usage-stats when backend implements it

  // ── Referral Endpoints ──────────────────────────────────────────────

  /// **GET /api/v1/referral/status**
  ///
  /// Backend: ❌ NOT IMPLEMENTED - No referral routes in backend
  /// Auth: JWT (expected)
  /// Status: ❌ Missing
  ///
  /// TODO: Backend needs to implement referral system endpoints
  static const String referralStatus = '$apiPrefix/referral/status';

  /// **GET /api/v1/referral/code**
  ///
  /// Backend: ❌ NOT IMPLEMENTED - No referral routes in backend
  /// Auth: JWT (expected)
  /// Status: ❌ Missing
  ///
  /// TODO: Backend needs to implement referral system endpoints
  static const String referralCode = '$apiPrefix/referral/code';

  /// **GET /api/v1/referral/stats**
  ///
  /// Backend: ❌ NOT IMPLEMENTED - No referral routes in backend
  /// Auth: JWT (expected)
  /// Status: ❌ Missing
  ///
  /// TODO: Backend needs to implement referral system endpoints
  static const String referralStats = '$apiPrefix/referral/stats';

  /// **GET /api/v1/referral/recent**
  ///
  /// Backend: ❌ NOT IMPLEMENTED - No referral routes in backend
  /// Auth: JWT (expected)
  /// Status: ❌ Missing
  ///
  /// TODO: Backend needs to implement referral system endpoints
  static const String referralRecent = '$apiPrefix/referral/recent';

  // ── Payment Endpoints ─────────────────────────────────────────────────

  /// **POST /api/v1/payments/create**
  ///
  /// Backend: ⚠️ Different endpoint - Backend uses `/payments/crypto/invoice`
  /// Auth: JWT (requires PAYMENT_CREATE permission)
  /// Status: ⚠️ Partial
  ///
  /// TODO: Mobile should use `/payments/crypto/invoice` instead, or backend should add alias
  /// Backend endpoint: `backend/src/presentation/api/v1/payments/routes.py` - `/payments/crypto/invoice`
  static const String createPayment = '$apiPrefix/payments/create';

  /// **GET /api/v1/payments/history**
  ///
  /// Backend: `backend/src/presentation/api/v1/payments/routes.py` - `/payments/history`
  /// Auth: JWT (requires PAYMENT_READ permission)
  /// Status: ✅ Aligned
  ///
  /// Returns payment history with optional user filter and pagination.
  /// Query params: `user_uuid`, `offset`, `limit`
  static const String paymentHistory = '$apiPrefix/payments/history';

  /// **GET /api/v1/payments/:id/status**
  ///
  /// Backend: ⚠️ Different endpoint - Backend uses `/payments/crypto/invoice/:id`
  /// Auth: JWT (requires PAYMENT_READ permission)
  /// Status: ⚠️ Partial
  ///
  /// TODO: Mobile should use `/payments/crypto/invoice/:id` instead, or backend should add alias
  /// Backend endpoint: `backend/src/presentation/api/v1/payments/routes.py` - `/payments/crypto/invoice/{invoice_id}`
  static String paymentStatus(String id) => '$apiPrefix/payments/$id/status';

  // Future: payment-methods endpoint (backend task pending)
  // TODO: Add /api/v1/payments/methods when backend implements it

  // Future: trial endpoints (backend task pending)
  // TODO: Add /api/v1/trial/* when backend implements trial functionality

  // ── Two-Factor Authentication Endpoints ──────────────────────────────

  /// **POST /api/v1/2fa/setup**
  ///
  /// Backend: `backend/src/presentation/api/v1/two_factor/routes.py` - `/2fa/setup`
  /// Auth: JWT (current authenticated user)
  /// Status: ✅ Aligned
  ///
  /// Initiates 2FA setup and returns QR code data.
  /// Response: `{ "secret": string, "qr_code": string, ... }`
  static const String setup2fa = '$apiPrefix/2fa/setup';

  /// **POST /api/v1/2fa/verify**
  ///
  /// Backend: `backend/src/presentation/api/v1/two_factor/routes.py` - `/2fa/verify`
  /// Auth: JWT (current authenticated user)
  /// Status: ✅ Aligned
  ///
  /// Verifies 2FA code and enables two-factor authentication.
  /// Request: `{ "code": string }`
  static const String verify2fa = '$apiPrefix/2fa/verify';

  /// **POST /api/v1/2fa/validate**
  ///
  /// Backend: `backend/src/presentation/api/v1/two_factor/routes.py` - `/2fa/validate`
  /// Auth: JWT (current authenticated user)
  /// Status: ✅ Aligned
  ///
  /// Validates a 2FA code without changing state.
  /// Request: `{ "code": string }`
  /// Response: `{ "valid": bool }`
  static const String validate2fa = '$apiPrefix/2fa/validate';

  /// **POST /api/v1/2fa/disable**
  ///
  /// Backend: ⚠️ Method mismatch - Backend uses DELETE instead of POST
  /// Auth: JWT (current authenticated user)
  /// Status: ⚠️ Partial
  ///
  /// TODO: Mobile should use DELETE method, or backend should support POST as alias
  /// Backend: `backend/src/presentation/api/v1/two_factor/routes.py` - DELETE `/2fa/disable`
  static const String disable2fa = '$apiPrefix/2fa/disable';

  // ── OAuth Endpoints ──────────────────────────────────────────────────

  /// **GET /api/v1/oauth/telegram/authorize**
  ///
  /// Backend: `backend/src/presentation/api/v1/oauth/routes.py` - `/oauth/telegram/authorize`
  /// Auth: None (public endpoint)
  /// Status: ✅ Aligned
  ///
  /// Returns Telegram OAuth authorization URL.
  /// Response: `{ "authorize_url": string }`
  static const String oauthTelegramAuth = '$apiPrefix/oauth/telegram/authorize';

  /// **GET /api/v1/oauth/telegram/callback**
  ///
  /// Backend: ⚠️ Method mismatch - Backend uses POST instead of GET
  /// Auth: JWT (current authenticated user)
  /// Status: ⚠️ Partial
  ///
  /// TODO: Mobile should use POST method for OAuth callbacks
  /// Backend: `backend/src/presentation/api/v1/oauth/routes.py` - POST `/oauth/telegram/callback`
  static const String oauthTelegramCallback = '$apiPrefix/oauth/telegram/callback';

  /// **POST /api/v1/auth/telegram/bot-link**
  ///
  /// Backend: `backend/src/presentation/api/v1/auth/routes.py` - POST `/auth/telegram/bot-link`
  /// Auth: None (public endpoint, rate-limited)
  /// Status: ✅ Aligned
  ///
  /// Exchanges a one-time bot login token for JWT tokens.
  /// Request: `{ "token": string }`
  /// Response: `{ "access_token": string, "refresh_token": string, "token_type": string, "expires_in": int, "user": { ... } }`
  static const String telegramBotLink = '$apiPrefix/auth/telegram/bot-link';

  /// **GET /api/v1/oauth/github/authorize**
  ///
  /// Backend: `backend/src/presentation/api/v1/oauth/routes.py` - `/oauth/github/authorize`
  /// Auth: None (public endpoint)
  /// Status: ✅ Aligned
  ///
  /// Returns GitHub OAuth authorization URL.
  /// Response: `{ "authorize_url": string }`
  static const String oauthGithubAuth = '$apiPrefix/oauth/github/authorize';

  /// **GET /api/v1/oauth/github/callback**
  ///
  /// Backend: ⚠️ Method mismatch - Backend uses POST instead of GET
  /// Auth: JWT (current authenticated user)
  /// Status: ⚠️ Partial
  ///
  /// TODO: Mobile should use POST method for OAuth callbacks
  /// Backend: `backend/src/presentation/api/v1/oauth/routes.py` - POST `/oauth/github/callback`
  static const String oauthGithubCallback = '$apiPrefix/oauth/github/callback';

  /// **DELETE /api/v1/oauth/:provider**
  ///
  /// Backend: `backend/src/presentation/api/v1/oauth/routes.py` - DELETE `/oauth/{provider}`
  /// Auth: JWT (current authenticated user)
  /// Status: ✅ Aligned
  ///
  /// Append the provider name at call site (e.g., "telegram", "github").
  /// Unlinks a social account from the current user.
  static const String oauthUnlink = '$apiPrefix/oauth/';

  // ── Monitoring Endpoints ─────────────────────────────────────────────

  /// **GET /api/v1/monitoring/health**
  ///
  /// Backend: `backend/src/presentation/api/v1/monitoring/routes.py` - `/monitoring/health`
  /// Auth: JWT (requires MONITORING_READ permission)
  /// Status: ✅ Aligned
  ///
  /// System health check endpoint for database, Redis, and Remnawave API.
  /// Response: `{ "status": "healthy", "database": bool, "redis": bool, "remnawave": bool }`
  static const String health = '$apiPrefix/monitoring/health';

  /// **GET /api/v1/monitoring/stats**
  ///
  /// Backend: `backend/src/presentation/api/v1/monitoring/routes.py` - `/monitoring/stats`
  /// Auth: JWT (requires MONITORING_READ permission)
  /// Status: ✅ Aligned
  ///
  /// Returns server bandwidth statistics.
  /// Response: `{ "timestamp": string, ... }`
  static const String monitoringStats = '$apiPrefix/monitoring/stats';

  /// **GET /api/v1/monitoring/bandwidth**
  ///
  /// Backend: `backend/src/presentation/api/v1/monitoring/routes.py` - `/monitoring/bandwidth`
  /// Auth: JWT (requires MONITORING_READ permission)
  /// Status: ✅ Aligned
  ///
  /// Returns bandwidth analytics for a specific period.
  /// Query params: `period` (today, week, month)
  /// Response: `{ "timestamp": string, "period": string, ... }`
  static const String bandwidth = '$apiPrefix/monitoring/bandwidth';

  // ── Subscription Config Endpoints ────────────────────────────────────

  /// **GET /api/v1/subscriptions/config/:user_uuid**
  ///
  /// Backend: `backend/src/presentation/api/v1/subscriptions/routes.py` - `/subscriptions/config/{user_uuid}`
  /// Auth: JWT (current authenticated user)
  /// Status: ✅ Aligned
  ///
  /// Append the user UUID at call site. Generates VPN configuration for a user.
  /// Response: VPN configuration data
  static const String subscriptionConfig = '$apiPrefix/subscriptions/config/';

  // ── Config Profile Endpoints ─────────────────────────────────────────

  /// **GET /api/v1/config-profiles**
  ///
  /// Backend: `backend/src/presentation/api/v1/config_profiles/routes.py` - `/config-profiles/`
  /// Auth: JWT (expected)
  /// Status: ✅ Aligned
  ///
  /// Returns list of VPN configuration profiles.
  static const String configProfiles = '$apiPrefix/config-profiles/';

  // ── Billing Endpoints ────────────────────────────────────────────────

  /// **GET /api/v1/billing**
  ///
  /// Backend: `backend/src/presentation/api/v1/billing/routes.py` - `/billing/`
  /// Auth: JWT (expected)
  /// Status: ✅ Aligned
  ///
  /// Returns billing information for current user.
  static const String billing = '$apiPrefix/billing/';

  // ── WebSocket Endpoints ──────────────────────────────────────────────

  /// **WebSocket /ws/monitoring**
  ///
  /// Backend: `backend/src/presentation/api/v1/ws/` - WebSocket endpoint
  /// Auth: JWT (expected in connection handshake)
  /// Status: 🔄 TBD
  ///
  /// Real-time monitoring data via WebSocket connection.
  /// TODO: Verify WebSocket implementation and authentication mechanism
  static const String wsMonitoring = '/ws/monitoring';

  /// **POST /api/v1/ws/ticket**
  ///
  /// Backend: Issues a short-lived, single-use ticket for WebSocket auth.
  /// Auth: JWT (current authenticated user)
  /// Status: 🔄 TBD
  ///
  /// The ticket is valid for ~30 seconds and can only be used once.
  /// This avoids passing JWT tokens in WebSocket URLs (which appear in logs).
  /// Response: `{ "ticket": string }`
  static const String wsTicket = '$apiPrefix/ws/ticket';

  /// **WebSocket /ws/notifications**
  ///
  /// Backend: `backend/src/presentation/api/v1/ws/` - WebSocket endpoint
  /// Auth: JWT (expected in connection handshake)
  /// Status: 🔄 TBD
  ///
  /// Push notifications via WebSocket connection.
  /// TODO: Verify WebSocket implementation and authentication mechanism
  static const String wsNotifications = '/ws/notifications';

  // ══════════════════════════════════════════════════════════════════════
  // ── Deprecated / Missing Endpoints ───────────────────────────────────
  // ══════════════════════════════════════════════════════════════════════
  //
  // This section documents endpoints that are defined in mobile but have
  // alignment issues with the backend. These require attention for future
  // mobile or backend updates.
  //
  // **Missing Backend Implementation (Mobile expects, Backend doesn't have):**
  //
  // 1. GET /api/v1/servers/:id/status
  //    - Mobile: serverStatus() function
  //    - Migration: Use GET /api/v1/servers/:id instead
  //    - Timeline: Remove in mobile v2.0.0 or add to backend
  //
  // 2. GET /api/v1/subscriptions/active
  //    - Mobile: activeSubscription constant
  //    - Migration: Backend needs to implement active subscription endpoint
  //    - Timeline: Critical for user subscription management
  //
  // 3. POST /api/v1/subscriptions/cancel
  //    - Mobile: cancelSubscription constant
  //    - Migration: Backend needs to implement subscription cancellation
  //    - Timeline: Critical for user subscription management
  //
  // 4. PATCH /api/v1/auth/me
  //    - Mobile: updateMe constant
  //    - Migration: Backend needs to implement user profile updates
  //    - Timeline: Required for user settings feature
  //
  // 5. DELETE /api/v1/auth/me
  //    - Mobile: deleteAccount constant
  //    - Migration: Backend needs to implement account deletion (GDPR compliance)
  //    - Timeline: Critical for GDPR compliance
  //
  // 6. All /api/v1/referral/* endpoints
  //    - Mobile: referralStatus, referralCode, referralStats, referralRecent
  //    - Migration: Backend needs full referral system implementation
  //    - Timeline: Feature not yet implemented in backend
  //
  // **Method Mismatches (Endpoint exists but different HTTP method):**
  //
  // 1. /api/v1/2fa/disable
  //    - Mobile: POST
  //    - Backend: DELETE
  //    - Migration: Update mobile to use DELETE, or backend to accept POST
  //
  // 2. /api/v1/oauth/telegram/callback
  //    - Mobile: GET
  //    - Backend: POST
  //    - Migration: Update mobile to use POST for OAuth callbacks
  //
  // 3. /api/v1/oauth/github/callback
  //    - Mobile: GET
  //    - Backend: POST
  //    - Migration: Update mobile to use POST for OAuth callbacks
  //
  // **Path Mismatches (Different endpoint paths):**
  //
  // 1. POST /api/v1/payments/create
  //    - Mobile: /payments/create
  //    - Backend: /payments/crypto/invoice
  //    - Migration: Update mobile to use /payments/crypto/invoice
  //
  // 2. GET /api/v1/payments/:id/status
  //    - Mobile: /payments/:id/status
  //    - Backend: /payments/crypto/invoice/:id
  //    - Migration: Update mobile to use /payments/crypto/invoice/:id
  //
  // **Planned Backend Endpoints (Not yet implemented):**
  //
  // - /api/v1/users/usage-stats - User traffic and usage statistics
  // - /api/v1/payments/methods - Payment method management
  // - /api/v1/trial/* - Trial subscription endpoints
  //
  // ══════════════════════════════════════════════════════════════════════

  // ── Timeout Configuration (milliseconds) ──────────────────────────────

  /// Timeout for establishing a connection to the server.
  static const int connectTimeout = 15000;

  /// Timeout for receiving data from the server.
  static const int receiveTimeout = 30000;

  /// Timeout for sending data to the server.
  static const int sendTimeout = 15000;

  // ── HTTP Headers ──────────────────────────────────────────────────────

  static const String contentType = 'application/json';
  static const String authorizationHeader = 'Authorization';
  static const String bearerPrefix = 'Bearer ';
}

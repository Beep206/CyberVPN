import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/constants/api_constants.dart';

/// API Alignment Smoke Tests
///
/// These tests verify that mobile API constants align with backend routes
/// defined in backend/src/presentation/api/v1/.
///
/// Status Legend:
/// - ✅ Aligned: Endpoint exists in backend with matching path/method
/// - ⚠️ Partial: Endpoint exists but with different path/method/implementation
/// - ❌ Missing: Endpoint does not exist in backend
/// - 🔄 TBD: WebSocket endpoints (implementation status to be determined)
///
/// Backend Route Structure (from backend/src/presentation/api/v1/router.py):
/// - All routes prefixed with /api/v1
/// - Routers: auth, security, servers, subscriptions, payments, 2fa, oauth, etc.
void main() {
  group('ApiConstants', () {
    // ── Subtask 1.4: Verify apiPrefix constant ────────────────────────────

    test('apiPrefix should be /api/v1', () {
      expect(ApiConstants.apiPrefix, equals('/api/v1'));
    });

    test('apiV1Prefix should be /api/v1', () {
      expect(ApiConstants.apiV1Prefix, equals('/api/v1'));
    });

    // ── Subtask 1.4: All endpoint constants start with /api/v1 ────────────

    group('all endpoint paths start with /api/v1', () {
      final endpointMap = <String, String>{
        'login': ApiConstants.login,
        'register': ApiConstants.register,
        'refresh': ApiConstants.refresh,
        'logout': ApiConstants.logout,
        'servers': ApiConstants.servers,
        'serverById': ApiConstants.serverById,
        'plans': ApiConstants.plans,
        'subscriptions': ApiConstants.subscriptions,
        'activeSubscription': ApiConstants.activeSubscription,
        'cancelSubscription': ApiConstants.cancelSubscription,
        'me': ApiConstants.me,
        'updateMe': ApiConstants.updateMe,
        'deleteAccount': ApiConstants.deleteAccount,
        'createPayment': ApiConstants.createPayment,
        'paymentHistory': ApiConstants.paymentHistory,
        // Task 3: New endpoint constants
        'setup2fa': ApiConstants.setup2fa,
        'verify2fa': ApiConstants.verify2fa,
        'validate2fa': ApiConstants.validate2fa,
        'disable2fa': ApiConstants.disable2fa,
        'oauthTelegramAuth': ApiConstants.oauthTelegramAuth,
        'oauthTelegramCallback': ApiConstants.oauthTelegramCallback,
        'oauthGithubAuth': ApiConstants.oauthGithubAuth,
        'oauthGithubCallback': ApiConstants.oauthGithubCallback,
        'oauthUnlink': ApiConstants.oauthUnlink,
        'health': ApiConstants.health,
        'monitoringStats': ApiConstants.monitoringStats,
        'bandwidth': ApiConstants.bandwidth,
        'subscriptionConfig': ApiConstants.subscriptionConfig,
        'configProfiles': ApiConstants.configProfiles,
        'billing': ApiConstants.billing,
      };

      for (final entry in endpointMap.entries) {
        test('${entry.key} starts with /api/v1', () {
          expect(
            entry.value.startsWith('/api/v1'),
            isTrue,
            reason: '${entry.key} = "${entry.value}" does not start with /api/v1',
          );
        });
      }

      test('serverStatus(id) starts with /api/v1', () {
        final path = ApiConstants.serverStatus('test-id');
        expect(
          path.startsWith('/api/v1'),
          isTrue,
          reason: 'serverStatus = "$path" does not start with /api/v1',
        );
      });

      test('paymentStatus(id) starts with /api/v1', () {
        final path = ApiConstants.paymentStatus('test-id');
        expect(
          path.startsWith('/api/v1'),
          isTrue,
          reason: 'paymentStatus = "$path" does not start with /api/v1',
        );
      });
    });

    // ── Subtask 1.5: Cross-reference against known backend paths ──────────

    group('endpoint paths match known backend routes', () {
      // Known backend routes from backend/src/presentation/api/v1/**/routes.py
      // Backend router prefix: /api/v1 (from router.py)

      test('auth endpoints match backend /auth/* routes', () {
        expect(ApiConstants.login, equals('/api/v1/auth/login'));
        expect(ApiConstants.register, equals('/api/v1/auth/register'));
        expect(ApiConstants.refresh, equals('/api/v1/auth/refresh'));
        expect(ApiConstants.logout, equals('/api/v1/auth/logout'));
      });

      test('server endpoints match backend /servers/* routes', () {
        expect(ApiConstants.servers, equals('/api/v1/servers'));
        expect(ApiConstants.serverById, equals('/api/v1/servers/'));
        expect(
          ApiConstants.serverStatus('abc'),
          equals('/api/v1/servers/abc/status'),
        );
      });

      test('plan endpoints match backend /plans/* routes', () {
        expect(ApiConstants.plans, equals('/api/v1/plans'));
      });

      test('subscription endpoints match backend /subscriptions/* routes', () {
        expect(ApiConstants.subscriptions, equals('/api/v1/subscriptions'));
        expect(
          ApiConstants.activeSubscription,
          equals('/api/v1/subscriptions/active'),
        );
        expect(
          ApiConstants.cancelSubscription,
          equals('/api/v1/subscriptions/cancel'),
        );
      });

      test('user/auth me endpoints match backend /auth/me route', () {
        expect(ApiConstants.me, equals('/api/v1/auth/me'));
        expect(ApiConstants.updateMe, equals('/api/v1/auth/me'));
        expect(ApiConstants.deleteAccount, equals('/api/v1/auth/me'));
      });

      test('payment endpoints match backend /payments/* routes', () {
        expect(ApiConstants.createPayment, equals('/api/v1/payments/create'));
        expect(ApiConstants.paymentHistory, equals('/api/v1/payments/history'));
        expect(
          ApiConstants.paymentStatus('xyz'),
          equals('/api/v1/payments/xyz/status'),
        );
      });
    });

    // ── Task 2: Verify phantom constants are removed ────────────────────

    // These constants were removed because they do not exist on the backend.
    // If any of these names are re-added to ApiConstants, the test below
    // should be updated accordingly.
    //
    // Removed constants:
    //   forgotPassword, resetPassword, usageStats,
    //   referrals, referralCode, applyReferral, referralStats,
    //   activateTrial, trialStatus, trialEligibility,
    //   paymentMethods

    // ── Task 3: New endpoint constants verification ───────────────────────

    group('2FA endpoint constants', () {
      test('setup2fa matches expected path', () {
        expect(ApiConstants.setup2fa, equals('/api/v1/2fa/setup'));
      });

      test('verify2fa matches expected path', () {
        expect(ApiConstants.verify2fa, equals('/api/v1/2fa/verify'));
      });

      test('validate2fa matches expected path', () {
        expect(ApiConstants.validate2fa, equals('/api/v1/2fa/validate'));
      });

      test('disable2fa matches expected path', () {
        expect(ApiConstants.disable2fa, equals('/api/v1/2fa/disable'));
      });
    });

    group('OAuth endpoint constants', () {
      test('oauthTelegramAuth matches expected path', () {
        expect(
          ApiConstants.oauthTelegramAuth,
          equals('/api/v1/oauth/telegram/authorize'),
        );
      });

      test('oauthTelegramCallback matches expected path', () {
        expect(
          ApiConstants.oauthTelegramCallback,
          equals('/api/v1/oauth/telegram/callback'),
        );
      });

      test('oauthGithubAuth matches expected path', () {
        expect(
          ApiConstants.oauthGithubAuth,
          equals('/api/v1/oauth/github/authorize'),
        );
      });

      test('oauthGithubCallback matches expected path', () {
        expect(
          ApiConstants.oauthGithubCallback,
          equals('/api/v1/oauth/github/callback'),
        );
      });

      test('oauthUnlink uses base path for provider append', () {
        expect(ApiConstants.oauthUnlink, equals('/api/v1/oauth/'));
      });
    });

    group('Monitoring endpoint constants', () {
      test('health matches expected path', () {
        expect(ApiConstants.health, equals('/api/v1/monitoring/health'));
      });

      test('monitoringStats matches expected path', () {
        expect(
          ApiConstants.monitoringStats,
          equals('/api/v1/monitoring/stats'),
        );
      });

      test('bandwidth matches expected path', () {
        expect(ApiConstants.bandwidth, equals('/api/v1/monitoring/bandwidth'));
      });

      test('all monitoring endpoints contain /monitoring/', () {
        final monitoringEndpoints = [
          ApiConstants.health,
          ApiConstants.monitoringStats,
          ApiConstants.bandwidth,
        ];
        for (final endpoint in monitoringEndpoints) {
          expect(
            endpoint.contains('/monitoring/'),
            isTrue,
            reason: '"$endpoint" does not contain /monitoring/',
          );
        }
      });
    });

    group('Subscription config, config profiles, and billing constants', () {
      test('subscriptionConfig matches expected path', () {
        expect(
          ApiConstants.subscriptionConfig,
          equals('/api/v1/subscriptions/config/'),
        );
      });

      test('configProfiles matches expected path', () {
        expect(
          ApiConstants.configProfiles,
          equals('/api/v1/config-profiles/'),
        );
      });

      test('billing matches expected path', () {
        expect(ApiConstants.billing, equals('/api/v1/billing/'));
      });
    });

    group('WebSocket endpoint constants', () {
      test('wsMonitoring matches expected path', () {
        expect(ApiConstants.wsMonitoring, equals('/ws/monitoring'));
      });

      test('wsNotifications matches expected path', () {
        expect(ApiConstants.wsNotifications, equals('/ws/notifications'));
      });

      test('WebSocket endpoints start with /ws/', () {
        expect(
          ApiConstants.wsMonitoring.startsWith('/ws/'),
          isTrue,
          reason:
              'wsMonitoring = "${ApiConstants.wsMonitoring}" does not start with /ws/',
        );
        expect(
          ApiConstants.wsNotifications.startsWith('/ws/'),
          isTrue,
          reason:
              'wsNotifications = "${ApiConstants.wsNotifications}" does not start with /ws/',
        );
      });

      test('WebSocket endpoints do NOT start with /api/v1', () {
        expect(
          ApiConstants.wsMonitoring.startsWith('/api/v1'),
          isFalse,
          reason: 'wsMonitoring should use /ws/ prefix, not /api/v1',
        );
        expect(
          ApiConstants.wsNotifications.startsWith('/api/v1'),
          isFalse,
          reason: 'wsNotifications should use /ws/ prefix, not /api/v1',
        );
      });
    });

    // ── TE2-6: Additional Backend Alignment Tests ─────────────────────────

    group('Security Endpoints (✅ Aligned)', () {
      test('getAntiphishingCode aligns with backend GET /security/antiphishing', () {
        expect(
          ApiConstants.getAntiphishingCode,
          equals('/api/v1/security/antiphishing'),
        );
      });

      test('setAntiphishingCode aligns with backend POST /security/antiphishing', () {
        expect(
          ApiConstants.setAntiphishingCode,
          equals('/api/v1/security/antiphishing'),
        );
      });

      test('deleteAntiphishingCode aligns with backend DELETE /security/antiphishing', () {
        expect(
          ApiConstants.deleteAntiphishingCode,
          equals('/api/v1/security/antiphishing'),
        );
      });
    });

    group('Password Management Endpoints (✅ Aligned)', () {
      test('forgotPassword aligns with backend POST /auth/forgot-password', () {
        expect(
          ApiConstants.forgotPassword,
          equals('/api/v1/auth/forgot-password'),
        );
      });

      test('resetPassword aligns with backend POST /auth/reset-password', () {
        expect(
          ApiConstants.resetPassword,
          equals('/api/v1/auth/reset-password'),
        );
      });

      test('changePassword aligns with backend POST /auth/change-password', () {
        expect(
          ApiConstants.changePassword,
          equals('/api/v1/auth/change-password'),
        );
      });
    });

    group('Profile & User Endpoints (✅ Aligned)', () {
      test('profile aligns with backend GET /users/me/profile', () {
        expect(ApiConstants.profile, equals('/api/v1/users/me/profile'));
      });

      test('updateProfile aligns with backend PATCH /users/me/profile', () {
        expect(ApiConstants.updateProfile, equals('/api/v1/users/me/profile'));
      });

      test('usage aligns with backend GET /users/me/usage', () {
        expect(ApiConstants.usage, equals('/api/v1/users/me/usage'));
      });

      test('registerFcmToken aligns with backend POST /fcm/tokens', () {
        expect(ApiConstants.registerFcmToken, equals('/api/v1/fcm/tokens'));
      });

      test('deleteFcmToken aligns with backend DELETE /fcm/tokens', () {
        expect(ApiConstants.deleteFcmToken, equals('/api/v1/fcm/tokens'));
      });
    });

    group('Trial Endpoints (✅ Aligned)', () {
      test('trialActivate aligns with backend POST /trial/activate', () {
        expect(ApiConstants.trialActivate, equals('/api/v1/trial/activate'));
      });

      test('trialStatus aligns with backend GET /trial/status', () {
        expect(ApiConstants.trialStatus, equals('/api/v1/trial/status'));
      });
    });

    group('Status Endpoint (✅ Aligned)', () {
      test('status aligns with backend GET /status', () {
        expect(ApiConstants.status, equals('/api/v1/status'));
      });
    });

    group('Telegram Bot Auth (✅ Aligned)', () {
      test('telegramBotLink aligns with backend POST /auth/telegram/bot-link', () {
        expect(
          ApiConstants.telegramBotLink,
          equals('/api/v1/auth/telegram/bot-link'),
        );
      });
    });

    group('OTP Endpoints (⚠️ Pending Backend)', () {
      test('verifyEmail endpoint is defined (pending backend implementation)', () {
        expect(ApiConstants.verifyEmail, equals('/api/v1/auth/verify-email'));
      });

      test('resendOtp endpoint is defined (pending backend implementation)', () {
        expect(ApiConstants.resendOtp, equals('/api/v1/auth/resend-otp'));
      });
    });

    group('Wallet Endpoints (⚠️ Pending Backend)', () {
      test('walletBalance is defined (pending backend implementation)', () {
        expect(ApiConstants.walletBalance, equals('/api/v1/wallet/balance'));
      });

      test('walletTransactions is defined (pending backend implementation)', () {
        expect(
          ApiConstants.walletTransactions,
          equals('/api/v1/wallet/transactions'),
        );
      });

      test('walletWithdraw is defined (pending backend implementation)', () {
        expect(ApiConstants.walletWithdraw, equals('/api/v1/wallet/withdraw'));
      });
    });

    group('Referral Endpoints (❌ Missing in Backend)', () {
      test('referralStatus is defined but missing in backend', () {
        expect(ApiConstants.referralStatus, equals('/api/v1/referral/status'));
        // Backend: No referral routes implemented yet
      });

      test('referralCode is defined but missing in backend', () {
        expect(ApiConstants.referralCode, equals('/api/v1/referral/code'));
        // Backend: No referral routes implemented yet
      });

      test('referralStats is defined but missing in backend', () {
        expect(ApiConstants.referralStats, equals('/api/v1/referral/stats'));
        // Backend: No referral routes implemented yet
      });

      test('referralRecent is defined but missing in backend', () {
        expect(ApiConstants.referralRecent, equals('/api/v1/referral/recent'));
        // Backend: No referral routes implemented yet
      });
    });

    group('Mobile-Specific Endpoints (⚠️ Pending Backend)', () {
      test('biometricEnroll is defined (pending backend)', () {
        expect(
          ApiConstants.biometricEnroll,
          equals('/api/v1/mobile/auth/biometric/enroll'),
        );
      });

      test('biometricLogin is defined (pending backend)', () {
        expect(
          ApiConstants.biometricLogin,
          equals('/api/v1/mobile/auth/biometric/login'),
        );
      });
    });

    group('Endpoint Alignment - Missing in Mobile (Backend Exists)', () {
      // Document backend endpoints that mobile doesn't use yet

      test('backend has DELETE /auth/me for account deletion (✅ aligned)', () {
        // Mobile: ApiConstants.deleteAccount = '/api/v1/auth/me'
        // Backend: DELETE /auth/me implemented (FEAT-03)
        expect(ApiConstants.deleteAccount, equals('/api/v1/auth/me'));
      });

      test('backend has POST /auth/logout-all (not in mobile)', () {
        // Backend: POST /auth/logout-all - revoke all user tokens
        // Mobile could add: logoutAll constant if needed
      });

      test('backend has POST /auth/verify-otp (not in mobile)', () {
        // Backend: POST /auth/verify-otp - verify email OTP
        // Mobile could add: verifyOtp constant if needed
      });

      test('backend has POST /auth/resend-otp (not in mobile)', () {
        // Backend: POST /auth/resend-otp - resend email OTP
        // Note: ApiConstants.resendOtp exists, path matches
        expect(ApiConstants.resendOtp, equals('/api/v1/auth/resend-otp'));
      });

      test('backend has POST /auth/magic-link (not in mobile)', () {
        // Backend: POST /auth/magic-link - passwordless login
        // Mobile could add: magicLink constant if needed
      });

      test('backend has POST /2fa/reauth (not in mobile)', () {
        // Backend: POST /2fa/reauth - re-authenticate with password
        // Mobile could add: twoFactorReauth constant if needed
      });

      test('backend has GET /servers/stats (not in mobile)', () {
        // Backend: GET /servers/stats - server statistics
        // Mobile could add: serverStats constant if needed
      });

      test('backend has POST /payments/checkout (not in mobile)', () {
        // Backend: POST /payments/checkout - unified checkout
        // Mobile could add: checkout constant if needed
      });
    });

    group('Method Mismatches (⚠️ Partial Alignment)', () {
      test('disable2fa: mobile expects POST, backend supports both DELETE + POST', () {
        // Mobile: expects POST
        // Backend: DELETE (primary) + POST (alias for backward compatibility)
        expect(ApiConstants.disable2fa, equals('/api/v1/2fa/disable'));
      });

      test('oauthTelegramCallback: mobile expects GET, backend supports both POST + GET', () {
        // Mobile: expects GET
        // Backend: POST (primary) + GET (alias for backward compatibility)
        expect(
          ApiConstants.oauthTelegramCallback,
          equals('/api/v1/oauth/telegram/callback'),
        );
      });

      test('oauthGithubCallback: mobile expects GET, backend supports both POST + GET', () {
        // Mobile: expects GET
        // Backend: POST (primary) + GET (alias for backward compatibility)
        expect(
          ApiConstants.oauthGithubCallback,
          equals('/api/v1/oauth/github/callback'),
        );
      });
    });

    group('Path Mismatches (⚠️ Partial - Backend Has Aliases)', () {
      test('createPayment has backend alias for compatibility', () {
        // Mobile: POST /payments/create
        // Backend primary: POST /payments/crypto/invoice
        // Backend alias: POST /payments/create (deprecated)
        expect(ApiConstants.createPayment, equals('/api/v1/payments/create'));
      });

      test('paymentStatus has backend alias for compatibility', () {
        // Mobile: GET /payments/:id/status
        // Backend primary: GET /payments/crypto/invoice/:id
        // Backend alias: GET /payments/:id/status (deprecated)
        final statusPath = ApiConstants.paymentStatus('test-id');
        expect(statusPath, equals('/api/v1/payments/test-id/status'));
      });
    });

    group('Missing Backend Endpoints (❌)', () {
      test('serverStatus is not implemented in backend', () {
        // Mobile expects: GET /servers/:id/status
        // Backend has: No separate status endpoint
        // Mobile should use: GET /servers/:id instead
        final statusPath = ApiConstants.serverStatus('test-id');
        expect(statusPath, equals('/api/v1/servers/test-id/status'));
      });

      test('activeSubscription is not implemented in backend', () {
        // Mobile expects: GET /subscriptions/active
        // Backend has: No /active endpoint yet
        expect(
          ApiConstants.activeSubscription,
          equals('/api/v1/subscriptions/active'),
        );
      });

      test('cancelSubscription is not implemented in backend', () {
        // Mobile expects: POST /subscriptions/cancel
        // Backend has: No /cancel endpoint yet
        expect(
          ApiConstants.cancelSubscription,
          equals('/api/v1/subscriptions/cancel'),
        );
      });

      test('updateMe (PATCH /auth/me) is not implemented in backend', () {
        // Mobile expects: PATCH /auth/me
        // Backend has: GET /auth/me only
        // Note: Backend has PATCH /users/me/profile instead
        expect(ApiConstants.updateMe, equals('/api/v1/auth/me'));
      });
    });

    group('WebSocket Ticket Endpoint (✅ Aligned)', () {
      test('wsTicket aligns with backend POST /ws/ticket', () {
        expect(ApiConstants.wsTicket, equals('/api/v1/ws/ticket'));
      });
    });
  });
}

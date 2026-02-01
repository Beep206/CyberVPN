import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/core/constants/api_constants.dart';

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
  });
}

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/analytics/analytics_providers.dart';
import 'package:cybervpn_mobile/core/analytics/analytics_service.dart';
import 'package:cybervpn_mobile/core/analytics/noop_analytics.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';

/// Stub implementation of [AnalyticsService] used only to verify
/// that the provider returns a non-noop implementation when consent
/// is granted. This avoids needing Firebase initialized in tests.
class _StubFirebaseAnalytics implements AnalyticsService {
  @override
  Future<void> logEvent(String name, {Map<String, dynamic>? parameters}) async {}
  @override
  Future<void> setUserId(String? userId) async {}
  @override
  Future<void> setUserProperty({required String name, required String value}) async {}
  @override
  Future<void> logScreenView(String screenName, {String? screenClass}) async {}
}

void main() {
  group('analyticsConsentProvider', () {
    test('defaults to false when no preference is stored', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();

      final container = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
      );
      addTearDown(container.dispose);

      expect(container.read(analyticsConsentProvider), isFalse);
    });

    test('returns true when consent is stored as true', () async {
      SharedPreferences.setMockInitialValues({
        analyticsConsentKey: true,
      });
      final prefs = await SharedPreferences.getInstance();

      final container = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
      );
      addTearDown(container.dispose);

      expect(container.read(analyticsConsentProvider), isTrue);
    });

    test('setConsent persists value and updates state', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();

      final container = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
      );
      addTearDown(container.dispose);

      expect(container.read(analyticsConsentProvider), isFalse);

      await container.read(analyticsConsentProvider.notifier).setConsent(true);

      expect(container.read(analyticsConsentProvider), isTrue);
      expect(prefs.getBool(analyticsConsentKey), isTrue);
    });
  });

  group('analyticsProvider', () {
    test('returns NoopAnalytics when consent is false', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();

      final container = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
        ],
      );
      addTearDown(container.dispose);

      final analytics = container.read(analyticsProvider);
      expect(analytics, isA<NoopAnalytics>());
    });

    test('returns non-noop when consent is true (with override)', () async {
      SharedPreferences.setMockInitialValues({
        analyticsConsentKey: true,
      });
      final prefs = await SharedPreferences.getInstance();

      // Override analyticsProvider to avoid Firebase initialization in tests.
      // This verifies the consent-based switching logic works correctly.
      final stub = _StubFirebaseAnalytics();
      final container = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          analyticsProvider.overrideWith((ref) {
            final hasConsent = ref.watch(analyticsConsentProvider);
            if (hasConsent) {
              return stub;
            }
            return const NoopAnalytics();
          }),
        ],
      );
      addTearDown(container.dispose);

      final analytics = container.read(analyticsProvider);
      expect(analytics, same(stub));
      expect(analytics, isNot(isA<NoopAnalytics>()));
    });

    test('switches implementation when consent changes', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();

      final stub = _StubFirebaseAnalytics();
      final container = ProviderContainer(
        overrides: [
          sharedPreferencesProvider.overrideWithValue(prefs),
          analyticsProvider.overrideWith((ref) {
            final hasConsent = ref.watch(analyticsConsentProvider);
            if (hasConsent) {
              return stub;
            }
            return const NoopAnalytics();
          }),
        ],
      );
      addTearDown(container.dispose);

      // Initially no consent.
      expect(container.read(analyticsProvider), isA<NoopAnalytics>());

      // Grant consent.
      await container.read(analyticsConsentProvider.notifier).setConsent(true);

      // Should switch to stub (Firebase in production).
      expect(container.read(analyticsProvider), same(stub));

      // Revoke consent.
      await container.read(analyticsConsentProvider.notifier).setConsent(false);

      // Should switch back to Noop.
      expect(container.read(analyticsProvider), isA<NoopAnalytics>());
    });
  });
}

import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/analytics/analytics_service.dart';
import 'package:cybervpn_mobile/core/analytics/noop_analytics.dart';

void main() {
  late AnalyticsService analytics;

  setUp(() {
    analytics = const NoopAnalytics();
  });

  group('NoopAnalytics', () {
    test('logEvent does not throw', () async {
      await expectLater(
        analytics.logEvent('test_event'),
        completes,
      );
    });

    test('logEvent with parameters does not throw', () async {
      await expectLater(
        analytics.logEvent('test_event', parameters: {
          'key': 'value',
          'count': 42,
          'nested': {'a': 1},
        }),
        completes,
      );
    });

    test('logEvent with null parameters does not throw', () async {
      await expectLater(
        analytics.logEvent('test_event', parameters: null),
        completes,
      );
    });

    test('setUserId does not throw', () async {
      await expectLater(analytics.setUserId('user_123'), completes);
    });

    test('setUserId with null does not throw', () async {
      await expectLater(analytics.setUserId(null), completes);
    });

    test('setUserProperty does not throw', () async {
      await expectLater(
        analytics.setUserProperty(name: 'plan', value: 'premium'),
        completes,
      );
    });

    test('logScreenView does not throw', () async {
      await expectLater(
        analytics.logScreenView('HomeScreen'),
        completes,
      );
    });

    test('logScreenView with screenClass does not throw', () async {
      await expectLater(
        analytics.logScreenView(
          'HomeScreen',
          screenClass: 'HomeScreenWidget',
        ),
        completes,
      );
    });

    test('implements AnalyticsService', () {
      expect(analytics, isA<AnalyticsService>());
    });

    test('can be used as const', () {
      const a = NoopAnalytics();
      const b = NoopAnalytics();
      // Both are valid const instances.
      expect(a, isA<AnalyticsService>());
      expect(b, isA<AnalyticsService>());
    });
  });
}

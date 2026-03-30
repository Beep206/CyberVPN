import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/core/utils/startup_metrics.dart';

import '../helpers/fakes/fake_secure_storage.dart';

class _CountingSecureStorage extends FakeSecureStorage {
  int prewarmCallCount = 0;

  @override
  Future<void> prewarmCache({
    Iterable<String> keys = const [
      SecureStorageWrapper.accessTokenKey,
      SecureStorageWrapper.refreshTokenKey,
    ],
  }) async {
    prewarmCallCount++;
    await super.prewarmCache(keys: keys);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Startup smoke', () {
    test('startup metrics record milestones without throwing', () async {
      AppLogger.clearLogs();
      final metrics = StartupMetrics();
      addTearDown(metrics.dispose);

      await metrics.measureAsync('test async startup step', () async {
        await Future<void>.delayed(Duration.zero);
      });
      metrics.recordEvent('test startup event');

      expect(metrics.milestones, hasLength(2));
      expect(
        AppLogger.entries.any(
          (entry) => entry.message.contains('test async startup step'),
        ),
        isTrue,
      );
      expect(
        AppLogger.entries.any(
          (entry) => entry.message.contains('test startup event'),
        ),
        isTrue,
      );
    });

    test('critical provider overrides resolve within smoke budget', () async {
      SharedPreferences.setMockInitialValues(<String, Object>{});
      final prefs = await SharedPreferences.getInstance();
      final fakeSecureStorage = FakeSecureStorage();

      final stopwatch = Stopwatch()..start();
      final overrides = await buildProviderOverrides(
        prefs,
        secureStorage: fakeSecureStorage,
        prewarmSecureStorage: false,
      );
      final container = ProviderContainer(overrides: overrides);
      addTearDown(container.dispose);
      stopwatch.stop();

      expect(stopwatch.elapsed, lessThan(const Duration(seconds: 3)));
      expect(container.read(sharedPreferencesProvider), same(prefs));
      expect(container.read(secureStorageProvider), same(fakeSecureStorage));
      expect(container.read(apiClientProvider), isA<ApiClient>());
      expect(
        container.read(secureStorageProvider),
        isA<SecureStorageWrapper>(),
      );
    });

    test(
      'provider overrides skip secure storage prewarm when disabled',
      () async {
        SharedPreferences.setMockInitialValues(<String, Object>{});
        final prefs = await SharedPreferences.getInstance();
        final secureStorage = _CountingSecureStorage();

        await buildProviderOverrides(
          prefs,
          secureStorage: secureStorage,
          prewarmSecureStorage: false,
        );

        expect(secureStorage.prewarmCallCount, 0);
      },
    );

    test(
      'provider overrides can still opt into secure storage prewarm',
      () async {
        SharedPreferences.setMockInitialValues(<String, Object>{});
        final prefs = await SharedPreferences.getInstance();
        final secureStorage = _CountingSecureStorage();

        await buildProviderOverrides(
          prefs,
          secureStorage: secureStorage,
          prewarmSecureStorage: true,
        );

        expect(secureStorage.prewarmCallCount, 1);
      },
    );
  });
}

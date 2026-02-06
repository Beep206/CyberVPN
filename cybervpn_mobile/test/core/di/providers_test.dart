import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:cybervpn_mobile/features/servers/domain/repositories/server_repository.dart';
import 'package:cybervpn_mobile/features/subscription/domain/repositories/subscription_repository.dart';
import 'package:cybervpn_mobile/features/vpn/domain/repositories/vpn_repository.dart';

// All repository and infrastructure providers are now in core/di/providers.dart (imported above)
import 'package:cybervpn_mobile/core/providers/shared_preferences_provider.dart';

void main() {
  group('DI providers', () {
    late ProviderContainer container;

    setUp(() async {
      // Initialize SharedPreferences with empty values for testing.
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();

      final overrides = await buildProviderOverrides(prefs);
      container = ProviderContainer(
        overrides: overrides,
      );
    });

    tearDown(() {
      container.dispose();
    });

    test('sharedPreferencesProvider resolves without error', () {
      final prefs = container.read(sharedPreferencesProvider);
      expect(prefs, isA<SharedPreferences>());
    });

    test('secureStorageProvider resolves without error', () {
      final storage = container.read(secureStorageProvider);
      expect(storage, isA<SecureStorageWrapper>());
    });

    test('localStorageProvider resolves without error', () {
      final storage = container.read(localStorageProvider);
      expect(storage, isA<LocalStorageWrapper>());
    });

    test('networkInfoProvider resolves without error', () {
      final networkInfo = container.read(networkInfoProvider);
      expect(networkInfo, isA<NetworkInfo>());
    });

    test('apiClientProvider resolves without error', () {
      final apiClient = container.read(apiClientProvider);
      expect(apiClient, isA<ApiClient>());
    });

    test('authRepositoryProvider resolves without UnimplementedError', () {
      final repo = container.read(authRepositoryProvider);
      expect(repo, isA<AuthRepository>());
    });

    test('vpnRepositoryProvider resolves without UnimplementedError', () {
      final repo = container.read(vpnRepositoryProvider);
      expect(repo, isA<VpnRepository>());
    });

    test('serverRepositoryProvider resolves without UnimplementedError', () {
      final repo = container.read(serverRepositoryProvider);
      expect(repo, isA<ServerRepository>());
    });

    test('subscriptionRepositoryProvider resolves without UnimplementedError',
        () {
      final repo = container.read(subscriptionRepositoryProvider);
      expect(repo, isA<SubscriptionRepository>());
    });

    test('all providers resolve without throwing', () {
      // This test attempts to read every overridden provider to ensure
      // the full dependency graph is valid and no UnimplementedError is thrown.
      expect(
        () {
          container.read(sharedPreferencesProvider);
          container.read(secureStorageProvider);
          container.read(localStorageProvider);
          container.read(networkInfoProvider);
          container.read(apiClientProvider);
          container.read(authRepositoryProvider);
          container.read(vpnRepositoryProvider);
          container.read(serverRepositoryProvider);
          container.read(subscriptionRepositoryProvider);
        },
        returnsNormally,
      );
    });
  });
}

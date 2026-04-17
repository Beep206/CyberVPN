import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/servers/data/datasources/ping_service.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_notifier.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_state.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/di/profile_providers.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/profile_server.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/entities/vpn_profile.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/domain/repositories/profile_repository.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/providers/profile_update_notifier.dart';

class _FakeSettingsNotifier extends SettingsNotifier {
  _FakeSettingsNotifier(this._settings);

  final AppSettings _settings;

  @override
  Future<AppSettings> build() async => _settings;
}

class _FakeVpnConnectionNotifier extends AsyncNotifier<VpnConnectionState>
    implements VpnConnectionNotifier {
  _FakeVpnConnectionNotifier(this._state);

  final VpnConnectionState _state;

  @override
  Future<VpnConnectionState> build() async => _state;

  @override
  Future<void> applyKillSwitchSetting(bool enabled) async {}

  @override
  Future<void> connect(ServerEntity server) async {}

  @override
  Future<void> connectFromCustomServer(ImportedConfig customServer) async {}

  @override
  Future<void> connectToLastOrRecommended() async {}

  @override
  Future<void> disconnect() async {}

  @override
  Future<void> handleNetworkChange(bool isOnline) async {}
}

class _FakeConfigImportNotifier extends ConfigImportNotifier {
  _FakeConfigImportNotifier(this._configs);

  final List<ImportedConfig> _configs;
  final List<String> refreshedUrls = <String>[];

  @override
  Future<ConfigImportState> build() async {
    return ConfigImportState(customServers: _configs);
  }

  @override
  Future<bool> refreshSubscriptionUrl(String url) async {
    refreshedUrls.add(url);
    return true;
  }
}

class _FakePingService extends PingService {
  _FakePingService(this.latency);

  final int latency;

  @override
  Future<int?> pingServer(String host, int port) async => latency;
}

class _MockProfileRepository extends Mock implements ProfileRepository {}

void main() {
  ProviderContainer createContainer({
    required AppSettings settings,
    required List<VpnProfile> profiles,
    required _MockProfileRepository repository,
    required _FakeConfigImportNotifier configImportNotifier,
    PingService? pingService,
  }) {
    return ProviderContainer(
      overrides: [
        settingsProvider.overrideWith(() => _FakeSettingsNotifier(settings)),
        vpnConnectionProvider.overrideWith(
          () => _FakeVpnConnectionNotifier(const VpnDisconnected()),
        ),
        configImportProvider.overrideWith(() => configImportNotifier),
        profileListProvider.overrideWithValue(AsyncData(profiles)),
        vpnProfileRepositoryProvider.overrideWithValue(repository),
        if (pingService != null) pingServiceProvider.overrideWithValue(pingService),
      ],
    );
  }

  group('ProfileUpdateNotifier', () {
    test('refreshes due provider profiles and imported sources on app open', () async {
      final repository = _MockProfileRepository();
      final configImportNotifier = _FakeConfigImportNotifier([
        ImportedConfig(
          id: 'cfg-1',
          name: 'Imported',
          rawUri: 'vless://imported',
          protocol: 'vless',
          serverAddress: 'imported.example.com',
          port: 443,
          source: ImportSource.subscriptionUrl,
          subscriptionUrl: 'https://provider.example/sub',
          importedAt: DateTime.now().subtract(const Duration(hours: 2)),
        ),
      ]);
      when(() => repository.updateSubscription('remote-1')).thenAnswer(
        (_) async => const Success(null),
      );

      final container = createContainer(
        settings: const AppSettings(subscriptionAutoUpdateIntervalHours: 1),
        profiles: [
          VpnProfile.remote(
            id: 'remote-1',
            name: 'Provider',
            subscriptionUrl: 'encrypted',
            isActive: false,
            sortOrder: 0,
            createdAt: DateTime(2026, 4, 17, 10),
            lastUpdatedAt: DateTime.now().subtract(const Duration(hours: 2)),
            servers: const [],
          ),
        ],
        repository: repository,
        configImportNotifier: configImportNotifier,
      );
      addTearDown(container.dispose);
      final sub = container.listen(
        profileUpdateNotifierProvider,
        (previous, next) {},
      );
      addTearDown(sub.close);
      await container.read(settingsProvider.future);
      await container.read(configImportProvider.future);
      await container.read(profileListProvider.future);

      await container
          .read(profileUpdateNotifierProvider.notifier)
          .handleAppOpen(trigger: SubscriptionLifecycleTrigger.startup);

      final state = container.read(profileUpdateNotifierProvider);
      expect(state.lastUpdateCount, 1);
      expect(state.lastImportRefreshCount, 1);
      expect(state.lastLifecycleTrigger, SubscriptionLifecycleTrigger.startup);
      expect(
        configImportNotifier.refreshedUrls,
        contains('https://provider.example/sub'),
      );
      verify(() => repository.updateSubscription('remote-1')).called(1);
    });

    test('skips lifecycle refresh when on-open automation is disabled', () async {
      final repository = _MockProfileRepository();
      final configImportNotifier = _FakeConfigImportNotifier(const []);
      final container = createContainer(
        settings: const AppSettings(
          subscriptionAutoUpdateOnOpen: false,
          subscriptionPingOnOpenEnabled: false,
        ),
        profiles: const [],
        repository: repository,
        configImportNotifier: configImportNotifier,
      );
      addTearDown(container.dispose);
      final sub = container.listen(
        profileUpdateNotifierProvider,
        (previous, next) {},
      );
      addTearDown(sub.close);
      await container.read(settingsProvider.future);
      await container.read(configImportProvider.future);
      await container.read(profileListProvider.future);

      await container
          .read(profileUpdateNotifierProvider.notifier)
          .handleAppOpen(trigger: SubscriptionLifecycleTrigger.resume);

      verifyNever(() => repository.updateSubscription(any()));
      verifyNever(
        () => repository.updateProfileServerLatencies(any(), any()),
      );
      expect(container.read(profileUpdateNotifierProvider).lastUpdatedAt, isNull);
    });

    test('updates latency cache on app open when ping is enabled', () async {
      final repository = _MockProfileRepository();
      final configImportNotifier = _FakeConfigImportNotifier(const []);
      when(
        () => repository.updateProfileServerLatencies(
          'remote-1',
          any(),
        ),
      ).thenAnswer((_) async => const Success(null));

      final container = createContainer(
        settings: const AppSettings(
          subscriptionAutoUpdateOnOpen: false,
          subscriptionPingOnOpenEnabled: true,
        ),
        profiles: [
          VpnProfile.remote(
            id: 'remote-1',
            name: 'Provider',
            subscriptionUrl: 'encrypted',
            isActive: false,
            sortOrder: 0,
            createdAt: DateTime(2026, 4, 17, 10),
            lastUpdatedAt: DateTime.now(),
            servers: [
              ProfileServer(
                id: 'srv-1',
                profileId: 'remote-1',
                name: 'Berlin',
                serverAddress: 'berlin.example.com',
                port: 443,
                protocol: VpnProtocol.vless,
                configData: '{}',
                sortOrder: 0,
                createdAt: DateTime(2026, 4, 17, 10),
              ),
            ],
          ),
        ],
        repository: repository,
        configImportNotifier: configImportNotifier,
        pingService: _FakePingService(42),
      );
      addTearDown(container.dispose);
      final sub = container.listen(
        profileUpdateNotifierProvider,
        (previous, next) {},
      );
      addTearDown(sub.close);
      await container.read(settingsProvider.future);
      await container.read(configImportProvider.future);
      await container.read(profileListProvider.future);

      await container
          .read(profileUpdateNotifierProvider.notifier)
          .handleAppOpen(trigger: SubscriptionLifecycleTrigger.resume);

      final state = container.read(profileUpdateNotifierProvider);
      expect(state.lastPingedProfileCount, 1);
      verify(
        () => repository.updateProfileServerLatencies(
          'remote-1',
          {'srv-1': 42},
        ),
      ).called(1);
    });
  });
}

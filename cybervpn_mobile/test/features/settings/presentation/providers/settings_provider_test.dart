import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/settings/data/repositories/settings_repository_impl.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

void main() {
  late SettingsRepositoryImpl repository;
  late ProviderContainer container;

  Future<void> initContainer([Map<String, Object> values = const {}]) async {
    SharedPreferences.setMockInitialValues(values);
    final prefs = await SharedPreferences.getInstance();
    repository = SettingsRepositoryImpl(sharedPreferences: prefs);
    container = ProviderContainer(
      overrides: [settingsRepositoryProvider.overrideWithValue(repository)],
    );
  }

  Future<AppSettings> getPersistedSettings() async {
    final result = await repository.getSettings();
    expect(result, isA<Success<AppSettings>>());
    return (result as Success<AppSettings>).data;
  }

  group('SettingsNotifier phase 8 integration', () {
    setUp(() async {
      await initContainer();
    });

    tearDown(() {
      container.dispose();
    });

    test(
      'updates excluded route entries and keeps vpn settings in sync',
      () async {
        await container.read(settingsProvider.future);

        await container
            .read(settingsProvider.notifier)
            .updateExcludedRouteEntries([
              ExcludedRouteEntry.parse('10.0.0.0/8'),
              ExcludedRouteEntry.parse('2001:db8::/32'),
            ]);

        final vpnSettings = container.read(vpnSettingsProvider);
        expect(vpnSettings.bypassSubnets, ['10.0.0.0/8', '2001:db8::/32']);
        expect(vpnSettings.excludedRouteEntries, hasLength(2));
        expect(
          vpnSettings.excludedRouteEntries.last.targetType,
          ExcludedRouteTargetType.ipv6Cidr,
        );

        final persisted = await getPersistedSettings();
        expect(persisted.bypassSubnets, ['10.0.0.0/8', '2001:db8::/32']);
        expect(persisted.excludedRouteEntries, hasLength(2));
      },
    );

    test(
      'updates advanced vpn and subscription policy settings end-to-end',
      () async {
        await container.read(settingsProvider.future);
        final notifier = container.read(settingsProvider.notifier);

        await notifier.updateLocalDnsSettings(enabled: true, port: 1054);
        await notifier.updateUseDnsFromJson(true);
        await notifier.updateSniffing(true);
        await notifier.updateVpnRunMode(VpnRunMode.proxyOnly);
        await notifier.updateServerAddressResolve(
          enabled: true,
          dohUrl: 'https://dns.example/dns-query',
          dnsIp: '1.1.1.1',
        );
        await notifier.updateSubscriptionSettings(
          autoUpdateEnabled: false,
          autoUpdateIntervalHours: 12,
          updateNotificationsEnabled: true,
          autoUpdateOnOpen: false,
          pingOnOpenEnabled: true,
          connectStrategy: SubscriptionConnectStrategy.lowestDelay,
          preventDuplicateImports: false,
          collapseSubscriptions: false,
          noFilter: true,
          sortMode: SubscriptionSortMode.alphabetical,
        );
        await notifier.updateSubscriptionUserAgent(
          mode: SubscriptionUserAgentMode.custom,
          value: 'CyberVPN-Test/8.0',
        );
        await notifier.updatePingResultMode(PingResultMode.icon);
        await notifier.updateAllowLanConnections(true);
        await notifier.updateAppAutoStart(true);

        final vpnSettings = container.read(vpnSettingsProvider);
        expect(vpnSettings.useLocalDns, isTrue);
        expect(vpnSettings.localDnsPort, 1054);
        expect(vpnSettings.useDnsFromJson, isTrue);
        expect(vpnSettings.sniffingEnabled, isTrue);
        expect(vpnSettings.vpnRunMode, VpnRunMode.proxyOnly);
        expect(vpnSettings.serverAddressResolveEnabled, isTrue);
        expect(
          vpnSettings.serverAddressResolveDohUrl,
          'https://dns.example/dns-query',
        );
        expect(vpnSettings.serverAddressResolveDnsIp, '1.1.1.1');
        expect(vpnSettings.allowLanConnections, isTrue);
        expect(vpnSettings.appAutoStart, isTrue);

        final subscriptionSettings = container.read(
          subscriptionSettingsProvider,
        );
        expect(subscriptionSettings.autoUpdateEnabled, isFalse);
        expect(subscriptionSettings.autoUpdateIntervalHours, 12);
        expect(subscriptionSettings.updateNotificationsEnabled, isTrue);
        expect(subscriptionSettings.autoUpdateOnOpen, isFalse);
        expect(subscriptionSettings.pingOnOpenEnabled, isTrue);
        expect(
          subscriptionSettings.connectStrategy,
          SubscriptionConnectStrategy.lowestDelay,
        );
        expect(subscriptionSettings.preventDuplicateImports, isFalse);
        expect(subscriptionSettings.collapseSubscriptions, isFalse);
        expect(subscriptionSettings.noFilter, isTrue);
        expect(
          subscriptionSettings.userAgentMode,
          SubscriptionUserAgentMode.custom,
        );
        expect(subscriptionSettings.userAgentValue, 'CyberVPN-Test/8.0');
        expect(
          subscriptionSettings.sortMode,
          SubscriptionSortMode.alphabetical,
        );

        final pingSettings = container.read(pingSettingsPreferencesProvider);
        expect(pingSettings.resultMode, PingResultMode.icon);

        final persisted = await getPersistedSettings();
        expect(persisted.useLocalDns, isTrue);
        expect(persisted.subscriptionAutoUpdateEnabled, isFalse);
        expect(
          persisted.subscriptionConnectStrategy,
          SubscriptionConnectStrategy.lowestDelay,
        );
        expect(persisted.subscriptionUserAgentValue, 'CyberVPN-Test/8.0');
        expect(persisted.pingResultMode, PingResultMode.icon);
        expect(persisted.allowLanConnections, isTrue);
        expect(persisted.appAutoStart, isTrue);
      },
    );
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/settings/data/repositories/settings_repository_impl.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/routing_profile.dart';

void main() {
  late SettingsRepositoryImpl repository;

  /// Initialises [SharedPreferences] with the given [values] and creates
  /// a fresh [SettingsRepositoryImpl] backed by it.
  Future<void> initRepo([Map<String, Object> values = const {}]) async {
    SharedPreferences.setMockInitialValues(values);
    final prefs = await SharedPreferences.getInstance();
    repository = SettingsRepositoryImpl(sharedPreferences: prefs);
  }

  /// Helper to unwrap getSettings Result for assertion convenience.
  Future<AppSettings> getSettings() async {
    final result = await repository.getSettings();
    expect(result, isA<Success<AppSettings>>());
    return (result as Success<AppSettings>).data;
  }

  // ---------------------------------------------------------------------------
  // getSettings - default values
  // ---------------------------------------------------------------------------
  group('getSettings - default values when no keys present', () {
    setUp(initRepo);

    test('returns AppSettings with all defaults', () async {
      final settings = await getSettings();
      const defaults = AppSettings();

      expect(settings.themeMode, equals(defaults.themeMode));
      expect(settings.brightness, equals(defaults.brightness));
      expect(settings.dynamicColor, equals(defaults.dynamicColor));
      expect(settings.preferredProtocol, equals(defaults.preferredProtocol));
      expect(
        settings.autoConnectOnLaunch,
        equals(defaults.autoConnectOnLaunch),
      );
      expect(
        settings.autoConnectUntrustedWifi,
        equals(defaults.autoConnectUntrustedWifi),
      );
      expect(settings.killSwitch, equals(defaults.killSwitch));
      expect(settings.routingEnabled, equals(defaults.routingEnabled));
      expect(settings.routingProfiles, equals(defaults.routingProfiles));
      expect(
        settings.activeRoutingProfileId,
        equals(defaults.activeRoutingProfileId),
      );
      expect(settings.bypassSubnets, equals(defaults.bypassSubnets));
      expect(
        settings.excludedRouteEntries,
        equals(defaults.excludedRouteEntries),
      );
      expect(settings.splitTunneling, equals(defaults.splitTunneling));
      expect(settings.perAppProxyMode, equals(defaults.perAppProxyMode));
      expect(settings.perAppProxyAppIds, equals(defaults.perAppProxyAppIds));
      expect(settings.dnsProvider, equals(defaults.dnsProvider));
      expect(settings.customDns, isNull);
      expect(settings.useLocalDns, equals(defaults.useLocalDns));
      expect(settings.localDnsPort, equals(defaults.localDnsPort));
      expect(settings.useDnsFromJson, equals(defaults.useDnsFromJson));
      expect(
        settings.fragmentationEnabled,
        equals(defaults.fragmentationEnabled),
      );
      expect(settings.muxEnabled, equals(defaults.muxEnabled));
      expect(settings.preferredIpType, equals(defaults.preferredIpType));
      expect(settings.sniffingEnabled, equals(defaults.sniffingEnabled));
      expect(settings.vpnRunMode, equals(defaults.vpnRunMode));
      expect(
        settings.serverAddressResolveEnabled,
        equals(defaults.serverAddressResolveEnabled),
      );
      expect(settings.pingMode, equals(defaults.pingMode));
      expect(settings.pingTestUrl, equals(defaults.pingTestUrl));
      expect(settings.pingDisplayMode, equals(defaults.pingDisplayMode));
      expect(settings.pingResultMode, equals(defaults.pingResultMode));
      expect(settings.mtuMode, equals(defaults.mtuMode));
      expect(settings.mtuValue, equals(defaults.mtuValue));
      expect(
        settings.subscriptionAutoUpdateEnabled,
        equals(defaults.subscriptionAutoUpdateEnabled),
      );
      expect(
        settings.subscriptionAutoUpdateIntervalHours,
        equals(defaults.subscriptionAutoUpdateIntervalHours),
      );
      expect(
        settings.subscriptionAutoUpdateOnOpen,
        equals(defaults.subscriptionAutoUpdateOnOpen),
      );
      expect(
        settings.subscriptionConnectStrategy,
        equals(defaults.subscriptionConnectStrategy),
      );
      expect(
        settings.subscriptionUserAgentMode,
        equals(defaults.subscriptionUserAgentMode),
      );
      expect(
        settings.subscriptionSortMode,
        equals(defaults.subscriptionSortMode),
      );
      expect(
        settings.allowLanConnections,
        equals(defaults.allowLanConnections),
      );
      expect(settings.appAutoStart, equals(defaults.appAutoStart));
      expect(settings.locale, equals(defaults.locale));
      expect(
        settings.notificationConnection,
        equals(defaults.notificationConnection),
      );
      expect(settings.notificationExpiry, equals(defaults.notificationExpiry));
      expect(
        settings.notificationPromotional,
        equals(defaults.notificationPromotional),
      );
      expect(
        settings.notificationReferral,
        equals(defaults.notificationReferral),
      );
      expect(
        settings.notificationVpnSpeed,
        equals(defaults.notificationVpnSpeed),
      );
      expect(
        settings.clipboardAutoDetect,
        equals(defaults.clipboardAutoDetect),
      );
      expect(settings.logLevel, equals(defaults.logLevel));
    });

    test('default themeMode is cyberpunk', () async {
      final settings = await getSettings();
      expect(settings.themeMode, AppThemeMode.cyberpunk);
    });

    test('default brightness is system', () async {
      final settings = await getSettings();
      expect(settings.brightness, AppBrightness.system);
    });

    test('default preferredProtocol is auto', () async {
      final settings = await getSettings();
      expect(settings.preferredProtocol, PreferredProtocol.auto);
    });

    test('default locale is en', () async {
      final settings = await getSettings();
      expect(settings.locale, 'en');
    });

    test('default mtuValue is 1400', () async {
      final settings = await getSettings();
      expect(settings.mtuValue, 1400);
    });

    test('default logLevel is info', () async {
      final settings = await getSettings();
      expect(settings.logLevel, LogLevel.info);
    });
  });

  // ---------------------------------------------------------------------------
  // getSettings - reads stored values
  // ---------------------------------------------------------------------------
  group('getSettings - reads stored values', () {
    test('returns correct AppSettings when all keys are present', () async {
      final routingProfiles = [
        const RoutingProfile(
          id: 'profile-1',
          name: 'Streaming Direct',
          rules: [
            RoutingRule(
              id: 'rule-1',
              matchType: RoutingRuleMatchType.domainSuffix,
              value: 'youtube.com',
              action: RoutingRuleAction.direct,
            ),
          ],
        ),
      ];

      await initRepo({
        'settings.themeMode': 'materialYou',
        'settings.brightness': 'dark',
        'settings.dynamicColor': true,
        'settings.preferredProtocol': 'vlessReality',
        'settings.autoConnectOnLaunch': true,
        'settings.autoConnectUntrustedWifi': true,
        'settings.killSwitch': true,
        'settings.routingEnabled': true,
        'settings.routingProfiles':
            '[{"id":"profile-1","name":"Streaming Direct","enabled":true,"rules":[{"id":"rule-1","matchType":"domainSuffix","value":"youtube.com","action":"direct","enabled":true}]}]',
        'settings.activeRoutingProfileId': 'profile-1',
        'settings.bypassSubnets': ['10.0.0.0/8', '2001:db8::/32'],
        'settings.excludedRouteEntries':
            '[{"rawValue":"10.0.0.0/8","targetType":"ipv4Cidr"},{"rawValue":"2001:db8::/32","targetType":"ipv6Cidr"}]',
        'settings.splitTunneling': true,
        'settings.perAppProxyMode': 'proxySelected',
        'settings.perAppProxyAppIds': [
          'com.example.browser',
          'com.example.player',
        ],
        'settings.dnsProvider': 'cloudflare',
        'settings.customDns': '1.1.1.1',
        'settings.useLocalDns': true,
        'settings.localDnsPort': 1054,
        'settings.useDnsFromJson': true,
        'settings.fragmentationEnabled': true,
        'settings.muxEnabled': true,
        'settings.preferredIpType': 'ipv6',
        'settings.sniffingEnabled': true,
        'settings.vpnRunMode': 'proxyOnly',
        'settings.serverAddressResolveEnabled': true,
        'settings.serverAddressResolveDohUrl': 'https://dns.example/dns-query',
        'settings.serverAddressResolveDnsIp': '1.1.1.1',
        'settings.pingMode': 'realDelay',
        'settings.pingTestUrl': 'https://cp.cloudflare.com/generate_204',
        'settings.pingDisplayMode': 'quality',
        'settings.pingResultMode': 'icon',
        'settings.mtuMode': 'manual',
        'settings.mtuValue': 1500,
        'settings.subscriptionAutoUpdateEnabled': false,
        'settings.subscriptionAutoUpdateIntervalHours': 12,
        'settings.subscriptionUpdateNotificationsEnabled': true,
        'settings.subscriptionAutoUpdateOnOpen': false,
        'settings.subscriptionPingOnOpenEnabled': true,
        'settings.subscriptionConnectStrategy': 'lowestDelay',
        'settings.preventDuplicateImports': false,
        'settings.collapseSubscriptions': false,
        'settings.subscriptionNoFilter': true,
        'settings.subscriptionUserAgentMode': 'custom',
        'settings.subscriptionUserAgentValue': 'CyberVPN-Test/8.0',
        'settings.subscriptionSortMode': 'alphabetical',
        'settings.allowLanConnections': true,
        'settings.appAutoStart': true,
        'settings.locale': 'ru',
        'settings.notificationConnection': false,
        'settings.notificationExpiry': false,
        'settings.notificationPromotional': true,
        'settings.notificationReferral': false,
        'settings.notificationVpnSpeed': true,
        'settings.clipboardAutoDetect': false,
        'settings.logLevel': 'debug',
      });

      final settings = await getSettings();

      expect(settings.themeMode, AppThemeMode.materialYou);
      expect(settings.brightness, AppBrightness.dark);
      expect(settings.dynamicColor, isTrue);
      expect(settings.preferredProtocol, PreferredProtocol.vlessReality);
      expect(settings.autoConnectOnLaunch, isTrue);
      expect(settings.autoConnectUntrustedWifi, isTrue);
      expect(settings.killSwitch, isTrue);
      expect(settings.routingEnabled, isTrue);
      expect(settings.routingProfiles, routingProfiles);
      expect(settings.activeRoutingProfileId, 'profile-1');
      expect(settings.bypassSubnets, ['10.0.0.0/8', '2001:db8::/32']);
      expect(settings.excludedRouteEntries, hasLength(2));
      expect(settings.splitTunneling, isTrue);
      expect(settings.perAppProxyMode, PerAppProxyMode.proxySelected);
      expect(settings.perAppProxyAppIds, [
        'com.example.browser',
        'com.example.player',
      ]);
      expect(settings.dnsProvider, DnsProvider.cloudflare);
      expect(settings.customDns, '1.1.1.1');
      expect(settings.useLocalDns, isTrue);
      expect(settings.localDnsPort, 1054);
      expect(settings.useDnsFromJson, isTrue);
      expect(settings.fragmentationEnabled, isTrue);
      expect(settings.muxEnabled, isTrue);
      expect(settings.preferredIpType, PreferredIpType.ipv6);
      expect(settings.sniffingEnabled, isTrue);
      expect(settings.vpnRunMode, VpnRunMode.proxyOnly);
      expect(settings.serverAddressResolveEnabled, isTrue);
      expect(
        settings.serverAddressResolveDohUrl,
        'https://dns.example/dns-query',
      );
      expect(settings.serverAddressResolveDnsIp, '1.1.1.1');
      expect(settings.pingMode, PingMode.realDelay);
      expect(settings.pingTestUrl, 'https://cp.cloudflare.com/generate_204');
      expect(settings.pingDisplayMode, PingDisplayMode.quality);
      expect(settings.pingResultMode, PingResultMode.icon);
      expect(settings.mtuMode, MtuMode.manual);
      expect(settings.mtuValue, 1500);
      expect(settings.subscriptionAutoUpdateEnabled, isFalse);
      expect(settings.subscriptionAutoUpdateIntervalHours, 12);
      expect(settings.subscriptionUpdateNotificationsEnabled, isTrue);
      expect(settings.subscriptionAutoUpdateOnOpen, isFalse);
      expect(settings.subscriptionPingOnOpenEnabled, isTrue);
      expect(
        settings.subscriptionConnectStrategy,
        SubscriptionConnectStrategy.lowestDelay,
      );
      expect(settings.preventDuplicateImports, isFalse);
      expect(settings.collapseSubscriptions, isFalse);
      expect(settings.subscriptionNoFilter, isTrue);
      expect(
        settings.subscriptionUserAgentMode,
        SubscriptionUserAgentMode.custom,
      );
      expect(settings.subscriptionUserAgentValue, 'CyberVPN-Test/8.0');
      expect(settings.subscriptionSortMode, SubscriptionSortMode.alphabetical);
      expect(settings.allowLanConnections, isTrue);
      expect(settings.appAutoStart, isTrue);
      expect(settings.locale, 'ru');
      expect(settings.notificationConnection, isFalse);
      expect(settings.notificationExpiry, isFalse);
      expect(settings.notificationPromotional, isTrue);
      expect(settings.notificationReferral, isFalse);
      expect(settings.notificationVpnSpeed, isTrue);
      expect(settings.clipboardAutoDetect, isFalse);
      expect(settings.logLevel, LogLevel.debug);
    });

    test('returns defaults for invalid enum strings', () async {
      await initRepo({
        'settings.themeMode': 'invalidValue',
        'settings.dnsProvider': 'nonexistent',
        'settings.logLevel': 'verbose', // not in enum
        'settings.perAppProxyMode': 'nope',
        'settings.preferredIpType': 'nope',
        'settings.pingMode': 'nope',
        'settings.pingDisplayMode': 'nope',
      });

      final settings = await getSettings();
      const defaults = AppSettings();

      expect(settings.themeMode, defaults.themeMode);
      expect(settings.dnsProvider, defaults.dnsProvider);
      expect(settings.logLevel, defaults.logLevel);
      expect(settings.perAppProxyMode, defaults.perAppProxyMode);
      expect(settings.preferredIpType, defaults.preferredIpType);
      expect(settings.pingMode, defaults.pingMode);
      expect(settings.pingDisplayMode, defaults.pingDisplayMode);
    });

    test('reads partial keys and defaults the rest', () async {
      await initRepo({'settings.locale': 'de', 'settings.killSwitch': true});

      final settings = await getSettings();

      expect(settings.locale, 'de');
      expect(settings.killSwitch, isTrue);
      // Everything else should be default
      expect(settings.themeMode, AppThemeMode.cyberpunk);
      expect(settings.brightness, AppBrightness.system);
      expect(settings.dynamicColor, isFalse);
    });

    test('falls back to empty routing profiles for malformed json', () async {
      await initRepo({
        'settings.routingProfiles': '{invalid-json',
        'settings.routingEnabled': true,
      });

      final settings = await getSettings();

      expect(settings.routingEnabled, isTrue);
      expect(settings.routingProfiles, isEmpty);
    });

    test(
      'derives typed excluded routes from legacy bypassSubnets storage',
      () async {
        await initRepo({
          'settings.bypassSubnets': ['10.0.0.0/8', '2001:db8::/32'],
        });

        final settings = await getSettings();

        expect(
          settings.excludedRouteEntries.map((entry) => entry.normalizedValue),
          ['10.0.0.0/8', '2001:db8::/32'],
        );
        expect(
          settings.excludedRouteEntries.first.targetType,
          ExcludedRouteTargetType.ipv4Cidr,
        );
        expect(
          settings.excludedRouteEntries.last.targetType,
          ExcludedRouteTargetType.ipv6Cidr,
        );
      },
    );

    test(
      'derives pingResultMode from legacy pingDisplayMode when unset',
      () async {
        await initRepo({'settings.pingDisplayMode': 'quality'});

        final settings = await getSettings();

        expect(settings.pingDisplayMode, PingDisplayMode.quality);
        expect(settings.pingResultMode, PingResultMode.icon);
      },
    );
  });

  // ---------------------------------------------------------------------------
  // updateSettings
  // ---------------------------------------------------------------------------
  group('updateSettings', () {
    test('persists all fields and reads them back correctly', () async {
      await initRepo();

      const routingProfile = RoutingProfile(
        id: 'profile-1',
        name: 'Apps Direct',
        rules: [
          RoutingRule(
            id: 'rule-1',
            matchType: RoutingRuleMatchType.packageName,
            value: 'com.example.player',
            action: RoutingRuleAction.direct,
          ),
        ],
      );

      const custom = AppSettings(
        themeMode: AppThemeMode.materialYou,
        brightness: AppBrightness.light,
        dynamicColor: true,
        preferredProtocol: PreferredProtocol.vlessXhttp,
        autoConnectOnLaunch: true,
        autoConnectUntrustedWifi: true,
        killSwitch: true,
        routingEnabled: true,
        routingProfiles: [routingProfile],
        activeRoutingProfileId: 'profile-1',
        bypassSubnets: ['10.0.0.0/8'],
        excludedRouteEntries: [
          ExcludedRouteEntry(
            rawValue: '10.0.0.0/8',
            targetType: ExcludedRouteTargetType.ipv4Cidr,
          ),
        ],
        splitTunneling: true,
        perAppProxyMode: PerAppProxyMode.bypassSelected,
        perAppProxyAppIds: ['com.example.browser'],
        dnsProvider: DnsProvider.google,
        customDns: '8.8.8.8',
        useLocalDns: true,
        localDnsPort: 1054,
        useDnsFromJson: true,
        fragmentationEnabled: true,
        muxEnabled: true,
        preferredIpType: PreferredIpType.ipv4,
        sniffingEnabled: true,
        vpnRunMode: VpnRunMode.proxyOnly,
        serverAddressResolveEnabled: true,
        serverAddressResolveDohUrl: 'https://dns.example/dns-query',
        serverAddressResolveDnsIp: '8.8.8.8',
        pingMode: PingMode.realDelay,
        pingTestUrl: 'https://cp.cloudflare.com/generate_204',
        pingDisplayMode: PingDisplayMode.quality,
        pingResultMode: PingResultMode.icon,
        mtuMode: MtuMode.manual,
        mtuValue: 1300,
        subscriptionAutoUpdateEnabled: false,
        subscriptionAutoUpdateIntervalHours: 12,
        subscriptionUpdateNotificationsEnabled: true,
        subscriptionAutoUpdateOnOpen: false,
        subscriptionPingOnOpenEnabled: true,
        subscriptionConnectStrategy: SubscriptionConnectStrategy.random,
        preventDuplicateImports: false,
        collapseSubscriptions: false,
        subscriptionNoFilter: true,
        subscriptionUserAgentMode: SubscriptionUserAgentMode.custom,
        subscriptionUserAgentValue: 'CyberVPN-Test/8.0',
        subscriptionSortMode: SubscriptionSortMode.alphabetical,
        allowLanConnections: true,
        appAutoStart: true,
        locale: 'ja',
        notificationConnection: false,
        notificationExpiry: false,
        notificationPromotional: true,
        notificationReferral: false,
        notificationVpnSpeed: true,
        clipboardAutoDetect: false,
        logLevel: LogLevel.error,
      );

      await repository.updateSettings(custom);
      final result = await getSettings();

      expect(result.themeMode, AppThemeMode.materialYou);
      expect(result.brightness, AppBrightness.light);
      expect(result.dynamicColor, isTrue);
      expect(result.preferredProtocol, PreferredProtocol.vlessXhttp);
      expect(result.autoConnectOnLaunch, isTrue);
      expect(result.autoConnectUntrustedWifi, isTrue);
      expect(result.killSwitch, isTrue);
      expect(result.routingEnabled, isTrue);
      expect(result.routingProfiles, [routingProfile]);
      expect(result.activeRoutingProfileId, 'profile-1');
      expect(result.bypassSubnets, ['10.0.0.0/8']);
      expect(result.excludedRouteEntries, hasLength(1));
      expect(result.splitTunneling, isTrue);
      expect(result.perAppProxyMode, PerAppProxyMode.bypassSelected);
      expect(result.perAppProxyAppIds, ['com.example.browser']);
      expect(result.dnsProvider, DnsProvider.google);
      expect(result.customDns, '8.8.8.8');
      expect(result.useLocalDns, isTrue);
      expect(result.localDnsPort, 1054);
      expect(result.useDnsFromJson, isTrue);
      expect(result.fragmentationEnabled, isTrue);
      expect(result.muxEnabled, isTrue);
      expect(result.preferredIpType, PreferredIpType.ipv4);
      expect(result.sniffingEnabled, isTrue);
      expect(result.vpnRunMode, VpnRunMode.proxyOnly);
      expect(result.serverAddressResolveEnabled, isTrue);
      expect(
        result.serverAddressResolveDohUrl,
        'https://dns.example/dns-query',
      );
      expect(result.serverAddressResolveDnsIp, '8.8.8.8');
      expect(result.pingMode, PingMode.realDelay);
      expect(result.pingTestUrl, 'https://cp.cloudflare.com/generate_204');
      expect(result.pingDisplayMode, PingDisplayMode.quality);
      expect(result.pingResultMode, PingResultMode.icon);
      expect(result.mtuMode, MtuMode.manual);
      expect(result.mtuValue, 1300);
      expect(result.subscriptionAutoUpdateEnabled, isFalse);
      expect(result.subscriptionAutoUpdateIntervalHours, 12);
      expect(result.subscriptionUpdateNotificationsEnabled, isTrue);
      expect(result.subscriptionAutoUpdateOnOpen, isFalse);
      expect(result.subscriptionPingOnOpenEnabled, isTrue);
      expect(
        result.subscriptionConnectStrategy,
        SubscriptionConnectStrategy.random,
      );
      expect(result.preventDuplicateImports, isFalse);
      expect(result.collapseSubscriptions, isFalse);
      expect(result.subscriptionNoFilter, isTrue);
      expect(
        result.subscriptionUserAgentMode,
        SubscriptionUserAgentMode.custom,
      );
      expect(result.subscriptionUserAgentValue, 'CyberVPN-Test/8.0');
      expect(result.subscriptionSortMode, SubscriptionSortMode.alphabetical);
      expect(result.allowLanConnections, isTrue);
      expect(result.appAutoStart, isTrue);
      expect(result.locale, 'ja');
      expect(result.notificationConnection, isFalse);
      expect(result.notificationExpiry, isFalse);
      expect(result.notificationPromotional, isTrue);
      expect(result.notificationReferral, isFalse);
      expect(result.notificationVpnSpeed, isTrue);
      expect(result.clipboardAutoDetect, isFalse);
      expect(result.logLevel, LogLevel.error);
    });

    test('removes customDns key when value is null', () async {
      await initRepo({'settings.customDns': '1.1.1.1'});

      // First verify it has a value
      var settings = await getSettings();
      expect(settings.customDns, '1.1.1.1');

      // Update with null customDns
      await repository.updateSettings(const AppSettings(customDns: null));

      settings = await getSettings();
      expect(settings.customDns, isNull);
    });

    test('overwrites previously stored values', () async {
      await initRepo({'settings.locale': 'en'});

      await repository.updateSettings(const AppSettings(locale: 'fr'));

      final settings = await getSettings();
      expect(settings.locale, 'fr');
    });

    test('persists each enum as its name string', () async {
      await initRepo();

      const settings = AppSettings(
        themeMode: AppThemeMode.materialYou,
        brightness: AppBrightness.dark,
        preferredProtocol: PreferredProtocol.vlessWsTls,
        dnsProvider: DnsProvider.quad9,
        mtuMode: MtuMode.manual,
        logLevel: LogLevel.warning,
      );

      await repository.updateSettings(settings);

      // Read back and verify enum round-trip
      final result = await getSettings();
      expect(result.themeMode, AppThemeMode.materialYou);
      expect(result.brightness, AppBrightness.dark);
      expect(result.preferredProtocol, PreferredProtocol.vlessWsTls);
      expect(result.dnsProvider, DnsProvider.quad9);
      expect(result.mtuMode, MtuMode.manual);
      expect(result.logLevel, LogLevel.warning);
    });
  });

  // ---------------------------------------------------------------------------
  // resetSettings
  // ---------------------------------------------------------------------------
  group('resetSettings', () {
    test('clears all settings keys so defaults are returned', () async {
      await initRepo({
        'settings.themeMode': 'materialYou',
        'settings.brightness': 'dark',
        'settings.dynamicColor': true,
        'settings.preferredProtocol': 'vlessReality',
        'settings.autoConnectOnLaunch': true,
        'settings.killSwitch': true,
        'settings.routingEnabled': true,
        'settings.routingProfiles':
            '[{"id":"profile-1","name":"Profile","enabled":true,"rules":[]}]',
        'settings.activeRoutingProfileId': 'profile-1',
        'settings.perAppProxyMode': 'proxySelected',
        'settings.perAppProxyAppIds': ['com.example.browser'],
        'settings.locale': 'zh',
        'settings.logLevel': 'error',
        'settings.mtuValue': 1200,
        'settings.customDns': '9.9.9.9',
      });

      // Verify non-default values are present
      var settings = await getSettings();
      expect(settings.themeMode, AppThemeMode.materialYou);
      expect(settings.locale, 'zh');
      expect(settings.mtuValue, 1200);
      expect(settings.routingProfiles, isNotEmpty);
      expect(settings.perAppProxyAppIds, ['com.example.browser']);

      // Reset
      await repository.resetSettings();

      // All should be defaults now
      settings = await getSettings();
      const defaults = AppSettings();

      expect(settings.themeMode, defaults.themeMode);
      expect(settings.brightness, defaults.brightness);
      expect(settings.dynamicColor, defaults.dynamicColor);
      expect(settings.preferredProtocol, defaults.preferredProtocol);
      expect(settings.autoConnectOnLaunch, defaults.autoConnectOnLaunch);
      expect(settings.killSwitch, defaults.killSwitch);
      expect(settings.routingEnabled, defaults.routingEnabled);
      expect(settings.routingProfiles, defaults.routingProfiles);
      expect(settings.activeRoutingProfileId, defaults.activeRoutingProfileId);
      expect(settings.perAppProxyMode, defaults.perAppProxyMode);
      expect(settings.perAppProxyAppIds, defaults.perAppProxyAppIds);
      expect(settings.locale, defaults.locale);
      expect(settings.logLevel, defaults.logLevel);
      expect(settings.mtuValue, defaults.mtuValue);
      expect(settings.customDns, isNull);
    });

    test('does not affect non-settings keys', () async {
      SharedPreferences.setMockInitialValues({
        'settings.locale': 'fr',
        'other.key': 'should-remain',
      });
      final prefs = await SharedPreferences.getInstance();
      repository = SettingsRepositoryImpl(sharedPreferences: prefs);

      await repository.resetSettings();

      // Settings key should be cleared
      expect(prefs.getString('settings.locale'), isNull);

      // Other key should remain
      expect(prefs.getString('other.key'), 'should-remain');
    });

    test('update after reset persists new values', () async {
      await initRepo({'settings.locale': 'de'});

      await repository.resetSettings();
      await repository.updateSettings(const AppSettings(locale: 'es'));

      final settings = await getSettings();
      expect(settings.locale, 'es');
    });
  });

  // ---------------------------------------------------------------------------
  // Round-trip: update -> get -> reset -> get
  // ---------------------------------------------------------------------------
  group('full lifecycle', () {
    test('update, read, reset, read cycle works correctly', () async {
      await initRepo();

      // 1. Read defaults
      var settings = await getSettings();
      expect(settings, equals(const AppSettings()));

      // 2. Update with custom values
      const custom = AppSettings(
        themeMode: AppThemeMode.materialYou,
        locale: 'ko',
        killSwitch: true,
        mtuValue: 1200,
        logLevel: LogLevel.debug,
      );
      await repository.updateSettings(custom);

      // 3. Read back custom values
      settings = await getSettings();
      expect(settings.themeMode, AppThemeMode.materialYou);
      expect(settings.locale, 'ko');
      expect(settings.killSwitch, isTrue);
      expect(settings.mtuValue, 1200);
      expect(settings.logLevel, LogLevel.debug);

      // 4. Reset
      await repository.resetSettings();

      // 5. Read defaults again
      settings = await getSettings();
      expect(settings.themeMode, AppThemeMode.cyberpunk);
      expect(settings.locale, 'en');
      expect(settings.killSwitch, isFalse);
      expect(settings.mtuValue, 1400);
      expect(settings.logLevel, LogLevel.info);
    });
  });

  // ---------------------------------------------------------------------------
  // Enum coverage
  // ---------------------------------------------------------------------------
  group('enum value coverage', () {
    test('all AppThemeMode values round-trip correctly', () async {
      for (final mode in AppThemeMode.values) {
        await initRepo({'settings.themeMode': mode.name});
        final settings = await getSettings();
        expect(settings.themeMode, mode, reason: 'Failed for ${mode.name}');
      }
    });

    test('all AppBrightness values round-trip correctly', () async {
      for (final brightness in AppBrightness.values) {
        await initRepo({'settings.brightness': brightness.name});
        final settings = await getSettings();
        expect(
          settings.brightness,
          brightness,
          reason: 'Failed for ${brightness.name}',
        );
      }
    });

    test('all PreferredProtocol values round-trip correctly', () async {
      for (final protocol in PreferredProtocol.values) {
        await initRepo({'settings.preferredProtocol': protocol.name});
        final settings = await getSettings();
        expect(
          settings.preferredProtocol,
          protocol,
          reason: 'Failed for ${protocol.name}',
        );
      }
    });

    test('all DnsProvider values round-trip correctly', () async {
      for (final dns in DnsProvider.values) {
        await initRepo({'settings.dnsProvider': dns.name});
        final settings = await getSettings();
        expect(settings.dnsProvider, dns, reason: 'Failed for ${dns.name}');
      }
    });

    test('all MtuMode values round-trip correctly', () async {
      for (final mtu in MtuMode.values) {
        await initRepo({'settings.mtuMode': mtu.name});
        final settings = await getSettings();
        expect(settings.mtuMode, mtu, reason: 'Failed for ${mtu.name}');
      }
    });

    test('all LogLevel values round-trip correctly', () async {
      for (final level in LogLevel.values) {
        await initRepo({'settings.logLevel': level.name});
        final settings = await getSettings();
        expect(settings.logLevel, level, reason: 'Failed for ${level.name}');
      }
    });
  });
}

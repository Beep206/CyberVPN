import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/routing_profile.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AppSettings enums', () {
    test('AppThemeMode has expected values', () {
      expect(AppThemeMode.values, hasLength(2));
      expect(AppThemeMode.values, contains(AppThemeMode.materialYou));
      expect(AppThemeMode.values, contains(AppThemeMode.cyberpunk));
    });

    test('AppBrightness has expected values', () {
      expect(AppBrightness.values, hasLength(3));
      expect(AppBrightness.values, contains(AppBrightness.system));
      expect(AppBrightness.values, contains(AppBrightness.light));
      expect(AppBrightness.values, contains(AppBrightness.dark));
    });

    test('PreferredProtocol has expected values', () {
      expect(PreferredProtocol.values, hasLength(4));
      expect(PreferredProtocol.values, contains(PreferredProtocol.auto));
      expect(
        PreferredProtocol.values,
        contains(PreferredProtocol.vlessReality),
      );
      expect(PreferredProtocol.values, contains(PreferredProtocol.vlessXhttp));
      expect(PreferredProtocol.values, contains(PreferredProtocol.vlessWsTls));
    });

    test('DnsProvider has expected values', () {
      expect(DnsProvider.values, hasLength(5));
      expect(DnsProvider.values, contains(DnsProvider.system));
      expect(DnsProvider.values, contains(DnsProvider.cloudflare));
      expect(DnsProvider.values, contains(DnsProvider.google));
      expect(DnsProvider.values, contains(DnsProvider.quad9));
      expect(DnsProvider.values, contains(DnsProvider.custom));
    });

    test('LogLevel has expected values', () {
      expect(LogLevel.values, hasLength(6));
      expect(LogLevel.values, contains(LogLevel.auto));
      expect(LogLevel.values, contains(LogLevel.debug));
      expect(LogLevel.values, contains(LogLevel.info));
      expect(LogLevel.values, contains(LogLevel.warning));
      expect(LogLevel.values, contains(LogLevel.error));
      expect(LogLevel.values, contains(LogLevel.none));
    });

    test('PerAppProxyMode has expected values', () {
      expect(PerAppProxyMode.values, hasLength(3));
      expect(PerAppProxyMode.values, contains(PerAppProxyMode.off));
      expect(PerAppProxyMode.values, contains(PerAppProxyMode.proxySelected));
      expect(PerAppProxyMode.values, contains(PerAppProxyMode.bypassSelected));
    });

    test('PreferredIpType has expected values', () {
      expect(PreferredIpType.values, hasLength(3));
      expect(PreferredIpType.values, contains(PreferredIpType.auto));
      expect(PreferredIpType.values, contains(PreferredIpType.ipv4));
      expect(PreferredIpType.values, contains(PreferredIpType.ipv6));
    });

    test('PingMode has expected values', () {
      expect(PingMode.values, hasLength(5));
      expect(PingMode.values, contains(PingMode.tcp));
      expect(PingMode.values, contains(PingMode.realDelay));
      expect(PingMode.values, contains(PingMode.proxyGet));
      expect(PingMode.values, contains(PingMode.proxyHead));
      expect(PingMode.values, contains(PingMode.icmp));
    });

    test('phase 8 enums expose expected values', () {
      expect(VpnRunMode.values, containsAll(VpnRunMode.values));
      expect(
        SubscriptionConnectStrategy.values,
        containsAll(SubscriptionConnectStrategy.values),
      );
      expect(
        SubscriptionUserAgentMode.values,
        containsAll(SubscriptionUserAgentMode.values),
      );
      expect(
        SubscriptionSortMode.values,
        containsAll(SubscriptionSortMode.values),
      );
      expect(PingResultMode.values, containsAll(PingResultMode.values));
    });
  });

  group('AppSettings', () {
    late AppSettings settings;

    setUp(() {
      settings = const AppSettings();
    });

    test('creates entity with sensible defaults', () {
      expect(settings.themeMode, AppThemeMode.cyberpunk);
      expect(settings.brightness, AppBrightness.system);
      expect(settings.dynamicColor, false);
      expect(settings.preferredProtocol, PreferredProtocol.auto);
      expect(settings.autoConnectOnLaunch, false);
      expect(settings.autoConnectUntrustedWifi, false);
      expect(settings.killSwitch, false);
      expect(settings.routingEnabled, false);
      expect(settings.routingProfiles, isEmpty);
      expect(settings.activeRoutingProfileId, isNull);
      expect(settings.bypassSubnets, isEmpty);
      expect(settings.excludedRouteEntries, isEmpty);
      expect(settings.perAppProxyMode, PerAppProxyMode.off);
      expect(settings.perAppProxyAppIds, isEmpty);
      expect(settings.dnsProvider, DnsProvider.system);
      expect(settings.customDns, isNull);
      expect(settings.useLocalDns, isFalse);
      expect(settings.localDnsPort, 1053);
      expect(settings.useDnsFromJson, isFalse);
      expect(settings.fragmentationEnabled, false);
      expect(settings.muxEnabled, false);
      expect(settings.preferredIpType, PreferredIpType.auto);
      expect(settings.sniffingEnabled, isFalse);
      expect(settings.vpnRunMode, VpnRunMode.vpn);
      expect(settings.serverAddressResolveEnabled, isFalse);
      expect(settings.serverAddressResolveDohUrl, isNull);
      expect(settings.serverAddressResolveDnsIp, isNull);
      expect(settings.pingMode, PingMode.tcp);
      expect(settings.pingTestUrl, 'https://google.com/generate_204');
      expect(settings.pingResultMode, PingResultMode.time);
      expect(settings.subscriptionAutoUpdateEnabled, isTrue);
      expect(settings.subscriptionAutoUpdateIntervalHours, 24);
      expect(settings.subscriptionAutoUpdateOnOpen, isTrue);
      expect(settings.subscriptionPingOnOpenEnabled, isFalse);
      expect(
        settings.subscriptionConnectStrategy,
        SubscriptionConnectStrategy.lastUsed,
      );
      expect(settings.preventDuplicateImports, isTrue);
      expect(settings.collapseSubscriptions, isTrue);
      expect(settings.subscriptionNoFilter, isFalse);
      expect(
        settings.subscriptionUserAgentMode,
        SubscriptionUserAgentMode.appDefault,
      );
      expect(settings.subscriptionUserAgentValue, isNull);
      expect(settings.subscriptionSortMode, SubscriptionSortMode.none);
      expect(settings.allowLanConnections, isFalse);
      expect(settings.appAutoStart, isFalse);
      expect(settings.locale, 'en');
      expect(settings.notificationConnection, true);
      expect(settings.notificationExpiry, true);
      expect(settings.notificationPromotional, false);
      expect(settings.notificationReferral, true);
      expect(settings.clipboardAutoDetect, false);
      expect(settings.logLevel, LogLevel.info);
    });

    test('creates entity with all fields specified', () {
      const routingProfile = RoutingProfile(
        id: 'profile-1',
        name: 'Default',
        rules: [
          RoutingRule(
            id: 'rule-1',
            matchType: RoutingRuleMatchType.domainSuffix,
            value: 'youtube.com',
            action: RoutingRuleAction.direct,
          ),
        ],
      );

      const custom = AppSettings(
        themeMode: AppThemeMode.materialYou,
        brightness: AppBrightness.dark,
        dynamicColor: true,
        preferredProtocol: PreferredProtocol.vlessReality,
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
        perAppProxyMode: PerAppProxyMode.proxySelected,
        perAppProxyAppIds: ['com.example.browser'],
        dnsProvider: DnsProvider.custom,
        customDns: '1.1.1.1',
        useLocalDns: true,
        localDnsPort: 1054,
        useDnsFromJson: true,
        fragmentationEnabled: true,
        muxEnabled: true,
        preferredIpType: PreferredIpType.ipv6,
        sniffingEnabled: true,
        vpnRunMode: VpnRunMode.proxyOnly,
        serverAddressResolveEnabled: true,
        serverAddressResolveDohUrl: 'https://dns.example/dns-query',
        serverAddressResolveDnsIp: '1.1.1.1',
        pingMode: PingMode.realDelay,
        pingTestUrl: 'https://cp.cloudflare.com/generate_204',
        pingResultMode: PingResultMode.icon,
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
        locale: 'ru',
        notificationConnection: false,
        notificationExpiry: false,
        notificationPromotional: true,
        notificationReferral: false,
        clipboardAutoDetect: false,
        logLevel: LogLevel.debug,
      );

      expect(custom.themeMode, AppThemeMode.materialYou);
      expect(custom.brightness, AppBrightness.dark);
      expect(custom.dynamicColor, true);
      expect(custom.preferredProtocol, PreferredProtocol.vlessReality);
      expect(custom.autoConnectOnLaunch, true);
      expect(custom.autoConnectUntrustedWifi, true);
      expect(custom.killSwitch, true);
      expect(custom.routingEnabled, true);
      expect(custom.routingProfiles, [routingProfile]);
      expect(custom.activeRoutingProfileId, 'profile-1');
      expect(custom.bypassSubnets, ['10.0.0.0/8']);
      expect(custom.excludedRouteEntries, hasLength(1));
      expect(custom.perAppProxyMode, PerAppProxyMode.proxySelected);
      expect(custom.perAppProxyAppIds, ['com.example.browser']);
      expect(custom.dnsProvider, DnsProvider.custom);
      expect(custom.customDns, '1.1.1.1');
      expect(custom.useLocalDns, isTrue);
      expect(custom.localDnsPort, 1054);
      expect(custom.useDnsFromJson, isTrue);
      expect(custom.fragmentationEnabled, true);
      expect(custom.muxEnabled, true);
      expect(custom.preferredIpType, PreferredIpType.ipv6);
      expect(custom.sniffingEnabled, isTrue);
      expect(custom.vpnRunMode, VpnRunMode.proxyOnly);
      expect(custom.serverAddressResolveEnabled, isTrue);
      expect(
        custom.serverAddressResolveDohUrl,
        'https://dns.example/dns-query',
      );
      expect(custom.serverAddressResolveDnsIp, '1.1.1.1');
      expect(custom.pingMode, PingMode.realDelay);
      expect(custom.pingTestUrl, 'https://cp.cloudflare.com/generate_204');
      expect(custom.pingResultMode, PingResultMode.icon);
      expect(custom.subscriptionAutoUpdateEnabled, isFalse);
      expect(custom.subscriptionAutoUpdateIntervalHours, 12);
      expect(custom.subscriptionUpdateNotificationsEnabled, isTrue);
      expect(custom.subscriptionAutoUpdateOnOpen, isFalse);
      expect(custom.subscriptionPingOnOpenEnabled, isTrue);
      expect(
        custom.subscriptionConnectStrategy,
        SubscriptionConnectStrategy.random,
      );
      expect(custom.preventDuplicateImports, isFalse);
      expect(custom.collapseSubscriptions, isFalse);
      expect(custom.subscriptionNoFilter, isTrue);
      expect(
        custom.subscriptionUserAgentMode,
        SubscriptionUserAgentMode.custom,
      );
      expect(custom.subscriptionUserAgentValue, 'CyberVPN-Test/8.0');
      expect(custom.subscriptionSortMode, SubscriptionSortMode.alphabetical);
      expect(custom.allowLanConnections, isTrue);
      expect(custom.appAutoStart, isTrue);
      expect(custom.locale, 'ru');
      expect(custom.notificationConnection, false);
      expect(custom.notificationExpiry, false);
      expect(custom.notificationPromotional, true);
      expect(custom.notificationReferral, false);
      expect(custom.clipboardAutoDetect, false);
      expect(custom.logLevel, LogLevel.debug);
    });

    test('copyWith preserves unchanged fields', () {
      final updated = settings.copyWith(themeMode: AppThemeMode.materialYou);

      expect(updated.themeMode, AppThemeMode.materialYou);
      // All other fields remain at defaults
      expect(updated.brightness, settings.brightness);
      expect(updated.dynamicColor, settings.dynamicColor);
      expect(updated.preferredProtocol, settings.preferredProtocol);
      expect(updated.autoConnectOnLaunch, settings.autoConnectOnLaunch);
      expect(
        updated.autoConnectUntrustedWifi,
        settings.autoConnectUntrustedWifi,
      );
      expect(updated.killSwitch, settings.killSwitch);
      expect(updated.routingEnabled, settings.routingEnabled);
      expect(updated.routingProfiles, settings.routingProfiles);
      expect(updated.activeRoutingProfileId, settings.activeRoutingProfileId);
      expect(updated.bypassSubnets, settings.bypassSubnets);
      expect(updated.excludedRouteEntries, settings.excludedRouteEntries);
      expect(updated.perAppProxyMode, settings.perAppProxyMode);
      expect(updated.perAppProxyAppIds, settings.perAppProxyAppIds);
      expect(updated.dnsProvider, settings.dnsProvider);
      expect(updated.customDns, settings.customDns);
      expect(updated.useLocalDns, settings.useLocalDns);
      expect(updated.localDnsPort, settings.localDnsPort);
      expect(updated.useDnsFromJson, settings.useDnsFromJson);
      expect(updated.fragmentationEnabled, settings.fragmentationEnabled);
      expect(updated.muxEnabled, settings.muxEnabled);
      expect(updated.preferredIpType, settings.preferredIpType);
      expect(updated.sniffingEnabled, settings.sniffingEnabled);
      expect(updated.vpnRunMode, settings.vpnRunMode);
      expect(updated.pingMode, settings.pingMode);
      expect(updated.pingTestUrl, settings.pingTestUrl);
      expect(updated.pingResultMode, settings.pingResultMode);
      expect(updated.locale, settings.locale);
      expect(
        updated.subscriptionAutoUpdateEnabled,
        settings.subscriptionAutoUpdateEnabled,
      );
      expect(updated.allowLanConnections, settings.allowLanConnections);
      expect(updated.appAutoStart, settings.appAutoStart);
      expect(updated.notificationConnection, settings.notificationConnection);
      expect(updated.notificationExpiry, settings.notificationExpiry);
      expect(updated.notificationPromotional, settings.notificationPromotional);
      expect(updated.notificationReferral, settings.notificationReferral);
      expect(updated.clipboardAutoDetect, settings.clipboardAutoDetect);
      expect(updated.logLevel, settings.logLevel);
    });

    test('copyWith updates multiple fields', () {
      final updated = settings.copyWith(
        killSwitch: true,
        locale: 'de',
        logLevel: LogLevel.error,
        preferredIpType: PreferredIpType.ipv4,
        useLocalDns: true,
        appAutoStart: true,
      );

      expect(updated.killSwitch, true);
      expect(updated.locale, 'de');
      expect(updated.logLevel, LogLevel.error);
      expect(updated.preferredIpType, PreferredIpType.ipv4);
      expect(updated.useLocalDns, isTrue);
      expect(updated.appAutoStart, isTrue);
      expect(updated.themeMode, settings.themeMode);
    });

    test('equality for identical settings', () {
      const settings1 = AppSettings();
      const settings2 = AppSettings();

      expect(settings1, equals(settings2));
      expect(settings1.hashCode, equals(settings2.hashCode));
    });

    test('inequality for different settings', () {
      const settings1 = AppSettings();
      const settings2 = AppSettings(themeMode: AppThemeMode.materialYou);

      expect(settings1, isNot(equals(settings2)));
    });

    test('toString returns meaningful representation', () {
      final str = settings.toString();
      expect(str, contains('AppSettings'));
    });
  });
}

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/excluded_route_entry.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/routing_profile.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/services/vpn_runtime_capabilities.dart';
import 'package:cybervpn_mobile/features/vpn/domain/services/vpn_runtime_config_builder.dart';

void main() {
  const builder = VpnRuntimeConfigBuilder();
  const supportedCapabilities = VpnRuntimeCapabilities(
    supportsPerAppProxy: true,
    supportsExcludedRoutes: true,
    supportsRoutingRules: true,
    supportsMux: true,
    supportsFragmentation: true,
    supportsPreferredIpType: true,
    supportsDnsOverride: true,
    supportsManualMtu: true,
    supportsSniffing: true,
    supportsProxyOnlyMode: true,
  );

  VpnConfigEntity baseConfig({required String configData}) => VpnConfigEntity(
    id: 'cfg-1',
    name: 'Primary',
    serverAddress: '1.2.3.4',
    port: 443,
    protocol: VpnProtocol.vless,
    configData: configData,
  );

  group('VpnRuntimeConfigBuilder', () {
    test('keeps raw URI config when no JSON mutations are required', () {
      const rawUri = 'vless://uuid@example.com:443?security=tls&type=tcp#Test';

      final result = builder.build(
        sourceConfig: baseConfig(configData: rawUri),
        vpnSettings: const VpnSettings(logLevel: LogLevel.error),
        capabilities: supportedCapabilities,
        blockedApps: const ['com.example.blocked'],
      );

      expect(result.config.configData, rawUri);
      expect(result.config.blockedApps, const ['com.example.blocked']);
      expect(result.config.bypassSubnets, isEmpty);
      expect(result.config.dnsServers, isNull);
      expect(result.appliedSettings, isEmpty);
    });

    test('applies runtime log level from app settings', () {
      const rawUri = 'vless://uuid@example.com:443?security=tls&type=tcp#Test';

      final result = builder.build(
        sourceConfig: baseConfig(configData: rawUri),
        vpnSettings: const VpnSettings(logLevel: LogLevel.debug),
        capabilities: supportedCapabilities,
        blockedApps: const [],
      );

      final runtimeJson =
          jsonDecode(result.config.configData) as Map<String, dynamic>;
      final logConfig = runtimeJson['log'] as Map<String, dynamic>;

      expect(logConfig['loglevel'], 'debug');
      expect(logConfig['dnsLog'], isTrue);
      expect(result.appliedSettings, contains('log-level:debug'));
    });

    test('applies routing, DNS, mux, fragmentation, IP type and MTU', () {
      final sourceJson = jsonEncode({
        'inbounds': [
          {
            'tag': 'in_proxy',
            'port': 10807,
            'protocol': 'socks',
            'listen': '127.0.0.1',
            'settings': {'auth': 'noauth', 'udp': true},
          },
        ],
        'outbounds': [
          {
            'tag': 'proxy',
            'protocol': 'vless',
            'settings': {
              'vnext': [
                {
                  'address': '1.2.3.4',
                  'port': 443,
                  'users': [
                    {'id': 'uuid', 'encryption': 'none'},
                  ],
                },
              ],
            },
            'streamSettings': {
              'network': 'ws',
              'security': 'tls',
              'wsSettings': {'path': '/'},
              'tlsSettings': {'serverName': 'example.com'},
            },
            'mux': {'enabled': false, 'concurrency': 8},
          },
          {
            'tag': 'direct',
            'protocol': 'freedom',
            'settings': {'domainStrategy': 'AsIs'},
          },
          {
            'tag': 'blackhole',
            'protocol': 'blackhole',
            'settings': <String, dynamic>{},
          },
        ],
        'routing': {
          'domainStrategy': 'AsIs',
          'rules': <Map<String, dynamic>>[],
        },
        'dns': {
          'servers': ['8.8.8.8', '1.1.1.1'],
        },
      });

      const vpnSettings = VpnSettings(
        dnsProvider: DnsProvider.cloudflare,
        routingEnabled: true,
        routingProfiles: [
          RoutingProfile(
            id: 'profile-1',
            name: 'Default',
            rules: [
              RoutingRule(
                id: 'rule-domain',
                matchType: RoutingRuleMatchType.domainSuffix,
                value: 'example.com',
                action: RoutingRuleAction.direct,
              ),
              RoutingRule(
                id: 'rule-ip',
                matchType: RoutingRuleMatchType.ipCidr,
                value: '10.0.0.0/8',
                action: RoutingRuleAction.block,
              ),
            ],
          ),
        ],
        activeRoutingProfileId: 'profile-1',
        bypassSubnets: ['10.0.0.0/8'],
        excludedRouteEntries: [
          ExcludedRouteEntry(
            rawValue: '10.0.0.0/8',
            targetType: ExcludedRouteTargetType.ipv4Cidr,
          ),
          ExcludedRouteEntry(
            rawValue: '2001:db8::1',
            targetType: ExcludedRouteTargetType.ipv6Address,
          ),
        ],
        fragmentationEnabled: true,
        muxEnabled: true,
        preferredIpType: PreferredIpType.ipv4,
        mtuMode: MtuMode.manual,
        mtuValue: 1400,
        sniffingEnabled: true,
        vpnRunMode: VpnRunMode.proxyOnly,
      );

      final result = builder.build(
        sourceConfig: baseConfig(configData: sourceJson),
        vpnSettings: vpnSettings,
        capabilities: supportedCapabilities,
        blockedApps: const ['com.example.blocked'],
      );

      final runtimeJson =
          jsonDecode(result.config.configData) as Map<String, dynamic>;
      final outbounds = (runtimeJson['outbounds'] as List<dynamic>)
          .cast<Map<String, dynamic>>();
      final proxyOutbound = outbounds.firstWhere(
        (outbound) => outbound['tag'] == 'proxy',
      );
      final directOutbound = outbounds.firstWhere(
        (outbound) => outbound['tag'] == 'direct',
      );
      final fragmentOutbound = outbounds.firstWhere(
        (outbound) => outbound['tag'] == 'fragment',
      );
      final routing = runtimeJson['routing'] as Map<String, dynamic>;
      final dns = runtimeJson['dns'] as Map<String, dynamic>;
      final rules = (routing['rules'] as List<dynamic>)
          .cast<Map<String, dynamic>>();

      expect(result.config.blockedApps, const ['com.example.blocked']);
      expect(result.config.bypassSubnets, const [
        '10.0.0.0/8',
        '2001:db8::1/128',
      ]);
      expect(result.config.dnsServers, const ['1.1.1.1', '1.0.0.1']);
      expect(result.config.mtu, 1400);
      expect(result.config.proxyOnly, isTrue);
      expect(
        result.appliedSettings,
        containsAll(<String>[
          'proxy-only',
          'dns:override',
          'routing:profile-1',
          'mux',
          'preferred-ip:ipv4',
          'fragmentation',
          'sniffing',
        ]),
      );

      expect(dns['queryStrategy'], 'UseIPv4');
      expect((dns['servers'] as List<dynamic>).cast<String>(), const [
        '1.1.1.1',
        '1.0.0.1',
      ]);
      expect(proxyOutbound['targetStrategy'], 'UseIPv4');
      expect(proxyOutbound['mux'], {'enabled': true, 'concurrency': 8});
      expect(
        ((runtimeJson['inbounds'] as List<dynamic>).first
            as Map<String, dynamic>)['sniffing'],
        {
          'enabled': true,
          'destOverride': ['http', 'tls', 'quic'],
          'metadataOnly': false,
        },
      );
      expect(
        ((proxyOutbound['streamSettings'] as Map<String, dynamic>)['sockopt']
            as Map<String, dynamic>)['dialerProxy'],
        'fragment',
      );
      expect(
        ((directOutbound['settings']
            as Map<String, dynamic>)['domainStrategy']),
        'UseIPv4',
      );
      expect(fragmentOutbound['protocol'], 'freedom');
      expect(routing['domainStrategy'], 'IPIfNonMatch');
      expect(rules, hasLength(2));
      expect(rules[0]['domain'], const ['domain:example.com']);
      expect(rules[0]['outboundTag'], 'direct');
      expect(rules[1]['ip'], const ['10.0.0.0/8']);
      expect(rules[1]['outboundTag'], 'blackhole');
    });

    test('preserves dns from full JSON when useDnsFromJson is enabled', () {
      final sourceJson = jsonEncode({
        'inbounds': [
          {
            'tag': 'in_proxy',
            'port': 10807,
            'protocol': 'socks',
            'listen': '127.0.0.1',
            'settings': {'auth': 'noauth', 'udp': true},
          },
        ],
        'outbounds': [
          {
            'tag': 'proxy',
            'protocol': 'vless',
            'settings': {
              'vnext': [
                {
                  'address': '1.2.3.4',
                  'port': 443,
                  'users': [
                    {'id': 'uuid', 'encryption': 'none'},
                  ],
                },
              ],
            },
          },
        ],
        'dns': {
          'servers': ['77.88.8.8', '77.88.8.1'],
        },
      });

      final result = builder.build(
        sourceConfig: baseConfig(configData: sourceJson),
        vpnSettings: const VpnSettings(
          useDnsFromJson: true,
          dnsProvider: DnsProvider.cloudflare,
        ),
        capabilities: supportedCapabilities,
        blockedApps: const <String>[],
      );

      final runtimeJson =
          jsonDecode(result.config.configData) as Map<String, dynamic>;
      final dns = runtimeJson['dns'] as Map<String, dynamic>;

      expect(result.config.dnsServers, isNull);
      expect(result.appliedSettings, contains('dns:json'));
      expect((dns['servers'] as List<dynamic>).cast<String>(), const [
        '77.88.8.8',
        '77.88.8.1',
      ]);
    });

    test('rebuilds a full Xray config from stored profile metadata JSON', () {
      final partialConfig = jsonEncode({
        'uuid': 'uuid',
        'transport': {'type': 'ws', 'path': '/ws', 'host': 'edge.example.com'},
        'tls': {'security': 'tls', 'sni': 'edge.example.com'},
        'params': {'encryption': 'none'},
      });

      final result = builder.build(
        sourceConfig: baseConfig(configData: partialConfig),
        vpnSettings: const VpnSettings(),
        capabilities: supportedCapabilities,
        blockedApps: const <String>[],
      );

      final runtimeJson =
          jsonDecode(result.config.configData) as Map<String, dynamic>;
      final outbounds = (runtimeJson['outbounds'] as List<dynamic>)
          .cast<Map<String, dynamic>>();
      final proxyOutbound = outbounds.firstWhere(
        (outbound) => outbound['tag'] == 'proxy',
      );

      expect(runtimeJson['inbounds'], isA<List<dynamic>>());
      expect(proxyOutbound['protocol'], 'vless');
      expect(
        (((proxyOutbound['settings'] as Map<String, dynamic>)['vnext']
                    as List<dynamic>)
                .first
            as Map<String, dynamic>)['address'],
        '1.2.3.4',
      );
    });

    test(
      'drops unsupported runtime settings with explicit skipped reasons',
      () {
        const unsupported = VpnRuntimeCapabilities.unsupported();

        final result = builder.build(
          sourceConfig: baseConfig(
            configData: jsonEncode({
              'inbounds': <Map<String, dynamic>>[],
              'outbounds': <Map<String, dynamic>>[],
            }),
          ),
          vpnSettings: const VpnSettings(
            dnsProvider: DnsProvider.cloudflare,
            routingEnabled: true,
            bypassSubnets: ['10.0.0.0/8'],
            fragmentationEnabled: true,
            muxEnabled: true,
            preferredIpType: PreferredIpType.ipv6,
            mtuMode: MtuMode.manual,
            mtuValue: 1400,
          ),
          capabilities: unsupported,
          blockedApps: const <String>[],
        );

        expect(result.config.bypassSubnets, isEmpty);
        expect(result.config.dnsServers, isNull);
        expect(result.config.mtu, isNull);
        expect(
          result.skippedSettings.keys,
          containsAll(<String>[
            'dns',
            'routing',
            'excludedRoutes',
            'fragmentation',
            'mux',
            'preferredIpType',
            'mtu',
          ]),
        );
      },
    );
  });
}

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/vpn/domain/entities/vpn_config_entity.dart';
import 'package:cybervpn_mobile/features/vpn/domain/services/vpn_runtime_capabilities.dart';
import 'package:cybervpn_mobile/features/vpn/domain/services/vpn_server_address_resolver.dart';

void main() {
  VpnConfigEntity baseConfig({
    String configData =
        'vless://uuid@example.com:443?security=tls&type=tcp#Test',
  }) => VpnConfigEntity(
    id: 'cfg-1',
    name: 'Primary',
    serverAddress: 'example.com',
    port: 443,
    protocol: VpnProtocol.vless,
    configData: configData,
  );

  const capabilities = VpnRuntimeCapabilities(
    supportsPerAppProxy: true,
    supportsExcludedRoutes: true,
    supportsRoutingRules: true,
    supportsMux: true,
    supportsFragmentation: true,
    supportsPreferredIpType: true,
    supportsDnsOverride: true,
    supportsManualMtu: true,
    supportsServerAddressResolve: true,
  );

  group('VpnServerAddressResolver', () {
    test('returns source config unchanged when resolve is disabled', () async {
      final resolver = VpnServerAddressResolver(
        hostLookup: (host, {type = InternetAddressType.any}) async => [
          InternetAddress('203.0.113.10'),
        ],
      );

      final result = await resolver.resolve(
        sourceConfig: baseConfig(),
        vpnSettings: const VpnSettings(),
        capabilities: capabilities,
      );

      expect(result.config, baseConfig());
      expect(result.selectedAddress, isNull);
    });

    test('uses DoH candidates and selects the fastest address', () async {
      String? capturedDnsIp;
      final resolver = VpnServerAddressResolver(
        dohLookup:
            ({
              required dohUrl,
              required host,
              required type,
              String? dnsIp,
            }) async {
              capturedDnsIp = dnsIp;
              return [
                InternetAddress('203.0.113.10'),
                InternetAddress('203.0.113.20'),
              ];
            },
        hostLookup: (host, {type = InternetAddressType.any}) async =>
            throw StateError('system lookup should not run'),
        tcpProbe:
            (
              address,
              port, {
              timeout = const Duration(milliseconds: 1200),
            }) async {
              return address == '203.0.113.20'
                  ? const Duration(milliseconds: 40)
                  : const Duration(milliseconds: 120);
            },
      );

      final result = await resolver.resolve(
        sourceConfig: baseConfig(),
        vpnSettings: const VpnSettings(
          serverAddressResolveEnabled: true,
          serverAddressResolveDohUrl: 'https://dns.google/resolve',
          serverAddressResolveDnsIp: '8.8.8.8',
        ),
        capabilities: capabilities,
      );

      expect(capturedDnsIp, '8.8.8.8');
      expect(result.selectedAddress, '203.0.113.20');
      expect(
        result.appliedSettings,
        containsAll(['server-resolve:doh', 'server-resolve:selected']),
      );
      expect(result.candidateAddresses, ['203.0.113.10', '203.0.113.20']);

      final runtimeJson =
          jsonDecode(result.config.configData) as Map<String, dynamic>;
      final outbounds = (runtimeJson['outbounds'] as List<dynamic>)
          .cast<Map<String, dynamic>>();
      final proxyOutbound = outbounds.firstWhere(
        (outbound) => outbound['tag'] == 'proxy',
      );

      expect(result.config.serverAddress, '203.0.113.20');
      expect(
        (((proxyOutbound['settings'] as Map<String, dynamic>)['vnext']
                    as List<dynamic>)
                .first
            as Map<String, dynamic>)['address'],
        '203.0.113.20',
      );
    });

    test(
      'falls back to system lookup and respects preferred IPv6 type',
      () async {
        InternetAddressType? capturedType;
        final resolver = VpnServerAddressResolver(
          hostLookup: (host, {type = InternetAddressType.any}) async {
            capturedType = type;
            return [InternetAddress('2001:db8::5')];
          },
          tcpProbe:
              (
                address,
                port, {
                timeout = const Duration(milliseconds: 1200),
              }) async => const Duration(milliseconds: 50),
        );

        final result = await resolver.resolve(
          sourceConfig: baseConfig(configData: ''),
          vpnSettings: const VpnSettings(
            serverAddressResolveEnabled: true,
            preferredIpType: PreferredIpType.ipv6,
          ),
          capabilities: capabilities,
        );

        expect(capturedType, InternetAddressType.IPv6);
        expect(result.selectedAddress, '2001:db8::5');
        expect(result.config.serverAddress, '2001:db8::5');
        expect(result.config.configData, isEmpty);
        expect(result.appliedSettings, contains('server-resolve:system'));
      },
    );
  });
}

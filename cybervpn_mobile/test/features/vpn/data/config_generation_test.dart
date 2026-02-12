import 'dart:convert';

import 'package:cybervpn_mobile/core/constants/vpn_constants.dart';
import 'package:cybervpn_mobile/features/vpn/data/datasources/xray_config_generator.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  // ---------------------------------------------------------------------------
  // VLESS config generation
  // ---------------------------------------------------------------------------

  group('XrayConfigGenerator - VLESS', () {
    test('generates valid JSON with default parameters', () {
      final json = XrayConfigGenerator.generateVlessConfig(
        address: '203.0.113.1',
        port: 443,
        uuid: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;

      expect(config, contains('outbounds'));
      expect(config, contains('dns'));

      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      expect(outbound['protocol'], 'vless');

      final settings = outbound['settings'] as Map<String, dynamic>;
      final vnext = (settings['vnext'] as List).first
          as Map<String, dynamic>;
      expect(vnext['address'], '203.0.113.1');
      expect(vnext['port'], 443);

      final user =
          (vnext['users'] as List).first as Map<String, dynamic>;
      expect(user['id'], 'a1b2c3d4-e5f6-7890-abcd-ef1234567890');
      expect(user['encryption'], 'none');
    });

    test('includes TLS settings when security is tls', () {
      final json = XrayConfigGenerator.generateVlessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
        security: 'tls',
        sni: 'cdn.example.com',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      final stream = outbound['streamSettings'] as Map<String, dynamic>;
      final tlsSettings = stream['tlsSettings'] as Map<String, dynamic>;

      expect(stream['security'], 'tls');
      expect(tlsSettings['serverName'], 'cdn.example.com');
    });

    test('uses address as SNI when sni is null', () {
      final json = XrayConfigGenerator.generateVlessConfig(
        address: 'my-server.com',
        port: 443,
        uuid: 'test-uuid',
        security: 'tls',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      final stream = outbound['streamSettings'] as Map<String, dynamic>;
      final tlsSettings = stream['tlsSettings'] as Map<String, dynamic>;

      expect(tlsSettings['serverName'], 'my-server.com');
    });

    test('includes WebSocket settings when network is ws', () {
      final json = XrayConfigGenerator.generateVlessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
        network: 'ws',
        path: '/ws-path',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      final stream = outbound['streamSettings'] as Map<String, dynamic>;
      final wsSettings = stream['wsSettings'] as Map<String, dynamic>;

      expect(stream['network'], 'ws');
      expect(wsSettings['path'], '/ws-path');
    });

    test('uses default path "/" when path is null with ws network', () {
      final json = XrayConfigGenerator.generateVlessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
        network: 'ws',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      final stream = outbound['streamSettings'] as Map<String, dynamic>;
      final wsSettings = stream['wsSettings'] as Map<String, dynamic>;

      expect(wsSettings['path'], '/');
    });

    test('omits TLS settings when security is not tls', () {
      final json = XrayConfigGenerator.generateVlessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
        security: 'none',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      final stream = outbound['streamSettings'] as Map<String, dynamic>;

      expect(stream.containsKey('tlsSettings'), isFalse);
    });

    test('DNS servers match VpnConstants defaults', () {
      final json = XrayConfigGenerator.generateVlessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final dns = config['dns'] as Map<String, dynamic>;
      final servers = (dns['servers'] as List).cast<String>();

      expect(servers, equals(VpnConstants.defaultDnsServers));
      expect(servers, contains('1.1.1.1'));
      expect(servers, contains('8.8.8.8'));
    });

    test('generates valid JSON for non-standard port', () {
      final json = XrayConfigGenerator.generateVlessConfig(
        address: '10.0.0.1',
        port: 8443,
        uuid: 'test-uuid',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      final settings = outbound['settings'] as Map<String, dynamic>;
      final vnext =
          (settings['vnext'] as List)[0] as Map<String, dynamic>;

      expect(vnext['port'], 8443);
    });
  });

  // ---------------------------------------------------------------------------
  // VMess config generation
  // ---------------------------------------------------------------------------

  group('XrayConfigGenerator - VMess', () {
    test('generates valid JSON with default parameters', () {
      final json = XrayConfigGenerator.generateVmessConfig(
        address: '203.0.113.2',
        port: 443,
        uuid: 'b1c2d3e4-f5g6-7890-abcd-ef1234567890',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;

      expect(config, contains('outbounds'));
      expect(config, contains('dns'));

      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      expect(outbound['protocol'], 'vmess');

      final vmessSettings = outbound['settings'] as Map<String, dynamic>;
      final vnext = (vmessSettings['vnext'] as List).first
          as Map<String, dynamic>;
      expect(vnext['address'], '203.0.113.2');
      expect(vnext['port'], 443);

      final user =
          (vnext['users'] as List).first as Map<String, dynamic>;
      expect(user['id'], 'b1c2d3e4-f5g6-7890-abcd-ef1234567890');
      expect(user['alterId'], 0);
      expect(user['security'], 'auto');
    });

    test('includes custom alterId and security', () {
      final json = XrayConfigGenerator.generateVmessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
        alterId: 64,
        security: 'aes-128-gcm',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      final settings = outbound['settings'] as Map<String, dynamic>;
      final vnext =
          (settings['vnext'] as List)[0] as Map<String, dynamic>;
      final user = (vnext['users'] as List).first as Map<String, dynamic>;

      expect(user['alterId'], 64);
      expect(user['security'], 'aes-128-gcm');
    });

    test('includes WebSocket settings when network is ws', () {
      final json = XrayConfigGenerator.generateVmessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
        network: 'ws',
        path: '/vmess-ws',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      final stream = outbound['streamSettings'] as Map<String, dynamic>;

      final vmessWsSettings = stream['wsSettings'] as Map<String, dynamic>;
      expect(stream['network'], 'ws');
      expect(vmessWsSettings['path'], '/vmess-ws');
    });

    test('uses default path "/" when path is null with ws', () {
      final json = XrayConfigGenerator.generateVmessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
        network: 'ws',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      final stream = outbound['streamSettings'] as Map<String, dynamic>;
      final vmessWsDefSettings = stream['wsSettings'] as Map<String, dynamic>;

      expect(vmessWsDefSettings['path'], '/');
    });

    test('omits wsSettings when network is not ws', () {
      final json = XrayConfigGenerator.generateVmessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
        network: 'tcp',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final outbound =
          (config['outbounds'] as List).first as Map<String, dynamic>;
      final stream = outbound['streamSettings'] as Map<String, dynamic>;

      expect(stream['network'], 'tcp');
      expect(stream.containsKey('wsSettings'), isFalse);
    });

    test('DNS servers match VpnConstants defaults', () {
      final json = XrayConfigGenerator.generateVmessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
      );

      final config = jsonDecode(json) as Map<String, dynamic>;
      final dns = config['dns'] as Map<String, dynamic>;
      final servers = (dns['servers'] as List).cast<String>();

      expect(servers, equals(VpnConstants.defaultDnsServers));
    });

    test('output is valid parseable JSON', () {
      final json = XrayConfigGenerator.generateVmessConfig(
        address: 'example.com',
        port: 443,
        uuid: 'test-uuid',
      );

      // Should not throw
      expect(() => jsonDecode(json), returnsNormally);

      // Should be a Map
      final parsed = jsonDecode(json);
      expect(parsed, isA<Map<String, dynamic>>());
    });
  });

  // ---------------------------------------------------------------------------
  // Cross-protocol consistency
  // ---------------------------------------------------------------------------

  group('XrayConfigGenerator - cross-protocol', () {
    test('both generators include outbounds array', () {
      final vlessJson = XrayConfigGenerator.generateVlessConfig(
        address: 'server.com',
        port: 443,
        uuid: 'test-uuid',
      );
      final vmessJson = XrayConfigGenerator.generateVmessConfig(
        address: 'server.com',
        port: 443,
        uuid: 'test-uuid',
      );

      final vlessConfig = jsonDecode(vlessJson) as Map<String, dynamic>;
      final vmessConfig = jsonDecode(vmessJson) as Map<String, dynamic>;

      expect(vlessConfig['outbounds'], isA<List>());
      expect(vmessConfig['outbounds'], isA<List>());
      expect((vlessConfig['outbounds'] as List).length, 1);
      expect((vmessConfig['outbounds'] as List).length, 1);
    });

    test('both generators include DNS configuration', () {
      final vlessJson = XrayConfigGenerator.generateVlessConfig(
        address: 'server.com',
        port: 443,
        uuid: 'test-uuid',
      );
      final vmessJson = XrayConfigGenerator.generateVmessConfig(
        address: 'server.com',
        port: 443,
        uuid: 'test-uuid',
      );

      final vlessConfig = jsonDecode(vlessJson) as Map<String, dynamic>;
      final vmessConfig = jsonDecode(vmessJson) as Map<String, dynamic>;

      expect(vlessConfig, contains('dns'));
      expect(vmessConfig, contains('dns'));
    });

    test('protocol field differs between VLESS and VMess', () {
      final vlessJson = XrayConfigGenerator.generateVlessConfig(
        address: 'server.com',
        port: 443,
        uuid: 'test-uuid',
      );
      final vmessJson = XrayConfigGenerator.generateVmessConfig(
        address: 'server.com',
        port: 443,
        uuid: 'test-uuid',
      );

      final vlessConfig = jsonDecode(vlessJson) as Map<String, dynamic>;
      final vmessConfig = jsonDecode(vmessJson) as Map<String, dynamic>;
      final vlessOutbound =
          (vlessConfig['outbounds'] as List).first as Map<String, dynamic>;
      final vmessOutbound =
          (vmessConfig['outbounds'] as List).first as Map<String, dynamic>;

      expect(vlessOutbound['protocol'], 'vless');
      expect(vmessOutbound['protocol'], 'vmess');
    });

    test('VLESS uses encryption=none, VMess uses configurable security', () {
      final vlessJson = XrayConfigGenerator.generateVlessConfig(
        address: 'server.com',
        port: 443,
        uuid: 'test-uuid',
      );
      final vmessJson = XrayConfigGenerator.generateVmessConfig(
        address: 'server.com',
        port: 443,
        uuid: 'test-uuid',
      );

      final vlessConfig = jsonDecode(vlessJson) as Map<String, dynamic>;
      final vlessOutbound =
          (vlessConfig['outbounds'] as List).first as Map<String, dynamic>;
      final vlessSettings =
          vlessOutbound['settings'] as Map<String, dynamic>;
      final vlessVnext =
          (vlessSettings['vnext'] as List)[0] as Map<String, dynamic>;
      final vlessUser =
          (vlessVnext['users'] as List)[0] as Map<String, dynamic>;

      final vmessConfig = jsonDecode(vmessJson) as Map<String, dynamic>;
      final vmessOutbound =
          (vmessConfig['outbounds'] as List).first as Map<String, dynamic>;
      final vmessSettings =
          vmessOutbound['settings'] as Map<String, dynamic>;
      final vmessVnext =
          (vmessSettings['vnext'] as List)[0] as Map<String, dynamic>;
      final vmessUser =
          (vmessVnext['users'] as List)[0] as Map<String, dynamic>;

      expect(vlessUser['encryption'], 'none');
      expect(vmessUser['security'], 'auto');
    });
  });

  // ---------------------------------------------------------------------------
  // VpnConstants - DNS and encryption
  // ---------------------------------------------------------------------------

  group('VpnConstants - DNS and encryption settings', () {
    test('defaultDnsServers has 4 entries', () {
      expect(VpnConstants.defaultDnsServers, hasLength(4));
    });

    test('defaultDnsServers includes Cloudflare and Google', () {
      expect(VpnConstants.defaultDnsServers, contains('1.1.1.1'));
      expect(VpnConstants.defaultDnsServers, contains('1.0.0.1'));
      expect(VpnConstants.defaultDnsServers, contains('8.8.8.8'));
      expect(VpnConstants.defaultDnsServers, contains('8.8.4.4'));
    });

    test('defaultEncryption is auto', () {
      expect(VpnConstants.defaultEncryption, 'auto');
    });

    test('supportedEncryptions includes all common ciphers', () {
      expect(VpnConstants.supportedEncryptions, contains('auto'));
      expect(VpnConstants.supportedEncryptions, contains('aes-128-gcm'));
      expect(VpnConstants.supportedEncryptions, contains('aes-256-gcm'));
      expect(VpnConstants.supportedEncryptions, contains('chacha20-poly1305'));
      expect(VpnConstants.supportedEncryptions, contains('none'));
    });

    test('supportedTransports includes ws, tcp, grpc, http', () {
      expect(VpnConstants.supportedTransports, contains('tcp'));
      expect(VpnConstants.supportedTransports, contains('ws'));
      expect(VpnConstants.supportedTransports, contains('grpc'));
      expect(VpnConstants.supportedTransports, contains('http'));
    });

    test('defaultTransport is ws', () {
      expect(VpnConstants.defaultTransport, 'ws');
    });
  });
}

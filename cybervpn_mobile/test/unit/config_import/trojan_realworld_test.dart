import 'package:cybervpn_mobile/features/config_import/data/parsers/trojan_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:flutter_test/flutter_test.dart';

/// Real-world Trojan URI integration tests.
///
/// These URIs simulate configurations from popular VPN providers and
/// panel software. Focus is on realistic parameter combinations,
/// various transport types, and provider-specific quirks.
void main() {
  late TrojanParser parser;

  setUp(() {
    parser = TrojanParser();
  });

  // ---------------------------------------------------------------------------
  // Real-world Trojan + TLS (standard)
  // ---------------------------------------------------------------------------
  group('Trojan - real-world standard TLS configs', () {
    test('Basic Trojan TLS from 3X-UI panel', () {
      const uri =
          'trojan://a1b2c3d4e5f6@de-server.vpnprovider.net:443'
          '?security=tls'
          '&sni=de-server.vpnprovider.net'
          '&fingerprint=chrome'
          '&alpn=h2%2Chttp%2F1.1'
          '#DE-Frankfurt-Premium';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'trojan');
      expect(config.serverAddress, 'de-server.vpnprovider.net');
      expect(config.port, 443);
      expect(config.password, 'a1b2c3d4e5f6');
      expect(config.remark, 'DE-Frankfurt-Premium');
      expect(config.tlsSettings!['security'], 'tls');
      expect(config.tlsSettings!['sni'], 'de-server.vpnprovider.net');
      expect(config.tlsSettings!['fingerprint'], 'chrome');
      expect(config.tlsSettings!['alpn'], 'h2,http/1.1');
    });

    test('Trojan with UUID-style password (Marzban generates these)', () {
      const uri =
          'trojan://f47ac10b-58cc-4372-a567-0e02b2c3d479'
          '@marzban.example.com:443'
          '?security=tls'
          '&sni=marzban.example.com'
          '#Marzban-Trojan';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.password, 'f47ac10b-58cc-4372-a567-0e02b2c3d479');
      expect(config.remark, 'Marzban-Trojan');
    });

    test('Trojan on non-standard port 2083', () {
      const uri =
          'trojan://mysecretpassword@vpn.example.io:2083'
          '?security=tls'
          '&sni=vpn.example.io'
          '#CF-2083-Trojan';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.port, 2083);
      expect(config.remark, 'CF-2083-Trojan');
    });

    test('Trojan with allowInsecure=1 (skip cert verification)', () {
      const uri =
          'trojan://testpass@self-signed.example.com:443'
          '?security=tls'
          '&sni=self-signed.example.com'
          '&allowInsecure=1'
          '#Self-Signed';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.tlsSettings!['allowInsecure'], isTrue);
    });
  });

  // ---------------------------------------------------------------------------
  // Real-world Trojan + WebSocket (CDN-fronted)
  // ---------------------------------------------------------------------------
  group('Trojan - real-world WebSocket configs', () {
    test('Trojan-WS behind Cloudflare CDN', () {
      const uri =
          'trojan://cdn-password-123@cdn-proxy.example.com:443'
          '?type=ws'
          '&security=tls'
          '&path=%2Ftrojan-ws'
          '&host=user-trojan.workers.dev'
          '&sni=user-trojan.workers.dev'
          '#US-CF-Trojan-WS';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'trojan');
      expect(config.transportSettings!['type'], 'ws');
      expect(config.transportSettings!['path'], '/trojan-ws');
      expect(config.transportSettings!['host'], 'user-trojan.workers.dev');
      expect(config.tlsSettings!['sni'], 'user-trojan.workers.dev');
      expect(config.remark, 'US-CF-Trojan-WS');
    });

    test('Trojan-WS on port 80 without TLS', () {
      const uri =
          'trojan://plainpass@ws-plain.example.com:80'
          '?type=ws'
          '&path=%2Fws'
          '&host=ws-plain.example.com'
          '#WS-NoTLS';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.port, 80);
      expect(config.transportSettings!['type'], 'ws');
      expect(config.transportSettings!['path'], '/ws');
    });

    test('Trojan-WS with early-data path', () {
      const uri =
          'trojan://edpass@ws-ed.example.com:443'
          '?type=ws'
          '&security=tls'
          '&path=%2Ftrojan%3Fed%3D2048'
          '&host=ws-ed.example.com'
          '&sni=ws-ed.example.com'
          '#WS-EarlyData';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['path'], '/trojan?ed=2048');
    });
  });

  // ---------------------------------------------------------------------------
  // Real-world Trojan + gRPC
  // ---------------------------------------------------------------------------
  group('Trojan - real-world gRPC configs', () {
    test('Trojan-gRPC with TLS (X-UI style)', () {
      const uri =
          'trojan://grpc-password@grpc.example.net:443'
          '?type=grpc'
          '&security=tls'
          '&path=trojan-grpc-service'
          '&sni=grpc.example.net'
          '&fingerprint=firefox'
          '#NL-gRPC-Trojan';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'grpc');
      expect(config.transportSettings!['path'], 'trojan-grpc-service');
      expect(config.tlsSettings!['fingerprint'], 'firefox');
      expect(config.remark, 'NL-gRPC-Trojan');
    });
  });

  // ---------------------------------------------------------------------------
  // URL-encoded passwords and remarks
  // ---------------------------------------------------------------------------
  group('Trojan - URL-encoded special characters', () {
    test('Password with special characters (@, :, /)', () {
      const uri =
          'trojan://p%40ss%3Aw0rd%2F123@special.example.com:443'
          '?security=tls&sni=special.example.com'
          '#Special-Pass';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.password, 'p@ss:w0rd/123');
    });

    test('Chinese characters in remark', () {
      const uri =
          'trojan://pass123@hk-server.example.com:443'
          '?security=tls&sni=hk-server.example.com'
          '#%E9%A6%99%E6%B8%AF%20-%20Premium';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNotNull);
      expect(config.remark!, contains('Premium'));
    });

    test('Flag emoji and pipe separators in remark', () {
      const uri =
          'trojan://flagpass@node.example.com:443'
          '?security=tls&sni=node.example.com'
          '#%F0%9F%87%AF%F0%9F%87%B5%20%7C%20JP%20%7C%20Tokyo%20%7C%20x2.0';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNotNull);
      expect(config.remark!, contains('JP'));
      expect(config.remark!, contains('Tokyo'));
    });
  });

  // ---------------------------------------------------------------------------
  // IPv6 hosts
  // ---------------------------------------------------------------------------
  group('Trojan - IPv6 hosts', () {
    test('IPv6 server with TLS', () {
      const uri =
          'trojan://ipv6pass@[2a01:4f8:c010:d56a::1]:443'
          '?security=tls&sni=trojan6.example.com'
          '#IPv6-DE-Trojan';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '2a01:4f8:c010:d56a::1');
      expect(config.port, 443);
      expect(config.remark, 'IPv6-DE-Trojan');
    });
  });

  // ---------------------------------------------------------------------------
  // Provider-specific edge cases
  // ---------------------------------------------------------------------------
  group('Trojan - provider-specific edge cases', () {
    test('Trailing slash in URI (some panels add this)', () {
      const uri =
          'trojan://trailpass@trail.example.com:443/'
          '?security=tls&sni=trail.example.com'
          '#Trailing-Slash';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, 'trail.example.com');
      expect(config.port, 443);
    });

    test('Extra unknown query parameters preserved', () {
      const uri =
          'trojan://extrapass@extra.example.com:443'
          '?security=tls&sni=extra.example.com'
          '&flow=xtls-rprx-vision&custom_param=hello'
          '#Extra-Params';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams, isNotNull);
      expect(config.additionalParams!['flow'], 'xtls-rprx-vision');
      expect(config.additionalParams!['custom_param'], 'hello');
    });

    test('Minimal Trojan URI (password, host, port only)', () {
      const uri = 'trojan://minimalpass@minimal.example.com:443';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.password, 'minimalpass');
      expect(config.serverAddress, 'minimal.example.com');
      expect(config.port, 443);
      expect(config.remark, isNull);
      expect(config.tlsSettings, isNull);
      expect(config.transportSettings, isNull);
    });

    test('Long alphanumeric password (64 char hex string)', () {
      const uri =
          'trojan://a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2'
          '@long-pass.example.com:443'
          '?security=tls&sni=long-pass.example.com'
          '#Long-Password';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.password!.length, 64);
    });
  });

  // ---------------------------------------------------------------------------
  // Cross-field consistency
  // ---------------------------------------------------------------------------
  group('Trojan - cross-field consistency', () {
    test('all parsed configs have protocol set to trojan', () {
      final uris = [
        'trojan://pass1@host1.com:443',
        'trojan://pass2@host2.com:443?type=ws&path=%2Fws',
        'trojan://pass3@host3.com:443?type=grpc&path=svc&security=tls&sni=host3.com',
      ];

      for (final uri in uris) {
        final result = parser.parse(uri);
        expect(result, isA<ParseSuccess>(), reason: 'Failed for: $uri');
        final config = (result as ParseSuccess).config;
        expect(config.protocol, 'trojan');
      }
    });

    test('password is always stored in both uuid and password fields', () {
      const uri = 'trojan://dualfield@host.com:443#Test';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.uuid, 'dualfield');
      expect(config.password, 'dualfield');
      expect(config.uuid, config.password);
    });
  });
}

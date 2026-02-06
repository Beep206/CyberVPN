import 'package:cybervpn_mobile/features/config_import/data/parsers/vless_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:flutter_test/flutter_test.dart';

/// Real-world VLESS URI integration tests.
///
/// These URIs simulate configurations from popular VPN providers and
/// panel software (e.g., Remnawave, Marzban, X-UI, 3X-UI). The focus
/// is on realistic combinations of parameters rather than isolated
/// field validation (which is covered by the unit tests in
/// test/features/config_import/data/parsers/).
void main() {
  late VlessParser parser;

  setUp(() {
    parser = VlessParser();
  });

  // ---------------------------------------------------------------------------
  // Real-world VLESS + Reality configurations (most common in 2024-2025)
  // ---------------------------------------------------------------------------
  group('VLESS - real-world Reality URIs', () {
    test('3X-UI Reality + xtls-rprx-vision (typical Iranian provider)', () {
      const uri =
          'vless://b831381d-6324-4d53-ad4f-8cda48b30811'
          '@185.143.233.42:443'
          '?type=tcp'
          '&security=reality'
          '&pbk=SbVKOEMjK0sIlbwg4akyBg5mL5KZwwB-ed4eEE7YnRc'
          '&fp=chrome'
          '&sni=www.google.com'
          '&sid=6ba85179e30d4fc2'
          '&flow=xtls-rprx-vision'
          '&encryption=none'
          '#IR-Reality-TCP';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vless');
      expect(config.serverAddress, '185.143.233.42');
      expect(config.port, 443);
      expect(config.uuid, 'b831381d-6324-4d53-ad4f-8cda48b30811');
      expect(config.remark, 'IR-Reality-TCP');
      expect(config.tlsSettings!['security'], 'reality');
      expect(config.tlsSettings!['publicKey'],
          'SbVKOEMjK0sIlbwg4akyBg5mL5KZwwB-ed4eEE7YnRc');
      expect(config.tlsSettings!['fingerprint'], 'chrome');
      expect(config.tlsSettings!['sni'], 'www.google.com');
      expect(config.tlsSettings!['shortId'], '6ba85179e30d4fc2');
      expect(config.additionalParams!['flow'], 'xtls-rprx-vision');
      expect(config.additionalParams!['encryption'], 'none');
      expect(config.transportSettings!['type'], 'tcp');
    });

    test('Marzban Reality with Firefox fingerprint and short shortId', () {
      const uri =
          'vless://a3482e88-686a-4a58-8126-99c9034e4b09'
          '@de1.vpnprovider.net:2053'
          '?type=tcp'
          '&security=reality'
          '&pbk=rC2XGmFy6LbRCwCHBMejUaGPl0vlSab3NtDiFdRiB1c'
          '&fp=firefox'
          '&sni=www.amazon.de'
          '&sid=ab'
          '&flow=xtls-rprx-vision'
          '#DE-Frankfurt-01';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, 'de1.vpnprovider.net');
      expect(config.port, 2053);
      expect(config.remark, 'DE-Frankfurt-01');
      expect(config.tlsSettings!['fingerprint'], 'firefox');
      expect(config.tlsSettings!['sni'], 'www.amazon.de');
      expect(config.tlsSettings!['shortId'], 'ab');
    });

    test('Reality with empty shortId (valid in some panels)', () {
      const uri =
          'vless://c0293ea3-41b2-4e8c-b5f3-0a72d2ff1c82'
          '@95.216.100.50:443'
          '?type=tcp'
          '&security=reality'
          '&pbk=somePublicKeyValue123'
          '&fp=chrome'
          '&sni=yahoo.com'
          '&sid='
          '&flow=xtls-rprx-vision'
          '#FI-Helsinki';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '95.216.100.50');
      expect(config.remark, 'FI-Helsinki');
      // Empty sid is still present as empty string
      expect(config.tlsSettings!['shortId'], '');
    });
  });

  // ---------------------------------------------------------------------------
  // Real-world VLESS + WebSocket (CDN-fronted)
  // ---------------------------------------------------------------------------
  group('VLESS - real-world WebSocket URIs', () {
    test('CDN-fronted WS + TLS (Cloudflare typical config)', () {
      const uri =
          'vless://f47ac10b-58cc-4372-a567-0e02b2c3d479'
          '@cdn-proxy.example.com:443'
          '?type=ws'
          '&security=tls'
          '&path=%2Fvless-ws'
          '&host=user123.workers.dev'
          '&sni=user123.workers.dev'
          '&encryption=none'
          '#US-Cloudflare-WS';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vless');
      expect(config.serverAddress, 'cdn-proxy.example.com');
      expect(config.port, 443);
      expect(config.remark, 'US-Cloudflare-WS');
      expect(config.transportSettings!['type'], 'ws');
      expect(config.transportSettings!['path'], '/vless-ws');
      expect(config.transportSettings!['host'], 'user123.workers.dev');
      expect(config.tlsSettings!['security'], 'tls');
      expect(config.tlsSettings!['sni'], 'user123.workers.dev');
    });

    test('WS with early-data (ed parameter in path)', () {
      const uri =
          'vless://550e8400-e29b-41d4-a716-446655440000'
          '@ws-server.example.net:8443'
          '?type=ws'
          '&security=tls'
          '&path=%2Fws%3Fed%3D2048'
          '&host=ws-server.example.net'
          '&sni=ws-server.example.net'
          '#WS-EarlyData';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['path'], '/ws?ed=2048');
    });

    test('WS without TLS (plain HTTP, port 80)', () {
      const uri =
          'vless://6ba7b810-9dad-11d1-80b4-00c04fd430c8'
          '@plain-ws.example.com:80'
          '?type=ws'
          '&security=none'
          '&path=%2F'
          '&host=plain-ws.example.com'
          '#WS-NoTLS';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.port, 80);
      expect(config.transportSettings!['type'], 'ws');
      // security=none means no TLS settings
      expect(config.tlsSettings, isNull);
    });
  });

  // ---------------------------------------------------------------------------
  // Real-world VLESS + XHTTP / splithttp transport
  // ---------------------------------------------------------------------------
  group('VLESS - real-world XHTTP URIs', () {
    test('XHTTP with TLS and CDN host', () {
      const uri =
          'vless://7c9e6679-7425-40de-944b-e07fc1f90ae7'
          '@xhttp-node.example.com:443'
          '?type=xhttp'
          '&security=tls'
          '&path=%2Fxhttp-stream'
          '&host=cdn.example.com'
          '&sni=cdn.example.com'
          '&encryption=none'
          '#NL-XHTTP-CDN';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'xhttp');
      expect(config.transportSettings!['path'], '/xhttp-stream');
      expect(config.transportSettings!['host'], 'cdn.example.com');
      expect(config.remark, 'NL-XHTTP-CDN');
    });

    test('splithttp transport variant', () {
      const uri =
          'vless://e4d909c2-90d0-fb47-c9f1-0cb876843c8b'
          '@split.example.org:443'
          '?type=splithttp'
          '&security=tls'
          '&path=%2Fsplit-path'
          '&sni=split.example.org'
          '#Split-Server';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'splithttp');
    });
  });

  // ---------------------------------------------------------------------------
  // Real-world VLESS + gRPC
  // ---------------------------------------------------------------------------
  group('VLESS - real-world gRPC URIs', () {
    test('gRPC with Reality (Remnawave style)', () {
      const uri =
          'vless://d9428888-6728-4c5a-8d49-5b4010bb2983'
          '@grpc-node.vpnservice.io:443'
          '?type=grpc'
          '&security=reality'
          '&pbk=GrpcPublicKeyBase64String'
          '&fp=chrome'
          '&sni=www.google.com'
          '&sid=aabb'
          '&path=vless-grpc'
          '&flow=xtls-rprx-vision'
          '&encryption=none'
          '#DE-gRPC-Reality';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'grpc');
      expect(config.transportSettings!['path'], 'vless-grpc');
      expect(config.tlsSettings!['security'], 'reality');
      expect(config.remark, 'DE-gRPC-Reality');
    });

    test('gRPC with TLS', () {
      const uri =
          'vless://12345678-1234-1234-1234-123456789012'
          '@grpc.example.com:443'
          '?type=grpc'
          '&security=tls'
          '&sni=grpc.example.com'
          '&path=my-grpc-service'
          '#gRPC-TLS';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'grpc');
      expect(config.tlsSettings!['security'], 'tls');
    });
  });

  // ---------------------------------------------------------------------------
  // Real-world IPv6 URIs
  // ---------------------------------------------------------------------------
  group('VLESS - real-world IPv6 URIs', () {
    test('IPv6 server with Reality', () {
      const uri =
          'vless://a1a2a3a4-b1b2-c1c2-d1d2-e1e2e3e4e5e6'
          '@[2a01:4f8:c010:d56a::1]:443'
          '?type=tcp'
          '&security=reality'
          '&pbk=Ipv6PubKey123'
          '&fp=chrome'
          '&sni=www.google.com'
          '&sid=01'
          '&flow=xtls-rprx-vision'
          '#IPv6-Hetzner-DE';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '2a01:4f8:c010:d56a::1');
      expect(config.port, 443);
      expect(config.remark, 'IPv6-Hetzner-DE');
    });

    test('IPv6 loopback for local testing', () {
      const uri =
          'vless://01020304-0506-0708-0910-111213141516'
          '@[::1]:10443'
          '?type=tcp'
          '&security=none'
          '#Local-Test';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '::1');
      expect(config.port, 10443);
    });
  });

  // ---------------------------------------------------------------------------
  // URL-encoded and non-ASCII remarks
  // ---------------------------------------------------------------------------
  group('VLESS - URL-encoded and international remarks', () {
    test('Chinese characters in remark', () {
      const uri =
          'vless://abcdef12-3456-7890-abcd-ef1234567890'
          '@cn-proxy.example.com:443'
          '?type=tcp&security=reality'
          '&pbk=key123&fp=chrome&sni=www.bing.com&sid=aa'
          '&flow=xtls-rprx-vision'
          '#%E9%A6%99%E6%B8%AF%E6%9C%8D%E5%8A%A1%E5%99%A8%2001';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      // Should decode to Chinese characters
      expect(config.remark, isNotNull);
      expect(config.remark!, contains('01'));
    });

    test('Emoji-like encoded remark', () {
      const uri =
          'vless://12345678-abcd-ef01-2345-678901234567'
          '@emoji.example.com:443'
          '?type=tcp&security=none'
          '#US%20%F0%9F%87%BA%F0%9F%87%B8%20Premium';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNotNull);
      expect(config.remark!, contains('Premium'));
    });

    test('Remark with pipe separators (common in subscription links)', () {
      const uri =
          'vless://aabbccdd-1122-3344-5566-778899001122'
          '@node5.vpnprovider.com:443'
          '?type=tcp&security=reality'
          '&pbk=pkey&fp=chrome&sni=google.com&sid=ff'
          '&flow=xtls-rprx-vision'
          '#%F0%9F%87%A9%E2%80%8B%7C%20DE%20%7C%20Node-05%20%7C%20x1.5';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNotNull);
    });
  });

  // ---------------------------------------------------------------------------
  // Edge cases seen in real provider configs
  // ---------------------------------------------------------------------------
  group('VLESS - provider-specific edge cases', () {
    test('Non-standard port (2083 - Cloudflare SSL port)', () {
      const uri =
          'vless://deadbeef-dead-beef-dead-beefdeadbeef'
          '@cf-node.example.com:2083'
          '?type=ws&security=tls'
          '&path=%2Fvless&host=cf-node.example.com'
          '&sni=cf-node.example.com'
          '#CF-2083';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.port, 2083);
    });

    test('Very long remark (some panels generate verbose names)', () {
      const uri =
          'vless://11111111-2222-3333-4444-555555555555'
          '@node.example.com:443'
          '?type=tcp&security=reality'
          '&pbk=pk&fp=chrome&sni=google.com&sid=00'
          '&flow=xtls-rprx-vision'
          '#%5BPremium%5D%20DE%20-%20Frankfurt%20-%20Node%2003%20-%20'
          'x1.0%20-%20Unlimited%20-%20Expiry%3A%202025-12-31';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNotNull);
      expect(config.remark!, contains('Premium'));
      expect(config.remark!, contains('Frankfurt'));
    });

    test('h2 transport with Reality', () {
      const uri =
          'vless://22222222-3333-4444-5555-666666666666'
          '@h2-server.example.net:443'
          '?type=h2'
          '&security=reality'
          '&pbk=h2pubkey123'
          '&fp=safari'
          '&sni=www.apple.com'
          '&sid=cc'
          '&path=%2Fh2-path'
          '&flow=xtls-rprx-vision'
          '#H2-Reality';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'h2');
      expect(config.transportSettings!['path'], '/h2-path');
      expect(config.tlsSettings!['fingerprint'], 'safari');
      expect(config.tlsSettings!['sni'], 'www.apple.com');
    });
  });

  // ---------------------------------------------------------------------------
  // Consistency checks across parsed fields
  // ---------------------------------------------------------------------------
  group('VLESS - cross-field consistency', () {
    test('all parsed configs have protocol set to vless', () {
      final uris = [
        'vless://b831381d-6324-4d53-ad4f-8cda48b30811@host.com:443?type=tcp&security=none',
        'vless://b831381d-6324-4d53-ad4f-8cda48b30811@host.com:443?type=ws&security=tls&sni=host.com',
        'vless://b831381d-6324-4d53-ad4f-8cda48b30811@host.com:443?type=grpc&security=reality&pbk=k&fp=chrome&sni=g.com&sid=aa',
      ];

      for (final uri in uris) {
        final result = parser.parse(uri);
        expect(result, isA<ParseSuccess>(), reason: 'Failed for: $uri');
        final config = (result as ParseSuccess).config;
        expect(config.protocol, 'vless');
      }
    });

    test('port is always an integer within valid range', () {
      final ports = [443, 80, 2053, 2083, 8443, 10443, 8080, 1];
      for (final port in ports) {
        final uri =
            'vless://b831381d-6324-4d53-ad4f-8cda48b30811@host.com:$port?type=tcp&security=none';
        final result = parser.parse(uri);
        expect(result, isA<ParseSuccess>(), reason: 'Failed for port: $port');
        final config = (result as ParseSuccess).config;
        expect(config.port, port);
        expect(config.port, greaterThanOrEqualTo(1));
        expect(config.port, lessThanOrEqualTo(65535));
      }
    });
  });
}

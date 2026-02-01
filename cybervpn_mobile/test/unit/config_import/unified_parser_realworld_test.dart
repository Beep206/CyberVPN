import 'dart:convert';

import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/usecases/parse_vpn_uri.dart';
import 'package:flutter_test/flutter_test.dart';

/// Real-world integration tests for the unified VPN URI parser.
///
/// Tests the complete ParseVpnUri use case with realistic URIs that
/// simulate what users paste from subscription links, QR codes, and
/// share dialogs across popular VPN clients and providers.
///
/// Focus areas:
/// - Correct protocol dispatch for all 4 supported schemes
/// - Cross-parser consistency (common fields parsed identically)
/// - Multi-URI batch parsing (subscription link scenarios)
/// - Unknown/unsupported scheme handling
/// - Malformed input resilience
void main() {
  late ParseVpnUri useCase;

  setUp(() {
    useCase = ParseVpnUri();
  });

  // ---------------------------------------------------------------------------
  // Correct dispatch for real-world URIs
  // ---------------------------------------------------------------------------
  group('Unified parser - protocol dispatch with real-world URIs', () {
    test('dispatches VLESS Reality URI correctly', () {
      const uri =
          'vless://b831381d-6324-4d53-ad4f-8cda48b30811'
          '@reality-server.example.com:443'
          '?type=tcp&security=reality'
          '&pbk=SbVKOEMjK0sIlbwg4akyBg5mL5KZwwB-ed4eEE7YnRc'
          '&fp=chrome&sni=www.google.com&sid=6ba85179e30d4fc2'
          '&flow=xtls-rprx-vision&encryption=none'
          '#Reality-TCP';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vless');
      expect(config.serverAddress, 'reality-server.example.com');
    });

    test('dispatches VMess WS+TLS URI correctly', () {
      final vmessJson = {
        'v': '2',
        'ps': 'US-VMess-WS',
        'add': 'vmess-cdn.example.com',
        'port': 443,
        'id': '27848739-7e62-4138-9fd3-098a63964b6b',
        'aid': 0,
        'net': 'ws',
        'type': 'none',
        'host': 'user.workers.dev',
        'path': '/vmess-ws',
        'tls': 'tls',
        'sni': 'user.workers.dev',
      };
      final payload = base64Url
          .encode(utf8.encode(jsonEncode(vmessJson)))
          .replaceAll('=', '');
      final uri = 'vmess://$payload';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vmess');
      expect(config.serverAddress, 'vmess-cdn.example.com');
    });

    test('dispatches Trojan WS URI correctly', () {
      const uri =
          'trojan://trojan-password@trojan-ws.example.com:443'
          '?type=ws&security=tls'
          '&path=%2Ftrojan-ws&host=cdn.example.com'
          '&sni=cdn.example.com'
          '#Trojan-WS';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'trojan');
      expect(config.serverAddress, 'trojan-ws.example.com');
    });

    test('dispatches Shadowsocks SIP002 URI correctly', () {
      final userinfo = base64Url
          .encode(utf8.encode('aes-256-gcm:mypassword'))
          .replaceAll('=', '');
      final uri = 'ss://$userinfo@outline.example.com:8388'
          '/?plugin=${Uri.encodeComponent("obfs-local;obfs=http")}'
          '#Outline-SS';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'shadowsocks');
      expect(config.serverAddress, 'outline.example.com');
    });
  });

  // ---------------------------------------------------------------------------
  // Case-insensitive scheme detection
  // ---------------------------------------------------------------------------
  group('Unified parser - case-insensitive dispatch', () {
    test('VLESS in uppercase', () {
      const uri =
          'VLESS://b831381d-6324-4d53-ad4f-8cda48b30811@host.com:443'
          '?type=tcp&security=none';

      final result = useCase.call(uri);
      expect(result, isA<ParseSuccess>());
      expect((result as ParseSuccess).config.protocol, 'vless');
    });

    test('VMESS in mixed case', () {
      final json = {
        'add': 'host.com',
        'port': 443,
        'id': '12345678-1234-1234-1234-123456789012',
      };
      final payload = base64Url
          .encode(utf8.encode(jsonEncode(json)))
          .replaceAll('=', '');
      final uri = 'VmEsS://$payload';

      final result = useCase.call(uri);
      expect(result, isA<ParseSuccess>());
      expect((result as ParseSuccess).config.protocol, 'vmess');
    });

    test('TROJAN in uppercase', () {
      const uri = 'TROJAN://pass@host.com:443#Test';

      final result = useCase.call(uri);
      expect(result, isA<ParseSuccess>());
      expect((result as ParseSuccess).config.protocol, 'trojan');
    });

    test('SS in uppercase', () {
      final userinfo = base64Url
          .encode(utf8.encode('aes-256-gcm:pass'))
          .replaceAll('=', '');
      final uri = 'SS://$userinfo@host.com:443';

      final result = useCase.call(uri);
      expect(result, isA<ParseSuccess>());
      expect((result as ParseSuccess).config.protocol, 'shadowsocks');
    });
  });

  // ---------------------------------------------------------------------------
  // Unknown and unsupported schemes
  // ---------------------------------------------------------------------------
  group('Unified parser - unknown scheme handling', () {
    test('wireguard:// returns descriptive error', () {
      final result = useCase.call('wireguard://some-config-data');

      expect(result, isA<ParseFailure>());
      final msg = (result as ParseFailure).message;
      expect(msg, contains('Unsupported VPN URI scheme'));
      expect(msg, contains('wireguard'));
    });

    test('hysteria2:// returns descriptive error', () {
      final result = useCase.call('hysteria2://auth@host:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('hysteria2'),
      );
    });

    test('http:// returns descriptive error', () {
      final result = useCase.call('http://not-a-vpn.com');

      expect(result, isA<ParseFailure>());
      final msg = (result as ParseFailure).message;
      expect(msg, contains('Unsupported'));
      expect(msg, contains('http'));
    });

    test('tuic:// returns descriptive error', () {
      final result = useCase.call('tuic://uuid:password@host:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('tuic'),
      );
    });

    test('string without :// separator returns no-scheme error', () {
      final result = useCase.call('just-random-text');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('no scheme detected'),
      );
    });

    test('error message includes list of supported schemes', () {
      final result = useCase.call('wireguard://data');

      expect(result, isA<ParseFailure>());
      final msg = (result as ParseFailure).message;
      expect(msg, contains('vless://'));
      expect(msg, contains('vmess://'));
      expect(msg, contains('trojan://'));
      expect(msg, contains('ss://'));
    });
  });

  // ---------------------------------------------------------------------------
  // Empty / null / whitespace input
  // ---------------------------------------------------------------------------
  group('Unified parser - null and empty input', () {
    test('null returns ParseFailure', () {
      final result = useCase.call(null);

      expect(result, isA<ParseFailure>());
      expect((result as ParseFailure).message, contains('null or empty'));
    });

    test('empty string returns ParseFailure', () {
      final result = useCase.call('');

      expect(result, isA<ParseFailure>());
    });

    test('whitespace-only returns ParseFailure', () {
      final result = useCase.call('   \t\n  ');

      expect(result, isA<ParseFailure>());
    });
  });

  // ---------------------------------------------------------------------------
  // Multi-protocol batch simulation (subscription link scenario)
  // ---------------------------------------------------------------------------
  group('Unified parser - batch parsing simulation', () {
    test('parse multiple protocols from a subscription list', () {
      final vmessJson = {
        'v': '2',
        'ps': 'VMess-Node',
        'add': 'vmess.example.com',
        'port': 443,
        'id': '12345678-1234-1234-1234-123456789012',
        'aid': 0,
        'net': 'ws',
        'tls': 'tls',
        'sni': 'vmess.example.com',
      };
      final vmessPayload = base64Url
          .encode(utf8.encode(jsonEncode(vmessJson)))
          .replaceAll('=', '');

      final ssUserinfo = base64Url
          .encode(utf8.encode('aes-256-gcm:sspassword'))
          .replaceAll('=', '');

      // Simulate a subscription that contains one of each protocol
      final uris = [
        'vless://b831381d-6324-4d53-ad4f-8cda48b30811@vless.example.com:443'
            '?type=tcp&security=reality&pbk=key&fp=chrome&sni=google.com'
            '&sid=aa&flow=xtls-rprx-vision#VLESS-Node',
        'vmess://$vmessPayload',
        'trojan://trojanpass@trojan.example.com:443'
            '?security=tls&sni=trojan.example.com#Trojan-Node',
        'ss://$ssUserinfo@ss.example.com:8388#SS-Node',
      ];

      final expectedProtocols = ['vless', 'vmess', 'trojan', 'shadowsocks'];

      for (var i = 0; i < uris.length; i++) {
        final result = useCase.call(uris[i]);
        expect(result, isA<ParseSuccess>(), reason: 'Failed for URI $i');
        final config = (result as ParseSuccess).config;
        expect(config.protocol, expectedProtocols[i],
            reason: 'Wrong protocol for URI $i');
      }
    });

    test('mixed valid and invalid URIs in batch', () {
      final ssUserinfo = base64Url
          .encode(utf8.encode('aes-256-gcm:pass'))
          .replaceAll('=', '');

      final uris = [
        'vless://b831381d-6324-4d53-ad4f-8cda48b30811@host.com:443?type=tcp&security=none',
        'wireguard://unsupported', // should fail
        'ss://$ssUserinfo@host.com:443',
        '', // should fail
        'trojan://pass@host.com:443',
      ];

      final results = uris.map((uri) => useCase.call(uri)).toList();

      expect(results[0], isA<ParseSuccess>());
      expect(results[1], isA<ParseFailure>());
      expect(results[2], isA<ParseSuccess>());
      expect(results[3], isA<ParseFailure>());
      expect(results[4], isA<ParseSuccess>());
    });
  });

  // ---------------------------------------------------------------------------
  // Cross-parser consistency: common fields
  // ---------------------------------------------------------------------------
  group('Unified parser - cross-parser consistency', () {
    test('serverAddress field is consistently populated across protocols', () {
      final vmessJson = {
        'add': 'consistent.example.com',
        'port': 443,
        'id': '12345678-1234-1234-1234-123456789012',
      };
      final vmessPayload = base64Url
          .encode(utf8.encode(jsonEncode(vmessJson)))
          .replaceAll('=', '');

      final ssUserinfo = base64Url
          .encode(utf8.encode('aes-256-gcm:pass'))
          .replaceAll('=', '');

      final uris = [
        'vless://b831381d-6324-4d53-ad4f-8cda48b30811@consistent.example.com:443?type=tcp&security=none',
        'vmess://$vmessPayload',
        'trojan://pass@consistent.example.com:443',
        'ss://$ssUserinfo@consistent.example.com:443',
      ];

      for (final uri in uris) {
        final result = useCase.call(uri);
        expect(result, isA<ParseSuccess>(), reason: 'Failed for: $uri');
        final config = (result as ParseSuccess).config;
        expect(config.serverAddress, 'consistent.example.com',
            reason: 'Inconsistent serverAddress for: $uri');
      }
    });

    test('port field is consistently an integer across protocols', () {
      final vmessJson = {
        'add': 'host.com',
        'port': 8443,
        'id': '12345678-1234-1234-1234-123456789012',
      };
      final vmessPayload = base64Url
          .encode(utf8.encode(jsonEncode(vmessJson)))
          .replaceAll('=', '');

      final ssUserinfo = base64Url
          .encode(utf8.encode('aes-256-gcm:pass'))
          .replaceAll('=', '');

      final uris = [
        'vless://b831381d-6324-4d53-ad4f-8cda48b30811@host.com:8443?type=tcp&security=none',
        'vmess://$vmessPayload',
        'trojan://pass@host.com:8443',
        'ss://$ssUserinfo@host.com:8443',
      ];

      for (final uri in uris) {
        final result = useCase.call(uri);
        expect(result, isA<ParseSuccess>(), reason: 'Failed for: $uri');
        final config = (result as ParseSuccess).config;
        expect(config.port, 8443,
            reason: 'Inconsistent port for: $uri');
        expect(config.port, isA<int>());
      }
    });

    test('remark field is consistently decoded across protocols', () {
      final vmessJson = {
        'add': 'host.com',
        'port': 443,
        'id': '12345678-1234-1234-1234-123456789012',
        'ps': 'US - Premium',
      };
      final vmessPayload = base64Url
          .encode(utf8.encode(jsonEncode(vmessJson)))
          .replaceAll('=', '');

      final ssUserinfo = base64Url
          .encode(utf8.encode('aes-256-gcm:pass'))
          .replaceAll('=', '');

      final urisAndRemarks = <String, String>{
        'vless://b831381d-6324-4d53-ad4f-8cda48b30811@host.com:443?type=tcp&security=none#US%20-%20Premium':
            'US - Premium',
        'vmess://$vmessPayload': 'US - Premium',
        'trojan://pass@host.com:443#US%20-%20Premium': 'US - Premium',
        'ss://$ssUserinfo@host.com:443#US%20-%20Premium': 'US - Premium',
      };

      for (final entry in urisAndRemarks.entries) {
        final result = useCase.call(entry.key);
        expect(result, isA<ParseSuccess>(), reason: 'Failed for: ${entry.key}');
        final config = (result as ParseSuccess).config;
        expect(config.remark, entry.value,
            reason: 'Inconsistent remark for: ${entry.key}');
      }
    });
  });

  // ---------------------------------------------------------------------------
  // URIs with leading/trailing whitespace (copy-paste scenarios)
  // ---------------------------------------------------------------------------
  group('Unified parser - whitespace handling', () {
    test('leading and trailing whitespace is stripped', () {
      const uri =
          '  \n  vless://b831381d-6324-4d53-ad4f-8cda48b30811@host.com:443?type=tcp&security=none  \t  ';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
    });

    test('leading spaces before trojan:// URI', () {
      const uri = '    trojan://pass@host.com:443#Test';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
      expect((result as ParseSuccess).config.protocol, 'trojan');
    });
  });
}

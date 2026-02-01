import 'dart:convert';

import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/usecases/parse_vpn_uri.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  late ParseVpnUri useCase;

  setUp(() {
    useCase = ParseVpnUri();
  });

  group('ParseVpnUri - dispatching', () {
    test('dispatches vless:// URI to VlessParser', () {
      const uri =
          'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443'
          '?security=tls&type=ws#MyVless';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vless');
      expect(config.serverAddress, 'example.com');
      expect(config.port, 443);
    });

    test('dispatches vmess:// URI to VmessParser', () {
      final payload = base64Encode(utf8.encode(jsonEncode({
        'v': '2',
        'ps': 'MyVmess',
        'add': 'vmess.example.com',
        'port': 8080,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'aid': 0,
        'net': 'tcp',
        'type': 'none',
        'tls': '',
      })));
      final uri = 'vmess://$payload';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vmess');
      expect(config.serverAddress, 'vmess.example.com');
      expect(config.port, 8080);
    });

    test('dispatches trojan:// URI to TrojanParser', () {
      const uri = 'trojan://mypassword@trojan.example.com:443#MyTrojan';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'trojan');
      expect(config.serverAddress, 'trojan.example.com');
      expect(config.port, 443);
    });

    test('dispatches ss:// URI to ShadowsocksParser', () {
      final userinfo = base64Encode(utf8.encode('aes-256-gcm:mypassword'));
      final uri = 'ss://$userinfo@ss.example.com:8388#MySS';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'shadowsocks');
      expect(config.serverAddress, 'ss.example.com');
      expect(config.port, 8388);
    });

    test('is case-insensitive for scheme detection', () {
      const uri =
          'VLESS://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443'
          '?security=none&type=tcp';

      final result = useCase.call(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vless');
    });
  });

  group('ParseVpnUri - error handling', () {
    test('returns ParseFailure for null input', () {
      final result = useCase.call(null);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('null or empty'),
      );
    });

    test('returns ParseFailure for empty string', () {
      final result = useCase.call('');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('null or empty'),
      );
    });

    test('returns ParseFailure for whitespace-only string', () {
      final result = useCase.call('   ');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('null or empty'),
      );
    });

    test('returns ParseFailure with scheme name for unsupported scheme', () {
      final result = useCase.call('http://example.com');

      expect(result, isA<ParseFailure>());
      final message = (result as ParseFailure).message;
      expect(message, contains('Unsupported VPN URI scheme'));
      expect(message, contains('http'));
      expect(message, contains('vless://'));
      expect(message, contains('vmess://'));
      expect(message, contains('trojan://'));
      expect(message, contains('ss://'));
    });

    test('returns ParseFailure for wireguard:// scheme', () {
      final result = useCase.call('wireguard://somedata');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('wireguard'),
      );
    });

    test('returns ParseFailure for string with no scheme separator', () {
      final result = useCase.call('not-a-uri-at-all');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('no scheme detected'),
      );
    });

    test('returns ParseFailure for random gibberish with ://', () {
      final result = useCase.call('foobar://something');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('Unsupported VPN URI scheme'),
      );
    });
  });

  group('ParseVpnUri - custom parsers', () {
    test('accepts custom parser list', () {
      // Create use case with no parsers - everything should fail
      final emptyUseCase = ParseVpnUri(parsers: []);
      final result = emptyUseCase.call(
        'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443'
        '?security=none&type=tcp',
      );

      expect(result, isA<ParseFailure>());
    });
  });

  group('ParseVpnUri - supportedSchemes', () {
    test('lists all four supported schemes', () {
      expect(ParseVpnUri.supportedSchemes, containsAll([
        'vless://',
        'vmess://',
        'trojan://',
        'ss://',
      ]));
      expect(ParseVpnUri.supportedSchemes.length, 4);
    });
  });
}

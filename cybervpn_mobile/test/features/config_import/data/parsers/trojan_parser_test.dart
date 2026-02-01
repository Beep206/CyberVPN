import 'package:cybervpn_mobile/features/config_import/data/parsers/trojan_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  late TrojanParser parser;

  setUp(() {
    parser = TrojanParser();
  });

  group('TrojanParser - interface', () {
    test('protocolName returns trojan', () {
      expect(parser.protocolName, 'trojan');
    });

    test('canParse returns true for trojan:// URIs', () {
      expect(parser.canParse('trojan://pass@host:443'), isTrue);
      expect(parser.canParse('TROJAN://pass@host:443'), isTrue);
      expect(parser.canParse('  trojan://pass@host:443'), isTrue);
    });

    test('canParse returns false for non-trojan URIs', () {
      expect(parser.canParse('vless://uuid@host:443'), isFalse);
      expect(parser.canParse('ss://abc@host:443'), isFalse);
      expect(parser.canParse('http://example.com'), isFalse);
      expect(parser.canParse('invalid'), isFalse);
    });

    test('implements VpnUriParser', () {
      expect(parser, isA<VpnUriParser>());
    });
  });

  group('TrojanParser - standard Trojan URI', () {
    test('parses valid URI with all parameters', () {
      const uri =
          'trojan://mypassword@example.com:443?security=tls&sni=example.com&fingerprint=chrome&type=tcp&alpn=h2#My%20Server';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'trojan');
      expect(config.serverAddress, 'example.com');
      expect(config.port, 443);
      expect(config.uuid, 'mypassword');
      expect(config.password, 'mypassword');
      expect(config.remark, 'My Server');
      expect(config.tlsSettings, isNotNull);
      expect(config.tlsSettings!['sni'], 'example.com');
      expect(config.tlsSettings!['fingerprint'], 'chrome');
      expect(config.tlsSettings!['security'], 'tls');
      expect(config.tlsSettings!['alpn'], 'h2');
      expect(config.transportSettings, isNotNull);
      expect(config.transportSettings!['type'], 'tcp');
    });

    test('parses URI with minimal fields (password, host, port only)', () {
      const uri = 'trojan://secretpass@vpn.example.com:8443';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'trojan');
      expect(config.serverAddress, 'vpn.example.com');
      expect(config.port, 8443);
      expect(config.password, 'secretpass');
      expect(config.remark, isNull);
      expect(config.tlsSettings, isNull);
      expect(config.transportSettings, isNull);
      expect(config.additionalParams, isNull);
    });

    test('parses URI with IP address', () {
      const uri = 'trojan://pass123@192.168.1.100:443#IP%20Server';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '192.168.1.100');
      expect(config.port, 443);
      expect(config.remark, 'IP Server');
    });
  });

  group('TrojanParser - with SNI', () {
    test('parses URI with SNI parameter only', () {
      const uri = 'trojan://password@server.com:443?sni=cdn.server.com#SNI%20Server';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.tlsSettings, isNotNull);
      expect(config.tlsSettings!['sni'], 'cdn.server.com');
      expect(config.remark, 'SNI Server');
    });

    test('parses URI with SNI and fingerprint', () {
      const uri =
          'trojan://pass@host.com:443?sni=sni.host.com&fingerprint=firefox';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.tlsSettings!['sni'], 'sni.host.com');
      expect(config.tlsSettings!['fingerprint'], 'firefox');
    });
  });

  group('TrojanParser - with WebSocket transport', () {
    test('parses URI with WebSocket transport', () {
      const uri =
          'trojan://pass@example.com:443?type=ws&path=%2Fws&host=cdn.example.com#WS%20Server';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings, isNotNull);
      expect(config.transportSettings!['type'], 'ws');
      expect(config.transportSettings!['path'], '/ws');
      expect(config.transportSettings!['host'], 'cdn.example.com');
      expect(config.remark, 'WS Server');
    });

    test('parses URI with gRPC transport', () {
      const uri =
          'trojan://pass@example.com:443?type=grpc&path=trojan-grpc&sni=example.com';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'grpc');
      expect(config.transportSettings!['path'], 'trojan-grpc');
      expect(config.tlsSettings!['sni'], 'example.com');
    });

    test('parses URI with h2 transport', () {
      const uri = 'trojan://pass@example.com:443?type=h2&path=%2Fh2&host=example.com';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'h2');
      expect(config.transportSettings!['path'], '/h2');
    });
  });

  group('TrojanParser - missing remark', () {
    test('parses URI without remark (no fragment)', () {
      const uri = 'trojan://password@example.com:443?sni=example.com';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNull);
      expect(config.password, 'password');
      expect(config.serverAddress, 'example.com');
    });

    test('parses URI with empty fragment', () {
      const uri = 'trojan://password@example.com:443#';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNull);
    });
  });

  group('TrojanParser - IPv6 addresses', () {
    test('parses URI with IPv6 host in brackets', () {
      const uri = 'trojan://password@[::1]:443#IPv6%20Server';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '::1');
      expect(config.port, 443);
      expect(config.remark, 'IPv6 Server');
    });

    test('parses URI with full IPv6 address', () {
      const uri =
          'trojan://password@[2001:db8::1]:8443?sni=example.com#IPv6%20Full';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '2001:db8::1');
      expect(config.port, 8443);
    });
  });

  group('TrojanParser - URL-encoded special characters', () {
    test('handles URL-encoded password with special characters', () {
      // Password: p@ss:word/123
      const uri =
          'trojan://p%40ss%3Aword%2F123@example.com:443#Test';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.password, 'p@ss:word/123');
    });

    test('handles URL-encoded remark with unicode', () {
      const uri =
          'trojan://pass@example.com:443#%E6%97%A5%E6%9C%AC%E3%82%B5%E3%83%BC%E3%83%90%E3%83%BC';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      // Japanese characters
      expect(config.remark, isNotNull);
      expect(config.remark!.isNotEmpty, isTrue);
    });

    test('handles remark with spaces and special characters', () {
      const uri =
          'trojan://pass@example.com:443#Server%20%231%20(US)';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, 'Server #1 (US)');
    });
  });

  group('TrojanParser - allowInsecure parameter', () {
    test('parses allowInsecure=1 as true', () {
      const uri = 'trojan://pass@example.com:443?allowInsecure=1';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.tlsSettings!['allowInsecure'], isTrue);
    });

    test('parses allowInsecure=true as true', () {
      const uri = 'trojan://pass@example.com:443?allowInsecure=true';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.tlsSettings!['allowInsecure'], isTrue);
    });

    test('parses allowInsecure=0 as false', () {
      const uri = 'trojan://pass@example.com:443?allowInsecure=0';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.tlsSettings!['allowInsecure'], isFalse);
    });
  });

  group('TrojanParser - error handling', () {
    test('rejects non-trojan scheme', () {
      final result = parser.parse('vless://uuid@host:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('scheme must be trojan://'),
      );
    });

    test('rejects empty URI after scheme', () {
      final result = parser.parse('trojan://');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('empty URI after scheme'),
      );
    });

    test('rejects URI missing @ separator', () {
      final result = parser.parse('trojan://passwordhostport');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('missing @'),
      );
    });

    test('rejects URI with empty password', () {
      final result = parser.parse('trojan://@example.com:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('password is empty'),
      );
    });

    test('rejects URI with missing port', () {
      final result = parser.parse('trojan://pass@example.com');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });

    test('rejects port out of range (0)', () {
      final result = parser.parse('trojan://pass@example.com:0');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });

    test('rejects port out of range (99999)', () {
      final result = parser.parse('trojan://pass@example.com:99999');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });

    test('rejects unsupported transport type', () {
      final result = parser.parse(
        'trojan://pass@example.com:443?type=invalid_transport',
      );

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('unsupported transport type'),
      );
    });

    test('rejects IPv6 address missing closing bracket', () {
      final result = parser.parse('trojan://pass@[::1:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('closing bracket'),
      );
    });

    test('rejects URI with empty host', () {
      final result = parser.parse('trojan://pass@:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('server address is empty'),
      );
    });
  });

  group('TrojanParser - edge cases', () {
    test('handles whitespace around URI', () {
      const uri = '  trojan://pass@example.com:443#Test  ';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, 'example.com');
      expect(config.remark, 'Test');
    });

    test('handles unknown query parameters in additionalParams', () {
      const uri =
          'trojan://pass@example.com:443?sni=example.com&flow=xtls-rprx-vision&custom=value';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams, isNotNull);
      expect(config.additionalParams!['flow'], 'xtls-rprx-vision');
      expect(config.additionalParams!['custom'], 'value');
      // sni should be in tlsSettings, not additionalParams
      expect(config.additionalParams!.containsKey('sni'), isFalse);
    });

    test('handles URI with trailing slash before query', () {
      const uri = 'trojan://pass@example.com:443/?sni=example.com#Test';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, 'example.com');
      expect(config.port, 443);
    });

    test('parses complete real-world Trojan URI', () {
      const uri =
          'trojan://a1b2c3d4e5@trojan-server.example.com:443?security=tls&sni=trojan-server.example.com&type=ws&path=%2Ftrojan-ws&host=cdn.example.com&fingerprint=chrome&alpn=h2%2Chttp%2F1.1#US%20-%20Premium';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'trojan');
      expect(config.password, 'a1b2c3d4e5');
      expect(config.serverAddress, 'trojan-server.example.com');
      expect(config.port, 443);
      expect(config.remark, 'US - Premium');
      expect(config.tlsSettings!['security'], 'tls');
      expect(config.tlsSettings!['sni'], 'trojan-server.example.com');
      expect(config.tlsSettings!['fingerprint'], 'chrome');
      expect(config.transportSettings!['type'], 'ws');
      expect(config.transportSettings!['path'], '/trojan-ws');
      expect(config.transportSettings!['host'], 'cdn.example.com');
    });
  });
}

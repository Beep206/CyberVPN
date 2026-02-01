import 'package:cybervpn_mobile/features/config_import/data/parsers/vless_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:flutter_test/flutter_test.dart';

/// Helper to build a VLESS URI: vless://UUID@host:port?params#remark
String buildVlessUri({
  required String uuid,
  required String host,
  required int port,
  Map<String, String>? params,
  String? remark,
}) {
  final query = params != null && params.isNotEmpty
      ? '?${params.entries.map((e) => '${e.key}=${Uri.encodeComponent(e.value)}').join('&')}'
      : '';
  final fragment = remark != null ? '#${Uri.encodeComponent(remark)}' : '';

  // Handle IPv6 addresses
  final hostPart = host.contains(':') ? '[$host]' : host;

  return 'vless://$uuid@$hostPart:$port$query$fragment';
}

void main() {
  late VlessParser parser;

  setUp(() {
    parser = VlessParser();
  });

  group('VlessParser - interface', () {
    test('protocolName returns vless', () {
      expect(parser.protocolName, 'vless');
    });

    test('canParse returns true for vless:// URIs', () {
      expect(parser.canParse('vless://uuid@host:443'), isTrue);
      expect(parser.canParse('VLESS://uuid@host:443'), isTrue);
      expect(parser.canParse('  vless://uuid@host:443'), isTrue);
    });

    test('canParse returns false for non-vless URIs', () {
      expect(parser.canParse('ss://abc@host:443'), isFalse);
      expect(parser.canParse('vmess://abc@host:443'), isFalse);
      expect(parser.canParse('http://example.com'), isFalse);
      expect(parser.canParse('invalid'), isFalse);
    });

    test('implements VpnUriParser', () {
      expect(parser, isA<VpnUriParser>());
    });
  });

  group('VlessParser - standard VLESS URI', () {
    test('parses valid URI with all fields', () {
      final uri = buildVlessUri(
        uuid: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        host: 'example.com',
        port: 443,
        params: {
          'encryption': 'none',
          'security': 'tls',
          'sni': 'example.com',
          'type': 'tcp',
        },
        remark: 'My Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vless');
      expect(config.serverAddress, 'example.com');
      expect(config.port, 443);
      expect(config.uuid, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890');
      expect(config.remark, 'My Server');
      expect(config.additionalParams!['encryption'], 'none');
      expect(config.tlsSettings!['security'], 'tls');
      expect(config.tlsSettings!['sni'], 'example.com');
      expect(config.transportSettings!['type'], 'tcp');
    });

    test('parses URI without remark', () {
      final uri = buildVlessUri(
        uuid: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        host: '192.168.1.1',
        port: 8443,
        params: {'security': 'none', 'type': 'tcp'},
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNull);
      expect(config.serverAddress, '192.168.1.1');
      expect(config.port, 8443);
    });

    test('parses URI with minimal params (defaults)', () {
      const uri =
          'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vless');
      expect(config.additionalParams!['encryption'], 'none');
      expect(config.transportSettings!['type'], 'tcp');
      expect(config.tlsSettings, isNull); // security defaults to 'none'
    });
  });

  group('VlessParser - VLESS-Reality', () {
    test('parses VLESS-Reality URI with all Reality fields', () {
      final uri = buildVlessUri(
        uuid: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        host: 'reality.example.com',
        port: 443,
        params: {
          'encryption': 'none',
          'flow': 'xtls-rprx-vision',
          'security': 'reality',
          'sni': 'www.google.com',
          'fp': 'chrome',
          'pbk': 'abc123publickey',
          'sid': 'deadbeef',
          'type': 'tcp',
        },
        remark: 'Reality Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vless');
      expect(config.serverAddress, 'reality.example.com');
      expect(config.port, 443);
      expect(config.additionalParams!['flow'], 'xtls-rprx-vision');
      expect(config.tlsSettings!['security'], 'reality');
      expect(config.tlsSettings!['sni'], 'www.google.com');
      expect(config.tlsSettings!['fingerprint'], 'chrome');
      expect(config.tlsSettings!['publicKey'], 'abc123publickey');
      expect(config.tlsSettings!['shortId'], 'deadbeef');
      expect(config.remark, 'Reality Server');
    });

    test('parses Reality URI with alternative key names', () {
      final uri = buildVlessUri(
        uuid: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        host: 'server.com',
        port: 443,
        params: {
          'security': 'reality',
          'fingerprint': 'firefox',
          'publicKey': 'mypublickey',
          'shortId': 'abcd1234',
        },
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.tlsSettings!['fingerprint'], 'firefox');
      expect(config.tlsSettings!['publicKey'], 'mypublickey');
      expect(config.tlsSettings!['shortId'], 'abcd1234');
    });
  });

  group('VlessParser - VLESS-WS', () {
    test('parses VLESS WebSocket URI', () {
      final uri = buildVlessUri(
        uuid: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        host: 'ws.example.com',
        port: 443,
        params: {
          'encryption': 'none',
          'security': 'tls',
          'sni': 'ws.example.com',
          'type': 'ws',
          'path': '/websocket',
          'host': 'ws.example.com',
        },
        remark: 'WS Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'ws');
      expect(config.transportSettings!['path'], '/websocket');
      expect(config.transportSettings!['host'], 'ws.example.com');
      expect(config.remark, 'WS Server');
    });
  });

  group('VlessParser - VLESS-XHTTP', () {
    test('parses VLESS XHTTP transport URI', () {
      final uri = buildVlessUri(
        uuid: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        host: 'xhttp.example.com',
        port: 443,
        params: {
          'encryption': 'none',
          'security': 'tls',
          'type': 'xhttp',
          'path': '/xhttp-path',
          'host': 'cdn.example.com',
        },
        remark: 'XHTTP Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'xhttp');
      expect(config.transportSettings!['path'], '/xhttp-path');
      expect(config.transportSettings!['host'], 'cdn.example.com');
    });
  });

  group('VlessParser - IPv6 address', () {
    test('parses URI with IPv6 address in brackets', () {
      const uri =
          'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@[::1]:443?security=none#IPv6%20Server';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '::1');
      expect(config.port, 443);
      expect(config.remark, 'IPv6 Server');
    });

    test('parses URI with full IPv6 address', () {
      const uri =
          'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@[2001:db8::1]:8443?security=none';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '2001:db8::1');
      expect(config.port, 8443);
    });
  });

  group('VlessParser - URL-encoded special characters', () {
    test('decodes URL-encoded remark', () {
      const uri =
          'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443?security=none#Server%20%231%20(US)';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, 'Server #1 (US)');
    });

    test('decodes URL-encoded path in query params', () {
      final uri = buildVlessUri(
        uuid: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        host: 'example.com',
        port: 443,
        params: {
          'security': 'tls',
          'type': 'ws',
          'path': '/ws/path?ed=2048',
        },
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['path'], '/ws/path?ed=2048');
    });

    test('handles unicode characters in remark', () {
      const uri =
          'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443?security=none#%E6%9D%B1%E4%BA%AC%E3%82%B5%E3%83%BC%E3%83%90%E3%83%BC';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      // Decoded Japanese characters
      expect(config.remark, isNotNull);
      expect(config.remark!.isNotEmpty, isTrue);
    });
  });

  group('VlessParser - empty remark', () {
    test('handles empty fragment as null remark', () {
      const uri =
          'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443?security=none#';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNull);
    });

    test('handles missing fragment as null remark', () {
      const uri =
          'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443?security=none';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNull);
    });
  });

  group('VlessParser - error handling', () {
    test('rejects non-vless scheme', () {
      final result = parser.parse('ss://uuid@host:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('scheme must be vless://'),
      );
    });

    test('rejects missing @ separator', () {
      final result = parser.parse('vless://no-at-sign');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('missing @ separator'),
      );
    });

    test('rejects empty UUID', () {
      final result = parser.parse('vless://@example.com:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('UUID is empty'),
      );
    });

    test('rejects invalid UUID format', () {
      final result = parser.parse('vless://not-a-uuid@example.com:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('invalid UUID format'),
      );
    });

    test('rejects empty server address', () {
      final result =
          parser.parse('vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('server address is empty'),
      );
    });

    test('rejects port out of range (0)', () {
      final result = parser.parse(
        'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:0',
      );

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });

    test('rejects port out of range (70000)', () {
      final result = parser.parse(
        'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:70000',
      );

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });

    test('rejects missing port', () {
      final result = parser.parse(
        'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com',
      );

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });

    test('rejects unsupported security type', () {
      final result = parser.parse(
        'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443?security=fakesec',
      );

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('unsupported security type'),
      );
    });

    test('rejects IPv6 with missing closing bracket', () {
      final result = parser.parse(
        'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@[::1:443',
      );

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('missing closing bracket'),
      );
    });

    test('rejects non-numeric port', () {
      final result = parser.parse(
        'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:abc',
      );

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port is not a number'),
      );
    });
  });

  group('VlessParser - edge cases', () {
    test('handles whitespace around URI', () {
      const uri =
          '  vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@example.com:443?security=none  ';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
    });

    test('handles complete real-world VLESS-Reality URI', () {
      const uri = 'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890'
          '@my-server.example.com:443'
          '?encryption=none'
          '&flow=xtls-rprx-vision'
          '&security=reality'
          '&sni=www.google.com'
          '&fp=chrome'
          '&pbk=SomePublicKeyBase64Value'
          '&sid=abcd1234'
          '&type=tcp'
          '#US%20-%20Reality%20Server';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vless');
      expect(config.uuid, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890');
      expect(config.serverAddress, 'my-server.example.com');
      expect(config.port, 443);
      expect(config.additionalParams!['encryption'], 'none');
      expect(config.additionalParams!['flow'], 'xtls-rprx-vision');
      expect(config.tlsSettings!['security'], 'reality');
      expect(config.tlsSettings!['sni'], 'www.google.com');
      expect(config.tlsSettings!['fingerprint'], 'chrome');
      expect(config.tlsSettings!['publicKey'], 'SomePublicKeyBase64Value');
      expect(config.tlsSettings!['shortId'], 'abcd1234');
      expect(config.transportSettings!['type'], 'tcp');
      expect(config.remark, 'US - Reality Server');
    });

    test('parses URI with grpc transport', () {
      final uri = buildVlessUri(
        uuid: 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        host: 'grpc.example.com',
        port: 443,
        params: {
          'security': 'tls',
          'type': 'grpc',
          'path': 'myservice',
        },
        remark: 'gRPC Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['type'], 'grpc');
      expect(config.transportSettings!['path'], 'myservice');
    });
  });
}

import 'dart:convert';

import 'package:cybervpn_mobile/features/config_import/data/parsers/vmess_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:flutter_test/flutter_test.dart';

/// Helper to build a VMess URI from a JSON map.
String buildVmessUri(Map<String, dynamic> json) {
  final jsonString = jsonEncode(json);
  final encoded = base64Url.encode(utf8.encode(jsonString)).replaceAll('=', '');
  return 'vmess://$encoded';
}

/// Standard VMess JSON with all fields populated.
Map<String, dynamic> fullVmessJson({
  String v = '2',
  String ps = 'Test Server',
  String add = 'example.com',
  dynamic port = 443,
  String id = '27848739-7e62-4138-9fd3-098a63964b6b',
  dynamic aid = 0,
  String net = 'ws',
  String type = 'none',
  String host = 'cdn.example.com',
  String path = '/ws',
  String tls = 'tls',
  String sni = 'example.com',
}) {
  return {
    'v': v,
    'ps': ps,
    'add': add,
    'port': port,
    'id': id,
    'aid': aid,
    'net': net,
    'type': type,
    'host': host,
    'path': path,
    'tls': tls,
    'sni': sni,
  };
}

void main() {
  late VmessParser parser;

  setUp(() {
    parser = VmessParser();
  });

  group('VmessParser - interface', () {
    test('protocolName returns vmess', () {
      expect(parser.protocolName, 'vmess');
    });

    test('canParse returns true for vmess:// URIs', () {
      expect(parser.canParse('vmess://abc'), isTrue);
      expect(parser.canParse('VMESS://abc'), isTrue);
      expect(parser.canParse('  vmess://abc'), isTrue);
    });

    test('canParse returns false for non-vmess URIs', () {
      expect(parser.canParse('vless://abc@host:443'), isFalse);
      expect(parser.canParse('ss://abc@host:443'), isFalse);
      expect(parser.canParse('http://example.com'), isFalse);
      expect(parser.canParse('invalid'), isFalse);
    });

    test('implements VpnUriParser', () {
      expect(parser, isA<VpnUriParser>());
    });
  });

  group('VmessParser - standard VMess', () {
    test('parses complete VMess URI with all fields', () {
      final json = fullVmessJson();
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'vmess');
      expect(config.serverAddress, 'example.com');
      expect(config.port, 443);
      expect(config.uuid, '27848739-7e62-4138-9fd3-098a63964b6b');
      expect(config.remark, 'Test Server');
      expect(config.transportSettings, isNotNull);
      expect(config.transportSettings!['network'], 'ws');
      expect(config.transportSettings!['host'], 'cdn.example.com');
      expect(config.transportSettings!['path'], '/ws');
      expect(config.transportSettings!['headerType'], 'none');
      expect(config.tlsSettings, isNotNull);
      expect(config.tlsSettings!['security'], 'tls');
      expect(config.tlsSettings!['sni'], 'example.com');
      expect(config.additionalParams, isNotNull);
      expect(config.additionalParams!['alterId'], 0);
      expect(config.additionalParams!['version'], '2');
    });

    test('parses VMess URI with TCP transport', () {
      final json = fullVmessJson(
        net: 'tcp',
        host: '',
        path: '',
        tls: '',
      );
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['network'], 'tcp');
      expect(config.transportSettings!.containsKey('host'), isFalse);
      expect(config.transportSettings!.containsKey('path'), isFalse);
      expect(config.tlsSettings, isNull);
    });

    test('parses VMess URI with gRPC transport', () {
      final json = fullVmessJson(
        net: 'grpc',
        path: 'myService',
        type: 'gun',
      );
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['network'], 'grpc');
      expect(config.transportSettings!['path'], 'myService');
      expect(config.transportSettings!['headerType'], 'gun');
    });

    test('parses VMess URI with H2 transport', () {
      final json = fullVmessJson(
        net: 'h2',
        host: 'h2.example.com',
        path: '/h2path',
      );
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['network'], 'h2');
      expect(config.transportSettings!['host'], 'h2.example.com');
      expect(config.transportSettings!['path'], '/h2path');
    });

    test('parses VMess URI with KCP transport', () {
      final json = fullVmessJson(
        net: 'kcp',
        type: 'srtp',
        host: '',
        path: '',
      );
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['network'], 'kcp');
      expect(config.transportSettings!['headerType'], 'srtp');
    });
  });

  group('VmessParser - missing optional fields', () {
    test('parses VMess with only required fields', () {
      final json = {
        'add': '192.168.1.1',
        'port': 8080,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '192.168.1.1');
      expect(config.port, 8080);
      expect(config.uuid, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890');
      expect(config.remark, isNull);
      // Defaults
      expect(config.transportSettings!['network'], 'tcp');
      expect(config.transportSettings!['headerType'], 'none');
      expect(config.additionalParams!['alterId'], 0);
      expect(config.tlsSettings, isNull);
    });

    test('parses VMess without remark (ps)', () {
      final json = fullVmessJson();
      json.remove('ps');
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNull);
    });

    test('parses VMess without TLS', () {
      final json = fullVmessJson(tls: '');
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.tlsSettings, isNull);
    });

    test('parses VMess without alterId (defaults to 0)', () {
      final json = fullVmessJson();
      json.remove('aid');
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams!['alterId'], 0);
    });

    test('parses VMess without network (defaults to tcp)', () {
      final json = fullVmessJson();
      json.remove('net');
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['network'], 'tcp');
    });

    test('parses VMess without version field', () {
      final json = fullVmessJson();
      json.remove('v');
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams!.containsKey('version'), isFalse);
    });
  });

  group('VmessParser - non-standard key names', () {
    test('accepts "address" instead of "add"', () {
      final json = {
        'address': 'alt.example.com',
        'port': 443,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, 'alt.example.com');
    });

    test('accepts "uuid" instead of "id"', () {
      final json = {
        'add': 'example.com',
        'port': 443,
        'uuid': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.uuid, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890');
    });

    test('accepts "remark" instead of "ps"', () {
      final json = {
        'add': 'example.com',
        'port': 443,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'remark': 'Alt Remark',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, 'Alt Remark');
    });

    test('accepts "network" instead of "net"', () {
      final json = {
        'add': 'example.com',
        'port': 443,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'network': 'ws',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.transportSettings!['network'], 'ws');
    });

    test('accepts "alterId" instead of "aid"', () {
      final json = {
        'add': 'example.com',
        'port': 443,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'alterId': 64,
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams!['alterId'], 64);
    });

    test('accepts "server" instead of "add"', () {
      final json = {
        'server': 'server.example.com',
        'port': 443,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, 'server.example.com');
    });

    test('accepts "security" instead of "tls"', () {
      final json = {
        'add': 'example.com',
        'port': 443,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'security': 'tls',
        'sni': 'example.com',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.tlsSettings, isNotNull);
      expect(config.tlsSettings!['security'], 'tls');
      expect(config.tlsSettings!['sni'], 'example.com');
    });
  });

  group('VmessParser - port handling', () {
    test('accepts port as string', () {
      final json = fullVmessJson(port: '8443');
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.port, 8443);
    });

    test('accepts port as integer', () {
      final json = fullVmessJson(port: 443);
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.port, 443);
    });

    test('rejects port out of range (0)', () {
      final json = fullVmessJson(port: 0);
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });

    test('rejects port out of range (70000)', () {
      final json = fullVmessJson(port: 70000);
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });
  });

  group('VmessParser - alterId handling', () {
    test('accepts alterId as string', () {
      final json = fullVmessJson(aid: '64');
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams!['alterId'], 64);
    });

    test('accepts alterId as integer', () {
      final json = fullVmessJson(aid: 128);
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams!['alterId'], 128);
    });
  });

  group('VmessParser - invalid input', () {
    test('rejects non-vmess scheme', () {
      final result = parser.parse('vless://uuid@host:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('scheme must be vmess://'),
      );
    });

    test('rejects invalid base64', () {
      final result = parser.parse('vmess://!!!not-base64!!!');

      expect(result, isA<ParseFailure>());
      final message = (result as ParseFailure).message;
      expect(
        message.toLowerCase(),
        anyOf(
          contains('base64'),
          contains('decode'),
          contains('format'),
        ),
      );
    });

    test('rejects non-JSON base64 content', () {
      final encoded = base64Url.encode(utf8.encode('this is not json'));
      final result = parser.parse('vmess://$encoded');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('not valid JSON'),
      );
    });

    test('rejects base64 containing a JSON array instead of object', () {
      final encoded = base64Url.encode(utf8.encode('[1, 2, 3]'));
      final result = parser.parse('vmess://$encoded');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('must be an object'),
      );
    });

    test('rejects malformed JSON (missing closing brace)', () {
      final encoded = base64Url.encode(utf8.encode('{"add": "host"'));
      final result = parser.parse('vmess://$encoded');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('JSON'),
      );
    });

    test('rejects empty payload after scheme', () {
      final result = parser.parse('vmess://');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('empty payload'),
      );
    });

    test('rejects missing server address', () {
      final json = {
        'port': 443,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('address'),
      );
    });

    test('rejects empty server address', () {
      final json = {
        'add': '',
        'port': 443,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('address'),
      );
    });

    test('rejects missing port', () {
      final json = {
        'add': 'example.com',
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });

    test('rejects missing user ID', () {
      final json = {
        'add': 'example.com',
        'port': 443,
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('user ID'),
      );
    });

    test('rejects empty user ID', () {
      final json = {
        'add': 'example.com',
        'port': 443,
        'id': '',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('user ID'),
      );
    });
  });

  group('VmessParser - edge cases', () {
    test('handles whitespace around URI', () {
      final json = fullVmessJson();
      final uri = buildVmessUri(json);

      final result = parser.parse('  $uri  ');

      expect(result, isA<ParseSuccess>());
    });

    test('handles base64 with missing padding', () {
      final json = fullVmessJson();
      final jsonString = jsonEncode(json);
      // Encode without padding
      var encoded = base64Url.encode(utf8.encode(jsonString));
      encoded = encoded.replaceAll('=', '');
      final uri = 'vmess://$encoded';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
    });

    test('handles standard base64 (not URL-safe)', () {
      final json = fullVmessJson();
      final jsonString = jsonEncode(json);
      // Use standard base64 (not URL-safe)
      final encoded = base64.encode(utf8.encode(jsonString));
      final uri = 'vmess://$encoded';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
    });

    test('handles unicode characters in remark', () {
      final json = fullVmessJson(ps: 'Tokyo Server');
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, contains('Tokyo'));
    });

    test('handles IPv6 server address', () {
      final json = fullVmessJson(add: '::1');
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '::1');
    });

    test('handles case-insensitive scheme', () {
      final json = fullVmessJson();
      final jsonString = jsonEncode(json);
      final encoded =
          base64Url.encode(utf8.encode(jsonString)).replaceAll('=', '');
      final uri = 'VMESS://$encoded';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
    });

    test('primary key takes precedence over alias', () {
      // If both "add" and "address" are present, "add" should win
      final json = {
        'add': 'primary.example.com',
        'address': 'alias.example.com',
        'port': 443,
        'id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
      };
      final uri = buildVmessUri(json);

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, 'primary.example.com');
    });
  });
}

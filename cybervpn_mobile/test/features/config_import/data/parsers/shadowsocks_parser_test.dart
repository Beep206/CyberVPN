import 'dart:convert';

import 'package:cybervpn_mobile/features/config_import/data/parsers/shadowsocks_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:flutter_test/flutter_test.dart';

/// Helper to build a standard SS URI: ss://BASE64(method:password)@host:port#remark
String buildStandardUri({
  required String method,
  required String password,
  required String host,
  required int port,
  String? remark,
}) {
  final userinfo = base64Url.encode(utf8.encode('$method:$password'));
  final fragment = remark != null ? '#${Uri.encodeComponent(remark)}' : '';
  return 'ss://$userinfo@$host:$port$fragment';
}

/// Helper to build a legacy SS URI: ss://BASE64(method:password@host:port)#remark
String buildLegacyUri({
  required String method,
  required String password,
  required String host,
  required int port,
  String? remark,
}) {
  final payload = '$method:$password@$host:$port';
  final encoded = base64Url.encode(utf8.encode(payload));
  final fragment = remark != null ? '#${Uri.encodeComponent(remark)}' : '';
  return 'ss://$encoded$fragment';
}

/// Helper to build a SIP002 URI: ss://BASE64(method:password)@host:port/?plugin=...#remark
String buildSip002Uri({
  required String method,
  required String password,
  required String host,
  required int port,
  String? plugin,
  Map<String, String>? queryParams,
  String? remark,
}) {
  final userinfo = base64Url.encode(utf8.encode('$method:$password'));
  final fragment = remark != null ? '#${Uri.encodeComponent(remark)}' : '';

  var query = '';
  if (plugin != null || (queryParams != null && queryParams.isNotEmpty)) {
    final params = <String, String>{};
    if (plugin != null) params['plugin'] = plugin;
    if (queryParams != null) params.addAll(queryParams);
    query =
        '/?${params.entries.map((e) => '${e.key}=${Uri.encodeComponent(e.value)}').join('&')}';
  }

  return 'ss://$userinfo@$host:$port$query$fragment';
}

void main() {
  late ShadowsocksParser parser;

  setUp(() {
    parser = ShadowsocksParser();
  });

  group('ShadowsocksParser - interface', () {
    test('protocolName returns ss', () {
      expect(parser.protocolName, 'ss');
    });

    test('canParse returns true for ss:// URIs', () {
      expect(parser.canParse('ss://abc@host:443'), isTrue);
      expect(parser.canParse('SS://abc@host:443'), isTrue);
      expect(parser.canParse('  ss://abc@host:443'), isTrue);
    });

    test('canParse returns false for non-ss URIs', () {
      expect(parser.canParse('vless://abc@host:443'), isFalse);
      expect(parser.canParse('vmess://abc@host:443'), isFalse);
      expect(parser.canParse('http://example.com'), isFalse);
      expect(parser.canParse('invalid'), isFalse);
    });

    test('implements VpnUriParser', () {
      expect(parser, isA<VpnUriParser>());
    });
  });

  group('ShadowsocksParser - standard format', () {
    test('parses valid URI with all fields', () {
      final uri = buildStandardUri(
        method: 'aes-256-gcm',
        password: 'testpassword',
        host: 'example.com',
        port: 8388,
        remark: 'My Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'shadowsocks');
      expect(config.serverAddress, 'example.com');
      expect(config.port, 8388);
      expect(config.uuid, 'aes-256-gcm'); // method in uuid field
      expect(config.password, 'testpassword');
      expect(config.remark, 'My Server');
    });

    test('parses URI without remark', () {
      final uri = buildStandardUri(
        method: 'aes-128-gcm',
        password: 'pass123',
        host: '192.168.1.1',
        port: 443,
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNull);
      expect(config.uuid, 'aes-128-gcm');
      expect(config.password, 'pass123');
      expect(config.serverAddress, '192.168.1.1');
      expect(config.port, 443);
    });

    test('parses URI with chacha20-ietf-poly1305', () {
      final uri = buildStandardUri(
        method: 'chacha20-ietf-poly1305',
        password: 'strongpass!@#',
        host: 'vpn.example.org',
        port: 8080,
        remark: 'ChaCha Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.uuid, 'chacha20-ietf-poly1305');
      expect(config.password, 'strongpass!@#');
    });

    test('parses URI with URL-encoded remark containing special characters', () {
      final uri = buildStandardUri(
        method: 'aes-256-gcm',
        password: 'pass',
        host: 'example.com',
        port: 443,
        remark: 'Server #1 (US)',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, 'Server #1 (US)');
    });

    test('parses URI with various AEAD 2022 ciphers', () {
      for (final method in [
        '2022-blake3-aes-128-gcm',
        '2022-blake3-aes-256-gcm',
        '2022-blake3-chacha20-poly1305',
      ]) {
        final uri = buildStandardUri(
          method: method,
          password: 'key123',
          host: 'example.com',
          port: 8388,
        );

        final result = parser.parse(uri);
        expect(result, isA<ParseSuccess>(), reason: 'Failed for method $method');
        final config = (result as ParseSuccess).config;
        expect(config.uuid, method);
      }
    });
  });

  group('ShadowsocksParser - legacy format', () {
    test('parses legacy base64-encoded URI', () {
      final uri = buildLegacyUri(
        method: 'aes-256-gcm',
        password: 'mypassword',
        host: 'server.example.com',
        port: 8388,
        remark: 'Legacy Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'shadowsocks');
      expect(config.serverAddress, 'server.example.com');
      expect(config.port, 8388);
      expect(config.uuid, 'aes-256-gcm');
      expect(config.password, 'mypassword');
      expect(config.remark, 'Legacy Server');
    });

    test('parses legacy URI without remark', () {
      final uri = buildLegacyUri(
        method: 'chacha20-ietf-poly1305',
        password: 'pass',
        host: '10.0.0.1',
        port: 443,
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '10.0.0.1');
      expect(config.port, 443);
      expect(config.remark, isNull);
    });
  });

  group('ShadowsocksParser - SIP002 format', () {
    test('parses SIP002 URI without plugin', () {
      final uri = buildSip002Uri(
        method: 'aes-256-gcm',
        password: 'pass',
        host: 'example.com',
        port: 8388,
        remark: 'SIP002 Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'shadowsocks');
      expect(config.serverAddress, 'example.com');
      expect(config.port, 8388);
      expect(config.uuid, 'aes-256-gcm');
      expect(config.password, 'pass');
      expect(config.remark, 'SIP002 Server');
    });

    test('parses SIP002 URI with obfs-local plugin', () {
      final uri = buildSip002Uri(
        method: 'aes-256-gcm',
        password: 'pass123',
        host: 'example.com',
        port: 443,
        plugin: 'obfs-local;obfs=http;obfs-host=www.google.com',
        remark: 'Obfs Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams, isNotNull);
      expect(
        config.additionalParams!['plugin'],
        'obfs-local;obfs=http;obfs-host=www.google.com',
      );
      expect(config.remark, 'Obfs Server');
    });

    test('parses SIP002 URI with v2ray-plugin', () {
      final uri = buildSip002Uri(
        method: 'chacha20-ietf-poly1305',
        password: 'secret',
        host: 'cdn.example.com',
        port: 443,
        plugin: 'v2ray-plugin;mode=websocket;host=cdn.example.com;path=/ws',
        remark: 'V2Ray Plugin',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams, isNotNull);
      expect(
        config.additionalParams!['plugin'],
        contains('v2ray-plugin'),
      );
    });

    test('parses SIP002 URI with IPv6 address', () {
      final userinfo =
          base64Url.encode(utf8.encode('aes-256-gcm:password'));
      final uri = 'ss://$userinfo@[::1]:8388#IPv6%20Server';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '::1');
      expect(config.port, 8388);
      expect(config.remark, 'IPv6 Server');
    });
  });

  group('ShadowsocksParser - error handling', () {
    test('rejects non-ss scheme', () {
      final result = parser.parse('vless://uuid@host:443');

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('scheme must be ss://'),
      );
    });

    test('rejects invalid base64 encoding', () {
      final result = parser.parse('ss://!!!invalid!!!@host:443');

      expect(result, isA<ParseFailure>());
      final message = (result as ParseFailure).message;
      expect(
        message.toLowerCase(),
        anyOf(
          contains('base64'),
          contains('format'),
        ),
      );
    });

    test('rejects unsupported encryption method', () {
      final userinfo =
          base64Url.encode(utf8.encode('fake-cipher-256:password'));
      final uri = 'ss://$userinfo@host:443';

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('Unsupported encryption method'),
      );
    });

    test('rejects port out of range (0)', () {
      final userinfo =
          base64Url.encode(utf8.encode('aes-256-gcm:password'));
      final uri = 'ss://$userinfo@host:0';

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });

    test('rejects port out of range (70000)', () {
      final userinfo =
          base64Url.encode(utf8.encode('aes-256-gcm:password'));
      final uri = 'ss://$userinfo@host:70000';

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('port'),
      );
    });

    test('rejects URI with missing host:port separator', () {
      final userinfo =
          base64Url.encode(utf8.encode('aes-256-gcm:password'));
      final uri = 'ss://$userinfo@hostonly';

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
    });

    test('rejects URI with empty password', () {
      final userinfo = base64Url.encode(utf8.encode('aes-256-gcm:'));
      final uri = 'ss://$userinfo@host:443';

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('password is empty'),
      );
    });

    test('rejects URI with empty method', () {
      final userinfo = base64Url.encode(utf8.encode(':password'));
      final uri = 'ss://$userinfo@host:443';

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('method'),
      );
    });

    test('rejects empty URI after scheme', () {
      final result = parser.parse('ss://');

      expect(result, isA<ParseFailure>());
    });
  });

  group('ShadowsocksParser - edge cases', () {
    test('handles whitespace around URI', () {
      final uri = buildStandardUri(
        method: 'aes-256-gcm',
        password: 'pass',
        host: 'example.com',
        port: 443,
      );

      final result = parser.parse('  $uri  ');

      expect(result, isA<ParseSuccess>());
    });

    test('handles password containing colons', () {
      // Password "pass:word:123" — only first colon separates method from password
      final userinfo =
          base64Url.encode(utf8.encode('aes-256-gcm:pass:word:123'));
      final uri = 'ss://$userinfo@host:443#test';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.password, 'pass:word:123');
    });

    test('handles base64 with missing padding', () {
      // Manually create base64 without padding
      final raw = utf8.encode('aes-256-gcm:password');
      var encoded = base64Url.encode(raw);
      // Remove padding
      encoded = encoded.replaceAll('=', '');
      final uri = 'ss://$encoded@example.com:8388';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.uuid, 'aes-256-gcm');
      expect(config.password, 'password');
    });

    test('handles unicode remark', () {
      final uri = buildStandardUri(
        method: 'aes-256-gcm',
        password: 'pass',
        host: 'example.com',
        port: 443,
        remark: 'Tokyo Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, contains('Tokyo'));
    });
  });
}

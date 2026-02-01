import 'dart:convert';

import 'package:cybervpn_mobile/features/config_import/data/parsers/shadowsocks_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/parsers/vpn_uri_parser.dart';
import 'package:flutter_test/flutter_test.dart';

/// Helper to build a SIP002 ss:// URI.
String _sip002Uri({
  required String method,
  required String password,
  required String host,
  required int port,
  String? plugin,
  String? remark,
}) {
  final userinfo =
      base64Url.encode(utf8.encode('$method:$password')).replaceAll('=', '');
  final hostPart = host.contains(':') ? '[$host]' : host;
  final queryPart = plugin != null
      ? '/?plugin=${Uri.encodeComponent(plugin)}'
      : '';
  final fragmentPart =
      remark != null ? '#${Uri.encodeComponent(remark)}' : '';
  return 'ss://$userinfo@$hostPart:$port$queryPart$fragmentPart';
}

/// Helper to build a legacy ss:// URI (entire payload base64-encoded).
String _legacyUri({
  required String method,
  required String password,
  required String host,
  required int port,
  String? remark,
}) {
  final payload = '$method:$password@$host:$port';
  final encoded =
      base64Url.encode(utf8.encode(payload)).replaceAll('=', '');
  final fragmentPart =
      remark != null ? '#${Uri.encodeComponent(remark)}' : '';
  return 'ss://$encoded$fragmentPart';
}

/// Real-world Shadowsocks URI integration tests.
///
/// These URIs simulate configurations from popular providers and clients
/// (Outline, Shadowsocks-rust, Clash, Surge). Focus is on realistic
/// cipher/password combinations and SIP002 plugin configurations.
void main() {
  late ShadowsocksParser parser;

  setUp(() {
    parser = ShadowsocksParser();
  });

  // ---------------------------------------------------------------------------
  // Real-world SIP002 format (modern standard)
  // ---------------------------------------------------------------------------
  group('Shadowsocks - real-world SIP002 configs', () {
    test('Outline server with aes-256-gcm (most common)', () {
      final uri = _sip002Uri(
        method: 'aes-256-gcm',
        password: 'kDbX9cFTu8TTOeVq',
        host: 'outline.example.com',
        port: 443,
        remark: 'Outline-US-East',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'shadowsocks');
      expect(config.serverAddress, 'outline.example.com');
      expect(config.port, 443);
      expect(config.uuid, 'aes-256-gcm');
      expect(config.password, 'kDbX9cFTu8TTOeVq');
      expect(config.remark, 'Outline-US-East');
    });

    test('chacha20-ietf-poly1305 on mobile-friendly port', () {
      final uri = _sip002Uri(
        method: 'chacha20-ietf-poly1305',
        password: 'MyStrongP@ssw0rd!',
        host: '185.199.110.153',
        port: 8388,
        remark: 'SG-ChaCha20',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.uuid, 'chacha20-ietf-poly1305');
      expect(config.password, 'MyStrongP@ssw0rd!');
      expect(config.serverAddress, '185.199.110.153');
      expect(config.port, 8388);
    });

    test('2022-blake3-aes-256-gcm (modern AEAD 2022 cipher)', () {
      final uri = _sip002Uri(
        method: '2022-blake3-aes-256-gcm',
        password: 'base64EncodedKey123456789012345678901234567890==',
        host: 'ss-2022.example.net',
        port: 8388,
        remark: 'SS-2022-Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.uuid, '2022-blake3-aes-256-gcm');
    });

    test('2022-blake3-chacha20-poly1305', () {
      final uri = _sip002Uri(
        method: '2022-blake3-chacha20-poly1305',
        password: 'shortkey',
        host: 'chacha-2022.example.com',
        port: 51820,
        remark: 'ChaCha-2022',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.uuid, '2022-blake3-chacha20-poly1305');
      expect(config.port, 51820);
    });

    test('xchacha20-ietf-poly1305', () {
      final uri = _sip002Uri(
        method: 'xchacha20-ietf-poly1305',
        password: 'XChaChaPass',
        host: 'xchacha.example.com',
        port: 9090,
        remark: 'XChaCha-Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.uuid, 'xchacha20-ietf-poly1305');
    });
  });

  // ---------------------------------------------------------------------------
  // SIP002 with plugins
  // ---------------------------------------------------------------------------
  group('Shadowsocks - SIP002 with plugins', () {
    test('obfs-local HTTP obfuscation (Android Outline)', () {
      final uri = _sip002Uri(
        method: 'aes-256-gcm',
        password: 'obfspass',
        host: 'obfs.example.com',
        port: 443,
        plugin: 'obfs-local;obfs=http;obfs-host=www.microsoft.com',
        remark: 'Obfs-HTTP',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams, isNotNull);
      expect(
        config.additionalParams!['plugin'],
        'obfs-local;obfs=http;obfs-host=www.microsoft.com',
      );
      expect(config.remark, 'Obfs-HTTP');
    });

    test('obfs-local TLS obfuscation', () {
      final uri = _sip002Uri(
        method: 'chacha20-ietf-poly1305',
        password: 'tlsobfs',
        host: 'obfs-tls.example.com',
        port: 443,
        plugin: 'obfs-local;obfs=tls;obfs-host=www.google.com',
        remark: 'Obfs-TLS',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams!['plugin'], contains('obfs=tls'));
    });

    test('v2ray-plugin WebSocket mode', () {
      final uri = _sip002Uri(
        method: 'aes-256-gcm',
        password: 'v2raypass',
        host: 'v2ray-plugin.example.com',
        port: 443,
        plugin:
            'v2ray-plugin;mode=websocket;host=cdn.example.com;path=/v2ray;tls',
        remark: 'V2Ray-WS-Plugin',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.additionalParams!['plugin'], contains('v2ray-plugin'));
      expect(config.additionalParams!['plugin'], contains('mode=websocket'));
    });
  });

  // ---------------------------------------------------------------------------
  // Legacy format (full base64 encoded)
  // ---------------------------------------------------------------------------
  group('Shadowsocks - real-world legacy format', () {
    test('Legacy aes-256-gcm URI', () {
      final uri = _legacyUri(
        method: 'aes-256-gcm',
        password: 'legacypass123',
        host: 'legacy.example.com',
        port: 8388,
        remark: 'Legacy-Server',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.protocol, 'shadowsocks');
      expect(config.serverAddress, 'legacy.example.com');
      expect(config.port, 8388);
      expect(config.uuid, 'aes-256-gcm');
      expect(config.password, 'legacypass123');
      expect(config.remark, 'Legacy-Server');
    });

    test('Legacy chacha20-ietf-poly1305 without remark', () {
      final uri = _legacyUri(
        method: 'chacha20-ietf-poly1305',
        password: 'noname',
        host: '10.0.0.1',
        port: 443,
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNull);
      expect(config.serverAddress, '10.0.0.1');
    });

    test('Legacy format with IP address', () {
      final uri = _legacyUri(
        method: 'aes-128-gcm',
        password: 'ippass',
        host: '203.0.113.42',
        port: 9999,
        remark: 'IP-Legacy',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '203.0.113.42');
      expect(config.port, 9999);
    });
  });

  // ---------------------------------------------------------------------------
  // IPv6 servers
  // ---------------------------------------------------------------------------
  group('Shadowsocks - IPv6 servers', () {
    test('SIP002 with IPv6 address', () {
      final uri = _sip002Uri(
        method: 'aes-256-gcm',
        password: 'ipv6pass',
        host: '::1',
        port: 8388,
        remark: 'IPv6-SS',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '::1');
      expect(config.port, 8388);
    });

    test('SIP002 with full IPv6 address', () {
      final uri = _sip002Uri(
        method: 'aes-256-gcm',
        password: 'fullipv6pass',
        host: '2001:db8:85a3::8a2e:370:7334',
        port: 443,
        remark: 'Full-IPv6',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.serverAddress, '2001:db8:85a3::8a2e:370:7334');
    });
  });

  // ---------------------------------------------------------------------------
  // URL-encoded and international remarks
  // ---------------------------------------------------------------------------
  group('Shadowsocks - encoded remarks', () {
    test('Japanese characters in remark', () {
      final uri = _sip002Uri(
        method: 'aes-256-gcm',
        password: 'jppass',
        host: 'jp.example.com',
        port: 443,
        remark: '\u6771\u4EAC\u30B5\u30FC\u30D0\u30FC',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, isNotNull);
      expect(config.remark!.isNotEmpty, isTrue);
    });

    test('Remark with spaces and special characters', () {
      final uri = _sip002Uri(
        method: 'aes-256-gcm',
        password: 'specialpass',
        host: 'example.com',
        port: 443,
        remark: 'Server #1 (US) - Premium',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.remark, 'Server #1 (US) - Premium');
    });
  });

  // ---------------------------------------------------------------------------
  // Password edge cases
  // ---------------------------------------------------------------------------
  group('Shadowsocks - password edge cases', () {
    test('Password containing colons', () {
      final userinfo = base64Url
          .encode(utf8.encode('aes-256-gcm:pass:with:colons'))
          .replaceAll('=', '');
      final uri = 'ss://$userinfo@host.com:443#Colon-Pass';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.password, 'pass:with:colons');
    });

    test('Base64 password (common in SS 2022)', () {
      final uri = _sip002Uri(
        method: '2022-blake3-aes-256-gcm',
        password: 'dGhpcyBpcyBhIGJhc2U2NCBrZXk=',
        host: 'ss2022.example.com',
        port: 8388,
        remark: 'SS2022-B64Key',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.password, 'dGhpcyBpcyBhIGJhc2U2NCBrZXk=');
    });

    test('Long random password (Outline generates 24-char random passwords)', () {
      final uri = _sip002Uri(
        method: 'aes-256-gcm',
        password: 'kDbX9cFTu8TTOeVqA1B2C3D4',
        host: 'outline.example.com',
        port: 12345,
        remark: 'Long-Pass',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.password!.length, 24);
    });
  });

  // ---------------------------------------------------------------------------
  // Base64 encoding edge cases
  // ---------------------------------------------------------------------------
  group('Shadowsocks - base64 encoding variants', () {
    test('Standard base64 (not URL-safe) with padding', () {
      // Some older clients use standard base64 with + and /
      final raw = utf8.encode('aes-256-gcm:testpassword');
      final encoded = base64.encode(raw); // Standard with padding
      final uri = 'ss://$encoded@example.com:8388#Standard-B64';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.uuid, 'aes-256-gcm');
      expect(config.password, 'testpassword');
    });

    test('URL-safe base64 without padding', () {
      final raw = utf8.encode('aes-256-gcm:nopadding');
      var encoded = base64Url.encode(raw);
      encoded = encoded.replaceAll('=', '');
      final uri = 'ss://$encoded@example.com:8388#NoPad';

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.password, 'nopadding');
    });
  });

  // ---------------------------------------------------------------------------
  // Error scenarios from real-world bad configs
  // ---------------------------------------------------------------------------
  group('Shadowsocks - real-world error scenarios', () {
    test('Unsupported cipher from old config', () {
      final uri = _sip002Uri(
        method: 'bf-cfb',
        password: 'oldpass',
        host: 'old.example.com',
        port: 443,
        remark: 'Old-Cipher',
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('Unsupported encryption method'),
      );
    });

    test('Empty password in base64', () {
      final userinfo =
          base64Url.encode(utf8.encode('aes-256-gcm:')).replaceAll('=', '');
      final uri = 'ss://$userinfo@host.com:443';

      final result = parser.parse(uri);

      expect(result, isA<ParseFailure>());
      expect(
        (result as ParseFailure).message,
        contains('password is empty'),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Cross-field consistency
  // ---------------------------------------------------------------------------
  group('Shadowsocks - cross-field consistency', () {
    test('all parsed configs have protocol set to shadowsocks', () {
      final methods = [
        'aes-256-gcm',
        'aes-128-gcm',
        'chacha20-ietf-poly1305',
        '2022-blake3-aes-256-gcm',
      ];

      for (final method in methods) {
        final uri = _sip002Uri(
          method: method,
          password: 'pass',
          host: 'host.com',
          port: 443,
        );
        final result = parser.parse(uri);
        expect(result, isA<ParseSuccess>(), reason: 'Failed for: $method');
        final config = (result as ParseSuccess).config;
        expect(config.protocol, 'shadowsocks');
      }
    });

    test('encryption method is stored in uuid field', () {
      final uri = _sip002Uri(
        method: 'aes-256-gcm',
        password: 'pass',
        host: 'host.com',
        port: 443,
      );

      final result = parser.parse(uri);

      expect(result, isA<ParseSuccess>());
      final config = (result as ParseSuccess).config;
      expect(config.uuid, 'aes-256-gcm');
    });
  });
}

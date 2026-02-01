import 'dart:convert';

import 'package:cybervpn_mobile/features/config_import/data/parsers/subscription_url_parser.dart';
import 'package:cybervpn_mobile/features/config_import/domain/entities/imported_config.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// --- Mocks ---

class MockDio extends Mock implements Dio {}

// --- Helpers ---

/// Build a base64-encoded subscription body from a list of VPN URIs.
String buildBase64Subscription(List<String> uris) {
  final joined = uris.join('\n');
  return base64.encode(utf8.encode(joined));
}

/// A valid VLESS URI for testing.
String vlessUri({String host = 'vless.example.com', int port = 443}) {
  return 'vless://a1b2c3d4-e5f6-7890-abcd-ef1234567890@$host:$port'
      '?security=tls&type=ws#VLESS-$host';
}

/// A valid Trojan URI for testing.
String trojanUri({String host = 'trojan.example.com', int port = 443}) {
  return 'trojan://mypassword@$host:$port#Trojan-$host';
}

/// A valid Shadowsocks URI for testing.
String ssUri({String host = 'ss.example.com', int port = 8388}) {
  final userinfo = base64.encode(utf8.encode('aes-256-gcm:mypassword'));
  return 'ss://$userinfo@$host:$port#SS-$host';
}

void main() {
  late MockDio mockDio;
  late SubscriptionUrlParser parser;

  setUp(() {
    mockDio = MockDio();
    parser = SubscriptionUrlParser(dio: mockDio);
  });

  /// Helper to set up a successful Dio GET response with the given body.
  void stubDioGet(String url, String responseBody) {
    when(() => mockDio.get<String>(
          url,
          options: any(named: 'options'),
        )).thenAnswer(
      (_) async => Response<String>(
        data: responseBody,
        statusCode: 200,
        requestOptions: RequestOptions(path: url),
      ),
    );
  }

  /// Helper to set up a Dio GET that throws a DioException.
  void stubDioError(String url, DioExceptionType type, {int? statusCode}) {
    when(() => mockDio.get<String>(
          url,
          options: any(named: 'options'),
        )).thenThrow(
      DioException(
        type: type,
        requestOptions: RequestOptions(path: url),
        response: statusCode != null
            ? Response<String>(
                statusCode: statusCode,
                requestOptions: RequestOptions(path: url),
              )
            : null,
      ),
    );
  }

  group('SubscriptionUrlParser - successful parsing', () {
    test('parses base64 subscription with 3 valid configs', () async {
      const url = 'https://example.com/sub';
      final uris = [
        vlessUri(),
        trojanUri(),
        ssUri(),
      ];
      final body = buildBase64Subscription(uris);
      stubDioGet(url, body);

      final result = await parser.parse(url);

      expect(result.configs.length, 3);
      expect(result.errors, isEmpty);
      expect(result.isFullSuccess, isTrue);
      expect(result.configs[0].protocol, 'vless');
      expect(result.configs[0].serverAddress, 'vless.example.com');
      expect(result.configs[1].protocol, 'trojan');
      expect(result.configs[1].serverAddress, 'trojan.example.com');
      expect(result.configs[2].protocol, 'shadowsocks');
      expect(result.configs[2].serverAddress, 'ss.example.com');
    });

    test('sets ImportSource.subscriptionUrl on all configs', () async {
      const url = 'https://example.com/sub';
      final body = buildBase64Subscription([vlessUri()]);
      stubDioGet(url, body);

      final result = await parser.parse(url);

      expect(result.configs.first.source, ImportSource.subscriptionUrl);
      expect(result.configs.first.subscriptionUrl, url);
    });

    test('handles plain text (non-base64) subscription responses', () async {
      const url = 'https://example.com/sub-plain';
      final plainBody = [vlessUri(), trojanUri()].join('\n');
      stubDioGet(url, plainBody);

      final result = await parser.parse(url);

      expect(result.configs.length, 2);
      expect(result.errors, isEmpty);
    });

    test('skips empty lines in subscription content', () async {
      const url = 'https://example.com/sub';
      final uris = [vlessUri(), '', '   ', trojanUri()];
      final body = buildBase64Subscription(uris);
      stubDioGet(url, body);

      final result = await parser.parse(url);

      expect(result.configs.length, 2);
      expect(result.errors, isEmpty);
    });

    test('handles Windows-style line endings (CRLF)', () async {
      const url = 'https://example.com/sub';
      final content = '${vlessUri()}\r\n${trojanUri()}\r\n';
      final body = base64.encode(utf8.encode(content));
      stubDioGet(url, body);

      final result = await parser.parse(url);

      expect(result.configs.length, 2);
    });
  });

  group('SubscriptionUrlParser - mixed valid/invalid URIs', () {
    test('returns valid configs and error list for mixed content', () async {
      const url = 'https://example.com/sub';
      final uris = [
        vlessUri(),
        'invalid://not-a-vpn-uri',
        trojanUri(),
      ];
      final body = buildBase64Subscription(uris);
      stubDioGet(url, body);

      final result = await parser.parse(url);

      expect(result.configs.length, 2);
      expect(result.errors.length, 1);
      expect(result.isPartialSuccess, isTrue);
      expect(result.errors.first.lineNumber, 2);
      expect(result.errors.first.rawUri, 'invalid://not-a-vpn-uri');
    });

    test('returns all errors when no URIs are valid', () async {
      const url = 'https://example.com/sub';
      final uris = [
        'invalid://one',
        'garbage://two',
        'nope://three',
      ];
      final body = buildBase64Subscription(uris);
      stubDioGet(url, body);

      final result = await parser.parse(url);

      expect(result.configs, isEmpty);
      expect(result.errors.length, 3);
      expect(result.isFailure, isTrue);
    });
  });

  group('SubscriptionUrlParser - HTTP errors', () {
    test('throws SubscriptionFetchException on HTTP 404', () async {
      const url = 'https://example.com/sub';
      stubDioError(url, DioExceptionType.badResponse, statusCode: 404);

      expect(
        () => parser.parse(url),
        throwsA(isA<SubscriptionFetchException>().having(
          (e) => e.message,
          'message',
          contains('HTTP 404'),
        )),
      );
    });

    test('throws SubscriptionFetchException on HTTP 500', () async {
      const url = 'https://example.com/sub';
      stubDioError(url, DioExceptionType.badResponse, statusCode: 500);

      expect(
        () => parser.parse(url),
        throwsA(isA<SubscriptionFetchException>().having(
          (e) => e.url,
          'url',
          url,
        )),
      );
    });

    test('throws SubscriptionFetchException on connection timeout', () async {
      const url = 'https://example.com/sub';
      stubDioError(url, DioExceptionType.connectionTimeout);

      expect(
        () => parser.parse(url),
        throwsA(isA<SubscriptionFetchException>()),
      );
    });

    test('throws SubscriptionFetchException for invalid URL format', () async {
      expect(
        () => parser.parse('not-a-url'),
        throwsA(isA<SubscriptionFetchException>().having(
          (e) => e.message,
          'message',
          contains('Invalid subscription URL format'),
        )),
      );
    });

    test('throws SubscriptionFetchException for empty response', () async {
      const url = 'https://example.com/sub';
      stubDioGet(url, '   ');

      expect(
        () => parser.parse(url),
        throwsA(isA<SubscriptionFetchException>().having(
          (e) => e.message,
          'message',
          contains('Empty response body'),
        )),
      );
    });
  });

  group('SubscriptionUrlParser - base64 decoding', () {
    test('throws SubscriptionDecodeException for invalid base64', () async {
      const url = 'https://example.com/sub';
      // Content that is neither valid base64 nor VPN URIs
      stubDioGet(url, '!!!not-base64-and-not-vpn-uris!!!');

      expect(
        () => parser.parse(url),
        throwsA(isA<SubscriptionDecodeException>().having(
          (e) => e.message,
          'message',
          contains('not valid base64'),
        )),
      );
    });

    test('handles base64url encoding (URL-safe characters)', () async {
      const url = 'https://example.com/sub';
      final content = vlessUri();
      // Encode with standard base64, then replace to url-safe
      final encoded = base64.encode(utf8.encode(content))
          .replaceAll('+', '-')
          .replaceAll('/', '_')
          .replaceAll('=', ''); // Remove padding
      stubDioGet(url, encoded);

      final result = await parser.parse(url);

      expect(result.configs.length, 1);
    });
  });

  group('SubscriptionUrlParser - edge cases', () {
    test('handles subscription with single config', () async {
      const url = 'https://example.com/sub';
      final body = buildBase64Subscription([vlessUri()]);
      stubDioGet(url, body);

      final result = await parser.parse(url);

      expect(result.configs.length, 1);
      expect(result.isFullSuccess, isTrue);
    });

    test('generates deterministic IDs for same URI', () async {
      const url = 'https://example.com/sub';
      final uri = vlessUri();
      final body = buildBase64Subscription([uri]);
      stubDioGet(url, body);

      final result1 = await parser.parse(url);
      final result2 = await parser.parse(url);

      expect(result1.configs.first.id, result2.configs.first.id);
    });

    test('generates unique IDs for different URIs', () async {
      const url = 'https://example.com/sub';
      final uris = [
        vlessUri(host: 'server1.com'),
        vlessUri(host: 'server2.com'),
      ];
      final body = buildBase64Subscription(uris);
      stubDioGet(url, body);

      final result = await parser.parse(url);

      expect(result.configs[0].id, isNot(result.configs[1].id));
    });

    test('uses remark as name when available', () async {
      const url = 'https://example.com/sub';
      final body = buildBase64Subscription([vlessUri()]);
      stubDioGet(url, body);

      final result = await parser.parse(url);

      // The vlessUri has #VLESS-vless.example.com as remark
      expect(result.configs.first.name, contains('VLESS'));
    });
  });
}

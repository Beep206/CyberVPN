import 'dart:convert';

import 'package:cybervpn_mobile/core/auth/jwt_parser.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('JwtParser', () {
    // Helper to create a JWT token with a given payload
    String createJwt(Map<String, dynamic> payload) {
      final header = base64Url.encode(
        utf8.encode(jsonEncode({'alg': 'HS256', 'typ': 'JWT'})),
      );
      final payloadEncoded = base64Url.encode(utf8.encode(jsonEncode(payload)));
      // Fake signature (not verified by parser)
      const signature = 'fake_signature';
      return '$header.$payloadEncoded.$signature';
    }

    group('parse', () {
      test('parses valid JWT with all fields', () {
        final expTime = DateTime.now().add(const Duration(hours: 1));
        final iatTime = DateTime.now();
        final token = createJwt({
          'exp': expTime.millisecondsSinceEpoch ~/ 1000,
          'iat': iatTime.millisecondsSinceEpoch ~/ 1000,
          'sub': 'user-123',
          'type': 'access',
        });

        final payload = JwtParser.parse(token);

        expect(payload, isNotNull);
        expect(payload!.sub, 'user-123');
        expect(payload.type, 'access');
        expect(payload.isExpired, false);
      });

      test('parses JWT with only exp field', () {
        final expTime = DateTime.now().add(const Duration(hours: 1));
        final token = createJwt({
          'exp': expTime.millisecondsSinceEpoch ~/ 1000,
        });

        final payload = JwtParser.parse(token);

        expect(payload, isNotNull);
        expect(payload!.sub, isNull);
        expect(payload.type, isNull);
        expect(payload.isExpired, false);
      });

      test('returns null for token without exp field', () {
        final token = createJwt({
          'sub': 'user-123',
        });

        final payload = JwtParser.parse(token);

        expect(payload, isNull);
      });

      test('returns null for malformed token (wrong number of parts)', () {
        expect(JwtParser.parse('not.a.valid.jwt'), isNull);
        expect(JwtParser.parse('only.two'), isNull);
        expect(JwtParser.parse('single'), isNull);
      });

      test('returns null for token with invalid base64', () {
        expect(JwtParser.parse('header.!!!invalid!!!.signature'), isNull);
      });

      test('returns null for empty string', () {
        expect(JwtParser.parse(''), isNull);
      });
    });

    group('JwtPayload', () {
      test('isExpired returns true for expired token', () {
        final expTime = DateTime.now().subtract(const Duration(hours: 1));
        final token = createJwt({
          'exp': expTime.millisecondsSinceEpoch ~/ 1000,
        });

        final payload = JwtParser.parse(token);

        expect(payload, isNotNull);
        expect(payload!.isExpired, true);
      });

      test('isExpired returns false for valid token', () {
        final expTime = DateTime.now().add(const Duration(hours: 1));
        final token = createJwt({
          'exp': expTime.millisecondsSinceEpoch ~/ 1000,
        });

        final payload = JwtParser.parse(token);

        expect(payload, isNotNull);
        expect(payload!.isExpired, false);
      });

      test('expiresAt returns correct DateTime', () {
        final expTime =
            DateTime.now().add(const Duration(hours: 1)).toUtc();
        final expUnix = expTime.millisecondsSinceEpoch ~/ 1000;
        final token = createJwt({'exp': expUnix});

        final payload = JwtParser.parse(token);

        expect(payload, isNotNull);
        // Allow 1 second tolerance due to millisecond truncation
        expect(
          payload!.expiresAt.difference(expTime).inSeconds.abs(),
          lessThanOrEqualTo(1),
        );
      });

      test('timeUntilExpiry returns positive duration for valid token', () {
        final expTime = DateTime.now().add(const Duration(hours: 1));
        final token = createJwt({
          'exp': expTime.millisecondsSinceEpoch ~/ 1000,
        });

        final payload = JwtParser.parse(token);

        expect(payload, isNotNull);
        expect(payload!.timeUntilExpiry.isNegative, false);
        expect(payload.timeUntilExpiry.inMinutes, greaterThan(50));
      });

      test('timeUntilExpiry returns negative duration for expired token', () {
        final expTime = DateTime.now().subtract(const Duration(hours: 1));
        final token = createJwt({
          'exp': expTime.millisecondsSinceEpoch ~/ 1000,
        });

        final payload = JwtParser.parse(token);

        expect(payload, isNotNull);
        expect(payload!.timeUntilExpiry.isNegative, true);
      });
    });
  });
}

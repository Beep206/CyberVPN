import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:cybervpn_mobile/features/auth/data/services/telegram_oauth_service.dart';

void main() {
  group('TelegramOAuthService', () {
    group('constants', () {
      test('has correct bot username', () {
        expect(TelegramOAuthService.botUsername, 'CyberVPNBot');
      });

      test('has correct callback scheme', () {
        expect(TelegramOAuthService.callbackScheme, 'cybervpn');
      });

      test('has correct callback path', () {
        expect(TelegramOAuthService.callbackPath, 'telegram-auth');
      });

      test('has correct auth result param', () {
        expect(TelegramOAuthService.authResultParam, 'tg_auth_result');
      });
    });
  });

  group('TelegramAuthResult', () {
    test('creates result with all fields', () {
      final result = TelegramAuthResult(
        authData: 'base64data',
        id: 123456789,
        firstName: 'John',
        lastName: 'Doe',
        username: 'johndoe',
        photoUrl: 'https://t.me/photo.jpg',
        authDate: DateTime(2026, 1, 15),
        hash: 'abcdef123456',
      );

      expect(result.id, 123456789);
      expect(result.firstName, 'John');
      expect(result.lastName, 'Doe');
      expect(result.username, 'johndoe');
      expect(result.photoUrl, 'https://t.me/photo.jpg');
      expect(result.authData, 'base64data');
      expect(result.hash, 'abcdef123456');
    });

    test('creates result with required fields only', () {
      const result = TelegramAuthResult(
        authData: 'base64data',
        id: 123456789,
        firstName: 'John',
      );

      expect(result.id, 123456789);
      expect(result.firstName, 'John');
      expect(result.lastName, isNull);
      expect(result.username, isNull);
      expect(result.photoUrl, isNull);
    });

    test('fullName returns first name only when no last name', () {
      const result = TelegramAuthResult(
        authData: 'base64data',
        id: 123456789,
        firstName: 'John',
      );

      expect(result.fullName, 'John');
    });

    test('fullName returns full name when last name present', () {
      const result = TelegramAuthResult(
        authData: 'base64data',
        id: 123456789,
        firstName: 'John',
        lastName: 'Doe',
      );

      expect(result.fullName, 'John Doe');
    });

    test('fullName returns first name when last name is empty', () {
      const result = TelegramAuthResult(
        authData: 'base64data',
        id: 123456789,
        firstName: 'John',
        lastName: '',
      );

      expect(result.fullName, 'John');
    });

    test('toString returns readable format', () {
      const result = TelegramAuthResult(
        authData: 'base64data',
        id: 123456789,
        firstName: 'John',
        lastName: 'Doe',
        username: 'johndoe',
      );

      expect(
        result.toString(),
        'TelegramAuthResult(id: 123456789, name: John Doe, username: johndoe)',
      );
    });
  });

  group('TelegramAuthStartResult', () {
    test('has all expected values', () {
      expect(TelegramAuthStartResult.values, [
        TelegramAuthStartResult.launched,
        TelegramAuthStartResult.telegramNotInstalled,
        TelegramAuthStartResult.launchFailed,
      ]);
    });
  });

  group('Deep link parsing', () {
    test('parses valid callback URL', () {
      // Create a mock auth data JSON
      final authJson = {
        'id': 123456789,
        'first_name': 'John',
        'last_name': 'Doe',
        'username': 'johndoe',
        'photo_url': 'https://t.me/photo.jpg',
        'auth_date': 1704067200, // 2024-01-01 00:00:00 UTC
        'hash': 'abcdef123456',
      };

      // Base64 encode it
      final authData = base64Encode(utf8.encode(jsonEncode(authJson)));

      // Build callback URL
      final callbackUrl =
          'cybervpn://telegram-auth?tg_auth_result=$authData';

      // Parse the URL
      final uri = Uri.parse(callbackUrl);

      expect(uri.scheme, 'cybervpn');
      expect(uri.host, 'telegram-auth');
      expect(uri.queryParameters['tg_auth_result'], authData);

      // Decode and verify
      final decodedJson =
          jsonDecode(utf8.decode(base64Decode(authData))) as Map<String, dynamic>;
      expect(decodedJson['id'], 123456789);
      expect(decodedJson['first_name'], 'John');
    });

    test('builds correct Telegram deep link', () {
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final telegramUri = Uri(
        scheme: 'tg',
        host: 'resolve',
        queryParameters: {
          'domain': TelegramOAuthService.botUsername,
          'start': 'auth_$timestamp',
        },
      );

      expect(telegramUri.scheme, 'tg');
      expect(telegramUri.host, 'resolve');
      expect(
        telegramUri.queryParameters['domain'],
        TelegramOAuthService.botUsername,
      );
      expect(
        telegramUri.queryParameters['start'],
        startsWith('auth_'),
      );
    });
  });
}

import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/device/device_provider.dart';
import 'package:cybervpn_mobile/core/services/telegram_auth_service.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/logout_provider.dart'
    as logout_provider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../helpers/fakes/fake_api_client.dart';

class _FakeSecureStorage implements SecureStorageWrapper {
  final Map<String, String> _data = <String, String>{};

  @override
  Future<String?> read({required String key}) async => _data[key];

  @override
  Future<void> write({required String key, required String value}) async {
    _data[key] = value;
  }

  @override
  Future<void> delete({required String key}) async {
    _data.remove(key);
  }

  @override
  Future<String?> getRefreshToken() async => _data['refresh_token'];

  @override
  Future<String?> getAccessToken() async => _data['access_token'];

  @override
  Future<String> getOrCreateDeviceId() async => 'test-device-id';

  @override
  Future<void> setTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    _data['access_token'] = accessToken;
    _data['refresh_token'] = refreshToken;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  late ProviderContainer container;
  late FakeApiClient fakeApiClient;
  late _FakeSecureStorage fakeStorage;

  const testDevice = DeviceInfo(
    deviceId: 'test-device-id',
    platform: DevicePlatform.ios,
    platformId: 'ios-platform-id',
    osVersion: '17.4',
    appVersion: '1.2.3',
    deviceModel: 'iPhone 15 Pro',
  );

  setUp(() {
    fakeApiClient = FakeApiClient();
    fakeStorage = _FakeSecureStorage();
    container = ProviderContainer(
      overrides: [
        logout_provider.apiClientProvider.overrideWithValue(fakeApiClient),
        secureStorageProvider.overrideWithValue(fakeStorage),
      ],
    );
  });

  tearDown(() {
    container.dispose();
  });

  group('TelegramAuthService.authenticateWithIdToken', () {
    test('normalizes snake_case auth response and stores tokens', () async {
      fakeApiClient.setPostResponse(ApiConstants.telegramOidcAuth, {
        'tokens': {
          'access_token': 'access-token-123',
          'refresh_token': 'refresh-token-456',
          'expires_in': 900,
          'token_type': 'Bearer',
        },
        'user': {
          'id': 'user-001',
          'email': 'tg123@telegram.local',
          'username': 'tg_user',
          'telegram_id': 123456789,
          'is_email_verified': true,
          'is_premium': false,
          'created_at': '2026-04-21T06:00:00Z',
          'last_login_at': '2026-04-21T06:05:00Z',
        },
        'is_new_user': true,
      });

      final service = container.read(telegramAuthServiceProvider);
      final result = await service.authenticateWithIdToken(
        idToken: 'telegram-id-token',
        device: testDevice,
      );

      expect(result.isNewUser, isTrue);
      expect(
        result.tokens,
        equals(
          const TokenModel(
            accessToken: 'access-token-123',
            refreshToken: 'refresh-token-456',
            expiresIn: 900,
            tokenType: 'Bearer',
          ),
        ),
      );
      expect(result.user.id, equals('user-001'));
      expect(result.user.email, equals('tg123@telegram.local'));
      expect(result.user.username, equals('tg_user'));
      expect(result.user.telegramId, equals('123456789'));
      expect(await fakeStorage.getAccessToken(), equals('access-token-123'));
      expect(await fakeStorage.getRefreshToken(), equals('refresh-token-456'));
    });

    test('maps requires_2fa response to TelegramAuthException', () async {
      fakeApiClient.setPostResponse(ApiConstants.telegramOidcAuth, {
        'requires_2fa': true,
        'method': 'totp',
        'tfa_token': 'pending-token',
      });

      final service = container.read(telegramAuthServiceProvider);

      await expectLater(
        () => service.authenticateWithIdToken(
          idToken: 'telegram-id-token',
          device: testDevice,
        ),
        throwsA(
          isA<TelegramAuthException>().having(
            (e) => e.code,
            'code',
            equals('TWO_FACTOR_REQUIRED'),
          ).having(
            (e) => e.tfaToken,
            'tfaToken',
            equals('pending-token'),
          ),
        ),
      );
    });

    test('completes pending 2FA and stores tokens', () async {
      fakeApiClient.setPostResponse(ApiConstants.mobile2faComplete, {
        'tokens': {
          'access_token': 'after-2fa-access',
          'refresh_token': 'after-2fa-refresh',
          'expires_in': 900,
          'token_type': 'Bearer',
        },
        'user': {
          'id': 'user-001',
          'email': 'tg123@telegram.local',
          'username': 'tg_user',
          'telegram_id': 123456789,
          'is_email_verified': true,
          'is_premium': false,
          'created_at': '2026-04-21T06:00:00Z',
          'last_login_at': '2026-04-21T06:05:00Z',
        },
        'is_new_user': false,
      });

      final service = container.read(telegramAuthServiceProvider);
      final result = await service.completeTwoFactor(
        tfaToken: 'pending-token',
        code: '123456',
      );

      expect(result.isNewUser, isFalse);
      expect(result.tokens.accessToken, equals('after-2fa-access'));
      expect(await fakeStorage.getAccessToken(), equals('after-2fa-access'));
      expect(await fakeStorage.getRefreshToken(), equals('after-2fa-refresh'));
    });

    test('links Telegram identity for current user', () async {
      fakeApiClient.setPostResponse(ApiConstants.telegramOidcLink, {
        'linked': true,
        'provider': 'telegram',
        'telegram_username': 'tg_user',
      });

      final service = container.read(telegramAuthServiceProvider);
      await service.linkCurrentUserWithIdToken(idToken: 'telegram-id-token');
    });

    test('unlinks Telegram identity for current user', () async {
      fakeApiClient.setDeleteResponse(ApiConstants.telegramOidcLink, {
        'linked': false,
        'provider': 'telegram',
        'telegram_username': null,
      });

      final service = container.read(telegramAuthServiceProvider);
      await service.unlinkCurrentUserTelegram();
    });
  });
}

import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/device/device_provider.dart';
import 'package:cybervpn_mobile/core/device/device_service.dart';
import 'package:cybervpn_mobile/core/platform/telegram_native_auth_client.dart';
import 'package:cybervpn_mobile/core/platform/telegram_native_auth_method_channel.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';
import 'package:cybervpn_mobile/features/auth/data/models/user_model.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/features/auth/domain/repositories/auth_repository.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/telegram_auth_provider.dart';
import 'package:cybervpn_mobile/core/services/telegram_auth_service.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show authRepositoryProvider;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class _FakeAuthRepository implements AuthRepository {
  @override
  Future<Result<UserEntity?>> getCurrentUser() async => const Success(null);

  @override
  Future<Result<bool>> isAuthenticated() async => const Success(false);

  @override
  Future<Result<(UserEntity, String)>> login({
    required String email,
    required String password,
    required DeviceInfo device,
    bool rememberMe = false,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Result<(UserEntity, String)>> loginWithBotLink({
    required String token,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Result<String>> refreshToken({
    required String refreshToken,
    required String deviceId,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Result<(UserEntity, String)>> register({
    required String email,
    required String password,
    required DeviceInfo device,
    String? referralCode,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<Result<void>> logout({
    required String refreshToken,
    required String deviceId,
  }) async {
    throw UnimplementedError();
  }
}

class _FakeDeviceService implements DeviceService {
  @override
  Future<DeviceInfo> getDeviceInfo({String? pushToken}) async {
    return const DeviceInfo(
      deviceId: 'test-device-id',
      platform: DevicePlatform.android,
      platformId: 'android-platform-id',
      osVersion: '14',
      appVersion: '1.0.0',
      deviceModel: 'Pixel Test',
    );
  }

  @override
  Future<String> getDeviceId() async => 'test-device-id';

  @override
  Future<DeviceInfo> updatePushToken(String pushToken) async =>
      getDeviceInfo(pushToken: pushToken);

  @override
  void clearCache() {}

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

class _FakeTelegramNativeAuthClient implements TelegramNativeAuthClient {
  TelegramNativeAuthResult? nextResult;
  TelegramNativeAuthFailure? nextFailure;
  bool loginCalled = false;
  bool? lastRequestPhone;

  @override
  Future<TelegramNativeAuthResult> login({required bool requestPhone}) async {
    loginCalled = true;
    lastRequestPhone = requestPhone;

    final failure = nextFailure;
    if (failure != null) {
      throw failure;
    }

    return nextResult!;
  }
}

class _FakeTelegramAuthService extends TelegramAuthService {
  _FakeTelegramAuthService(super.ref);

  bool isInstalled = true;
  bool launchTelegramLoginResult = true;
  TelegramAuthResult? nextAuthResult;
  TelegramAuthException? nextAuthException;
  String? lastAuthData;
  String? lastIdToken;
  String? lastTfaToken;
  String? lastTwoFactorCode;

  @override
  Future<bool> isTelegramInstalled() async => isInstalled;

  @override
  Future<bool> launchTelegramLogin() async => launchTelegramLoginResult;

  @override
  Future<TelegramAuthResult> authenticateWithAuthData({
    required String authData,
    required DeviceInfo device,
  }) async {
    lastAuthData = authData;
    final exception = nextAuthException;
    if (exception != null) {
      throw exception;
    }
    return nextAuthResult!;
  }

  @override
  Future<TelegramAuthResult> authenticateWithIdToken({
    required String idToken,
    required DeviceInfo device,
  }) async {
    lastIdToken = idToken;
    final exception = nextAuthException;
    if (exception != null) {
      throw exception;
    }
    return nextAuthResult!;
  }

  @override
  Future<TelegramAuthResult> completeTwoFactor({
    required String tfaToken,
    required String code,
  }) async {
    lastTfaToken = tfaToken;
    lastTwoFactorCode = code;
    final exception = nextAuthException;
    if (exception != null) {
      throw exception;
    }
    return nextAuthResult!;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late ProviderContainer container;
  late _FakeTelegramNativeAuthClient fakeNativeClient;
  late _FakeTelegramAuthService fakeTelegramService;

  final testUserModel = UserModel(
    id: 'user-001',
    email: 'tg123@telegram.local',
    username: 'tg_user',
    telegramId: '123456789',
    isEmailVerified: true,
    createdAt: DateTime(2026, 4, 21, 6),
    lastLoginAt: DateTime(2026, 4, 21, 6, 5),
  );

  final testAuthResult = TelegramAuthResult(
    user: testUserModel,
    tokens: const TokenModel(
      accessToken: 'access-token-123',
      refreshToken: 'refresh-token-456',
      expiresIn: 900,
      tokenType: 'Bearer',
    ),
    isNewUser: true,
  );

  ProviderContainer createContainer({
    required bool nativeEnabled,
    required bool legacyEnabled,
    bool requestPhone = false,
  }) {
    return ProviderContainer(
      overrides: [
        authRepositoryProvider.overrideWithValue(_FakeAuthRepository()),
        deviceServiceProvider.overrideWithValue(_FakeDeviceService()),
        telegramAuthServiceProvider.overrideWith((ref) {
          fakeTelegramService = _FakeTelegramAuthService(ref);
          fakeTelegramService.nextAuthResult = testAuthResult;
          return fakeTelegramService;
        }),
        telegramNativeAuthClientProvider.overrideWithValue(fakeNativeClient),
        telegramNativeLoginEnabledProvider.overrideWithValue(nativeEnabled),
        telegramLegacyLoginAvailableProvider.overrideWithValue(legacyEnabled),
        telegramNativePhoneScopeEnabledProvider.overrideWithValue(requestPhone),
      ],
    );
  }

  setUp(() {
    fakeNativeClient = _FakeTelegramNativeAuthClient()
      ..nextResult = const TelegramNativeAuthResult(
        idToken: 'telegram-id-token',
        username: 'tg_user',
        displayName: 'Telegram User',
      );
  });

  tearDown(() {
    container.dispose();
  });

  group('TelegramAuthNotifier', () {
    test(
      'startLogin uses native flow and updates auth state on success',
      () async {
        container = createContainer(
          nativeEnabled: true,
          legacyEnabled: false,
          requestPhone: true,
        );

        await container.read(authProvider.future);

        await container.read(telegramAuthProvider.notifier).startLogin();

        final telegramState = container.read(telegramAuthProvider).requireValue;
        expect(telegramState, isA<TelegramAuthSuccess>());
        expect(fakeNativeClient.loginCalled, isTrue);
        expect(fakeNativeClient.lastRequestPhone, isTrue);
        expect(fakeTelegramService.lastIdToken, equals('telegram-id-token'));

        final authState = container.read(authProvider).requireValue;
        expect(authState, isA<AuthAuthenticated>());
        expect(
          (authState as AuthAuthenticated).user.email,
          testUserModel.email,
        );
      },
    );

    test('startLogin keeps cancelled native flow out of error state', () async {
      fakeNativeClient.nextFailure = const TelegramNativeAuthCancelled();
      container = createContainer(nativeEnabled: true, legacyEnabled: false);

      await container.read(authProvider.future);
      await container.read(telegramAuthProvider.notifier).startLogin();

      final telegramState = container.read(telegramAuthProvider).requireValue;
      expect(telegramState, isA<TelegramAuthCancelled>());

      final authState = container.read(authProvider).requireValue;
      expect(authState, isA<AuthUnauthenticated>());
    });

    test(
      'startLogin falls back to legacy widget flow when native is disabled',
      () async {
        container = createContainer(nativeEnabled: false, legacyEnabled: true);

        await container.read(telegramAuthProvider.notifier).startLogin();

        final telegramState = container.read(telegramAuthProvider).requireValue;
        expect(telegramState, isA<TelegramAuthWaitingForCallback>());
        expect(fakeNativeClient.loginCalled, isFalse);
        expect(fakeTelegramService.lastIdToken, isNull);
      },
    );

    test('startLogin exposes pending TOTP challenge for native Telegram login',
        () async {
      container = createContainer(nativeEnabled: true, legacyEnabled: false);
      container.read(telegramAuthServiceProvider);
      fakeTelegramService.nextAuthException = const TelegramAuthException(
        code: 'TWO_FACTOR_REQUIRED',
        message: 'Two-factor authentication is required.',
        tfaToken: 'pending-2fa-token',
        method: 'totp',
      );

      await container.read(authProvider.future);
      await container.read(telegramAuthProvider.notifier).startLogin();

      final telegramState = container.read(telegramAuthProvider).requireValue;
      expect(telegramState, isA<TelegramAuthRequiresTwoFactor>());

      final authState = container.read(authProvider).requireValue;
      expect(authState, isA<AuthUnauthenticated>());
    });

    test('completeTwoFactor finishes pending Telegram login', () async {
      container = createContainer(nativeEnabled: true, legacyEnabled: false);
      container.read(telegramAuthServiceProvider);
      fakeTelegramService.nextAuthException = const TelegramAuthException(
        code: 'TWO_FACTOR_REQUIRED',
        message: 'Two-factor authentication is required.',
        tfaToken: 'pending-2fa-token',
        method: 'totp',
      );

      await container.read(authProvider.future);
      await container.read(telegramAuthProvider.notifier).startLogin();

      fakeTelegramService.nextAuthException = null;
      await container.read(telegramAuthProvider.notifier).completeTwoFactor(
        '123456',
      );

      final telegramState = container.read(telegramAuthProvider).requireValue;
      expect(telegramState, isA<TelegramAuthSuccess>());
      expect(fakeTelegramService.lastTfaToken, equals('pending-2fa-token'));
      expect(fakeTelegramService.lastTwoFactorCode, equals('123456'));

      final authState = container.read(authProvider).requireValue;
      expect(authState, isA<AuthAuthenticated>());
    });
  });
}

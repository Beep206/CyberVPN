import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/data/datasources/auth_remote_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_local_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';
import 'package:cybervpn_mobile/features/auth/data/models/user_model.dart';
import 'package:cybervpn_mobile/features/auth/data/repositories/auth_repository_impl.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';

class MockAuthRemoteDataSource extends Mock implements AuthRemoteDataSource {}

class MockAuthLocalDataSource extends Mock implements AuthLocalDataSource {}

class MockNetworkInfo extends Mock implements NetworkInfo {}

void main() {
  late AuthRepositoryImpl repository;
  late MockAuthRemoteDataSource mockRemoteDataSource;
  late MockAuthLocalDataSource mockLocalDataSource;
  late MockNetworkInfo mockNetworkInfo;

  setUp(() {
    mockRemoteDataSource = MockAuthRemoteDataSource();
    mockLocalDataSource = MockAuthLocalDataSource();
    mockNetworkInfo = MockNetworkInfo();
    repository = AuthRepositoryImpl(
      remoteDataSource: mockRemoteDataSource,
      localDataSource: mockLocalDataSource,
      networkInfo: mockNetworkInfo,
    );
  });

  const testEmail = 'test@example.com';
  const testPassword = 'Password1';
  const testRefreshToken = 'refresh-token-123';
  const testDeviceId = 'test-device-id';

  const testDevice = DeviceInfo(
    deviceId: testDeviceId,
    platform: DevicePlatform.android,
    platformId: 'test-platform-id',
    osVersion: '14.0',
    appVersion: '1.0.0',
    deviceModel: 'Test Device',
  );

  final testTokenModel = TokenModel(
    accessToken: 'access-token-abc',
    refreshToken: 'refresh-token-xyz',
    expiresIn: 3600,
    tokenType: 'Bearer',
  );

  final testUserModel = UserModel(
    id: 'user-001',
    email: testEmail,
    username: 'testuser',
    isEmailVerified: true,
    isPremium: false,
    createdAt: DateTime(2026, 1, 1),
    lastLoginAt: DateTime(2026, 1, 31),
  );

  // Register fallback values for mocktail
  setUpAll(() {
    registerFallbackValue(testTokenModel);
    registerFallbackValue(testUserModel);
    registerFallbackValue(testDevice);
  });

  group('AuthRepositoryImpl', () {
    group('login', () {
      test(
          'returns (UserEntity, accessToken) on success when device is online',
          () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.login(
              email: testEmail,
              password: testPassword,
              device: testDevice,
            )).thenAnswer((_) async => (testUserModel, testTokenModel));
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        final result = await repository.login(
          email: testEmail,
          password: testPassword,
          device: testDevice,
        );

        expect(result, isA<Success<(UserEntity, String)>>());
        final (user, token) = (result as Success<(UserEntity, String)>).data;
        expect(user, isA<UserEntity>());
        expect(user.id, equals('user-001'));
        expect(user.email, equals(testEmail));
        expect(token, equals('access-token-abc'));

        verify(() => mockRemoteDataSource.login(
              email: testEmail,
              password: testPassword,
              device: testDevice,
            )).called(1);
        verify(() => mockLocalDataSource.cacheToken(testTokenModel)).called(1);
        verify(() => mockLocalDataSource.cacheUser(testUserModel)).called(1);
      });

      test('returns Failure with NetworkFailure when device is offline', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => false);

        final result = await repository.login(
          email: testEmail,
          password: testPassword,
          device: testDevice,
        );

        expect(result, isA<Failure<(UserEntity, String)>>());
        final failure = (result as Failure<(UserEntity, String)>).failure;
        expect(failure, isA<NetworkFailure>());
        expect(failure.message, equals('No internet connection'));

        verifyNever(() => mockRemoteDataSource.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
              device: any(named: 'device'),
            ));
      });

      test('returns Failure from remote data source exception', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.login(
              email: testEmail,
              password: testPassword,
              device: testDevice,
            )).thenThrow(
                const ServerException(message: 'Invalid credentials', code: 401));

        final result = await repository.login(
          email: testEmail,
          password: testPassword,
          device: testDevice,
        );

        expect(result, isA<Failure<(UserEntity, String)>>());
      });

      test('caches token and user after successful login', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.login(
              email: testEmail,
              password: testPassword,
              device: testDevice,
            )).thenAnswer((_) async => (testUserModel, testTokenModel));
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        await repository.login(
          email: testEmail,
          password: testPassword,
          device: testDevice,
        );

        verify(() => mockLocalDataSource.cacheToken(testTokenModel)).called(1);
        verify(() => mockLocalDataSource.cacheUser(testUserModel)).called(1);
      });
    });

    group('register', () {
      test(
          'returns (UserEntity, accessToken) on success when device is online',
          () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.register(
              email: testEmail,
              password: testPassword,
              device: testDevice,
              referralCode: null,
            )).thenAnswer((_) async => (testUserModel, testTokenModel));
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        final result = await repository.register(
          email: testEmail,
          password: testPassword,
          device: testDevice,
        );

        expect(result, isA<Success<(UserEntity, String)>>());
        final (user, token) = (result as Success<(UserEntity, String)>).data;
        expect(user, isA<UserEntity>());
        expect(user.email, equals(testEmail));
        expect(token, equals('access-token-abc'));
      });

      test('passes referral code to remote data source', () async {
        const referralCode = 'ABCDEF';
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.register(
              email: testEmail,
              password: testPassword,
              device: testDevice,
              referralCode: referralCode,
            )).thenAnswer((_) async => (testUserModel, testTokenModel));
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        await repository.register(
          email: testEmail,
          password: testPassword,
          device: testDevice,
          referralCode: referralCode,
        );

        verify(() => mockRemoteDataSource.register(
              email: testEmail,
              password: testPassword,
              device: testDevice,
              referralCode: referralCode,
            )).called(1);
      });

      test('returns Failure with NetworkFailure when device is offline', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => false);

        final result = await repository.register(
          email: testEmail,
          password: testPassword,
          device: testDevice,
        );

        expect(result, isA<Failure<(UserEntity, String)>>());
        final failure = (result as Failure<(UserEntity, String)>).failure;
        expect(failure, isA<NetworkFailure>());
      });

      test('returns Failure for duplicate email', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.register(
              email: testEmail,
              password: testPassword,
              device: testDevice,
              referralCode: null,
            )).thenThrow(const ServerException(
                message: 'Email already exists', code: 409));

        final result = await repository.register(
          email: testEmail,
          password: testPassword,
          device: testDevice,
        );

        expect(result, isA<Failure<(UserEntity, String)>>());
      });

      test('caches token and user after successful registration', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.register(
              email: testEmail,
              password: testPassword,
              device: testDevice,
              referralCode: null,
            )).thenAnswer((_) async => (testUserModel, testTokenModel));
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        await repository.register(
          email: testEmail,
          password: testPassword,
          device: testDevice,
        );

        verify(() => mockLocalDataSource.cacheToken(testTokenModel)).called(1);
        verify(() => mockLocalDataSource.cacheUser(testUserModel)).called(1);
      });
    });

    group('refreshToken', () {
      test('returns new access token and caches new token model', () async {
        final newTokenModel = TokenModel(
          accessToken: 'new-access-token',
          refreshToken: 'new-refresh-token',
          expiresIn: 3600,
        );
        when(() => mockRemoteDataSource.refreshToken(
              refreshToken: testRefreshToken,
              deviceId: testDeviceId,
            )).thenAnswer((_) async => newTokenModel);
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});

        final result = await repository.refreshToken(
          refreshToken: testRefreshToken,
          deviceId: testDeviceId,
        );

        expect(result, isA<Success<String>>());
        expect((result as Success<String>).data, equals('new-access-token'));
        verify(() => mockRemoteDataSource.refreshToken(
              refreshToken: testRefreshToken,
              deviceId: testDeviceId,
            )).called(1);
        verify(() => mockLocalDataSource.cacheToken(newTokenModel)).called(1);
      });

      test('does not check network connectivity', () async {
        final newTokenModel = TokenModel(
          accessToken: 'new-access-token',
          refreshToken: 'new-refresh-token',
          expiresIn: 3600,
        );
        when(() => mockRemoteDataSource.refreshToken(
              refreshToken: testRefreshToken,
              deviceId: testDeviceId,
            )).thenAnswer((_) async => newTokenModel);
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});

        await repository.refreshToken(
          refreshToken: testRefreshToken,
          deviceId: testDeviceId,
        );

        verifyNever(() => mockNetworkInfo.isConnected);
      });

      test('returns Failure for expired refresh token', () async {
        when(() => mockRemoteDataSource.refreshToken(
              refreshToken: testRefreshToken,
              deviceId: testDeviceId,
            )).thenThrow(
                const AuthException(message: 'Token expired', code: 401));

        final result = await repository.refreshToken(
          refreshToken: testRefreshToken,
          deviceId: testDeviceId,
        );

        expect(result, isA<Failure<String>>());
      });
    });

    group('logout', () {
      test('clears local auth data', () async {
        when(() => mockRemoteDataSource.logout(
              refreshToken: testRefreshToken,
              deviceId: testDeviceId,
            )).thenAnswer((_) async {});
        when(() => mockLocalDataSource.clearAuth())
            .thenAnswer((_) async {});

        final result = await repository.logout(
          refreshToken: testRefreshToken,
          deviceId: testDeviceId,
        );

        expect(result, isA<Success<void>>());
        verify(() => mockLocalDataSource.clearAuth()).called(1);
      });
    });

    group('getCurrentUser', () {
      test('returns cached user when available', () async {
        when(() => mockLocalDataSource.getCachedUser())
            .thenAnswer((_) async => testUserModel);

        final result = await repository.getCurrentUser();

        expect(result, isA<Success<UserEntity?>>());
        final user = (result as Success<UserEntity?>).data;
        expect(user, isA<UserEntity>());
        expect(user?.id, equals('user-001'));
        verifyNever(() => mockRemoteDataSource.getCurrentUser());
      });

      test('fetches from remote when no cached user and online', () async {
        when(() => mockLocalDataSource.getCachedUser())
            .thenAnswer((_) async => null);
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.getCurrentUser())
            .thenAnswer((_) async => testUserModel);
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        final result = await repository.getCurrentUser();

        expect(result, isA<Success<UserEntity?>>());
        final user = (result as Success<UserEntity?>).data;
        expect(user, isA<UserEntity>());
        expect(user?.email, equals(testEmail));
        verify(() => mockLocalDataSource.cacheUser(testUserModel)).called(1);
      });

      test('returns Success(null) when no cached user and offline', () async {
        when(() => mockLocalDataSource.getCachedUser())
            .thenAnswer((_) async => null);
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => false);

        final result = await repository.getCurrentUser();

        expect(result, isA<Success<UserEntity?>>());
        expect((result as Success<UserEntity?>).data, isNull);
      });

      test('returns Success(null) when remote fetch throws', () async {
        when(() => mockLocalDataSource.getCachedUser())
            .thenAnswer((_) async => null);
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.getCurrentUser())
            .thenThrow(const ServerException(message: 'Server error'));

        final result = await repository.getCurrentUser();

        expect(result, isA<Success<UserEntity?>>());
        expect((result as Success<UserEntity?>).data, isNull);
      });
    });

    group('isAuthenticated', () {
      test('returns Success(true) when token is cached', () async {
        when(() => mockLocalDataSource.getCachedToken())
            .thenAnswer((_) async => testTokenModel);

        final result = await repository.isAuthenticated();

        expect(result, isA<Success<bool>>());
        expect((result as Success<bool>).data, isTrue);
      });

      test('returns Success(false) when no token is cached', () async {
        when(() => mockLocalDataSource.getCachedToken())
            .thenAnswer((_) async => null);

        final result = await repository.isAuthenticated();

        expect(result, isA<Success<bool>>());
        expect((result as Success<bool>).data, isFalse);
      });
    });
  });
}

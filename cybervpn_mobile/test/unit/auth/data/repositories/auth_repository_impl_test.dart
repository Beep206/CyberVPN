import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/data/datasources/auth_remote_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_local_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';
import 'package:cybervpn_mobile/features/auth/data/models/user_model.dart';
import 'package:cybervpn_mobile/features/auth/data/repositories/auth_repository_impl.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';

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
            )).thenAnswer((_) async => (testUserModel, testTokenModel));
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        final (user, token) = await repository.login(
          email: testEmail,
          password: testPassword,
        );

        expect(user, isA<UserEntity>());
        expect(user.id, equals('user-001'));
        expect(user.email, equals(testEmail));
        expect(token, equals('access-token-abc'));

        verify(() => mockRemoteDataSource.login(
              email: testEmail,
              password: testPassword,
            )).called(1);
        verify(() => mockLocalDataSource.cacheToken(testTokenModel)).called(1);
        verify(() => mockLocalDataSource.cacheUser(testUserModel)).called(1);
      });

      test('throws NetworkFailure when device is offline', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => false);

        expect(
          () => repository.login(email: testEmail, password: testPassword),
          throwsA(isA<NetworkFailure>().having(
            (f) => f.message,
            'message',
            'No internet connection',
          )),
        );

        verifyNever(() => mockRemoteDataSource.login(
              email: any(named: 'email'),
              password: any(named: 'password'),
            ));
      });

      test('propagates exception from remote data source', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.login(
              email: testEmail,
              password: testPassword,
            )).thenThrow(
                const ServerException(message: 'Invalid credentials', code: 401));

        expect(
          () => repository.login(email: testEmail, password: testPassword),
          throwsA(isA<ServerException>()),
        );
      });

      test('caches token and user after successful login', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.login(
              email: testEmail,
              password: testPassword,
            )).thenAnswer((_) async => (testUserModel, testTokenModel));
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        await repository.login(email: testEmail, password: testPassword);

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
              referralCode: null,
            )).thenAnswer((_) async => (testUserModel, testTokenModel));
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        final (user, token) = await repository.register(
          email: testEmail,
          password: testPassword,
        );

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
              referralCode: referralCode,
            )).thenAnswer((_) async => (testUserModel, testTokenModel));
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        await repository.register(
          email: testEmail,
          password: testPassword,
          referralCode: referralCode,
        );

        verify(() => mockRemoteDataSource.register(
              email: testEmail,
              password: testPassword,
              referralCode: referralCode,
            )).called(1);
      });

      test('throws NetworkFailure when device is offline', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => false);

        expect(
          () => repository.register(email: testEmail, password: testPassword),
          throwsA(isA<NetworkFailure>()),
        );
      });

      test('propagates exception for duplicate email', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.register(
              email: testEmail,
              password: testPassword,
              referralCode: null,
            )).thenThrow(const ServerException(
                message: 'Email already exists', code: 409));

        expect(
          () => repository.register(email: testEmail, password: testPassword),
          throwsA(isA<ServerException>()),
        );
      });

      test('caches token and user after successful registration', () async {
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.register(
              email: testEmail,
              password: testPassword,
              referralCode: null,
            )).thenAnswer((_) async => (testUserModel, testTokenModel));
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});
        when(() => mockLocalDataSource.cacheUser(any()))
            .thenAnswer((_) async {});

        await repository.register(email: testEmail, password: testPassword);

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
        when(() => mockRemoteDataSource.refreshToken(testRefreshToken))
            .thenAnswer((_) async => newTokenModel);
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});

        final result = await repository.refreshToken(testRefreshToken);

        expect(result, equals('new-access-token'));
        verify(() => mockRemoteDataSource.refreshToken(testRefreshToken))
            .called(1);
        verify(() => mockLocalDataSource.cacheToken(newTokenModel)).called(1);
      });

      test('does not check network connectivity', () async {
        final newTokenModel = TokenModel(
          accessToken: 'new-access-token',
          refreshToken: 'new-refresh-token',
          expiresIn: 3600,
        );
        when(() => mockRemoteDataSource.refreshToken(testRefreshToken))
            .thenAnswer((_) async => newTokenModel);
        when(() => mockLocalDataSource.cacheToken(any()))
            .thenAnswer((_) async {});

        await repository.refreshToken(testRefreshToken);

        verifyNever(() => mockNetworkInfo.isConnected);
      });

      test('propagates exception for expired refresh token', () async {
        when(() => mockRemoteDataSource.refreshToken(testRefreshToken))
            .thenThrow(
                const AuthException(message: 'Token expired', code: 401));

        expect(
          () => repository.refreshToken(testRefreshToken),
          throwsA(isA<AuthException>()),
        );
      });
    });

    group('logout', () {
      test('clears local auth data', () async {
        when(() => mockLocalDataSource.clearAuth())
            .thenAnswer((_) async {});

        await repository.logout();

        verify(() => mockLocalDataSource.clearAuth()).called(1);
      });
    });

    group('getCurrentUser', () {
      test('returns cached user when available', () async {
        when(() => mockLocalDataSource.getCachedUser())
            .thenAnswer((_) async => testUserModel);

        final result = await repository.getCurrentUser();

        expect(result, isA<UserEntity>());
        expect(result?.id, equals('user-001'));
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

        expect(result, isA<UserEntity>());
        expect(result?.email, equals(testEmail));
        verify(() => mockLocalDataSource.cacheUser(testUserModel)).called(1);
      });

      test('returns null when no cached user and offline', () async {
        when(() => mockLocalDataSource.getCachedUser())
            .thenAnswer((_) async => null);
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => false);

        final result = await repository.getCurrentUser();

        expect(result, isNull);
      });

      test('returns null when remote fetch throws', () async {
        when(() => mockLocalDataSource.getCachedUser())
            .thenAnswer((_) async => null);
        when(() => mockNetworkInfo.isConnected)
            .thenAnswer((_) async => true);
        when(() => mockRemoteDataSource.getCurrentUser())
            .thenThrow(const ServerException(message: 'Server error'));

        final result = await repository.getCurrentUser();

        expect(result, isNull);
      });
    });

    group('isAuthenticated', () {
      test('returns true when token is cached', () async {
        when(() => mockLocalDataSource.getCachedToken())
            .thenAnswer((_) async => testTokenModel);

        final result = await repository.isAuthenticated();

        expect(result, isTrue);
      });

      test('returns false when no token is cached', () async {
        when(() => mockLocalDataSource.getCachedToken())
            .thenAnswer((_) async => null);

        final result = await repository.isAuthenticated();

        expect(result, isFalse);
      });
    });
  });
}

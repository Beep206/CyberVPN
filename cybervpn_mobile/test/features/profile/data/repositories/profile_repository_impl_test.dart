import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/network/network_info.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/profile/data/datasources/profile_remote_ds.dart';
import 'package:cybervpn_mobile/features/profile/data/repositories/profile_repository_impl.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/device.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/oauth_provider.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/profile.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class MockProfileRemoteDataSource extends Mock
    implements ProfileRemoteDataSource {}

class MockNetworkInfo extends Mock implements NetworkInfo {}

void main() {
  late MockProfileRemoteDataSource mockRemoteDs;
  late MockNetworkInfo mockNetworkInfo;
  late ProfileRepositoryImpl repository;

  setUp(() {
    mockRemoteDs = MockProfileRemoteDataSource();
    mockNetworkInfo = MockNetworkInfo();
    repository = ProfileRepositoryImpl(
      remoteDataSource: mockRemoteDs,
      networkInfo: mockNetworkInfo,
    );
  });

  void stubOnline() {
    when(() => mockNetworkInfo.isConnected).thenAnswer((_) async => true);
  }

  void stubOffline() {
    when(() => mockNetworkInfo.isConnected).thenAnswer((_) async => false);
  }

  const tProfile = Profile(
    id: 'user-1',
    email: 'test@example.com',
  );

  const tSetup2FA = Setup2FAResult(
    secret: 'SECRET',
    qrCodeUri: 'otpauth://totp/test',
  );

  final tDevices = [
    const Device(id: 'dev-1', name: 'Phone', platform: 'iOS'),
  ];

  // ---------------------------------------------------------------------------
  // Network connectivity checks
  // ---------------------------------------------------------------------------
  group('network connectivity', () {
    test('returns Failure with NetworkFailure when offline for getProfile', () async {
      stubOffline();

      final result = await repository.getProfile();

      expect(result, isA<Failure<Profile>>());
      expect((result as Failure<Profile>).failure, isA<NetworkFailure>());
    });

    test('returns Failure with NetworkFailure when offline for setup2FA', () async {
      stubOffline();

      final result = await repository.setup2FA();

      expect(result, isA<Failure<Setup2FAResult>>());
      expect((result as Failure<Setup2FAResult>).failure, isA<NetworkFailure>());
    });

    test('returns Failure with NetworkFailure when offline for getOAuthAuthorizationUrl', () async {
      stubOffline();

      final result = await repository.getOAuthAuthorizationUrl(OAuthProvider.github);

      expect(result, isA<Failure<String>>());
      expect((result as Failure<String>).failure, isA<NetworkFailure>());
    });
  });

  // ---------------------------------------------------------------------------
  // getProfile
  // ---------------------------------------------------------------------------
  group('getProfile', () {
    test('returns Success with Profile from remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.getProfile()).thenAnswer((_) async => tProfile);

      final result = await repository.getProfile();

      expect(result, isA<Success<Profile>>());
      expect((result as Success<Profile>).data, tProfile);
      verify(() => mockRemoteDs.getProfile()).called(1);
    });

    test('maps ServerException to Failure with ServerFailure', () async {
      stubOnline();
      when(() => mockRemoteDs.getProfile())
          .thenThrow(const ServerException(message: 'Server error', code: 500));

      final result = await repository.getProfile();

      expect(result, isA<Failure<Profile>>());
      expect((result as Failure<Profile>).failure, isA<ServerFailure>());
    });

    test('maps AuthException to Failure with AuthFailure', () async {
      stubOnline();
      when(() => mockRemoteDs.getProfile())
          .thenThrow(const AuthException(message: 'Unauthorized', code: 401));

      final result = await repository.getProfile();

      expect(result, isA<Failure<Profile>>());
      expect((result as Failure<Profile>).failure, isA<AuthFailure>());
    });

    test('maps NetworkException to Failure with NetworkFailure', () async {
      stubOnline();
      when(() => mockRemoteDs.getProfile())
          .thenThrow(const NetworkException(message: 'Timeout'));

      final result = await repository.getProfile();

      expect(result, isA<Failure<Profile>>());
      expect((result as Failure<Profile>).failure, isA<NetworkFailure>());
    });
  });

  // ---------------------------------------------------------------------------
  // setup2FA
  // ---------------------------------------------------------------------------
  group('setup2FA', () {
    test('returns Success with Setup2FAResult from remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.setup2FA()).thenAnswer((_) async => tSetup2FA);

      final result = await repository.setup2FA();

      expect(result, isA<Success<Setup2FAResult>>());
      final data = (result as Success<Setup2FAResult>).data;
      expect(data.secret, 'SECRET');
      expect(data.qrCodeUri, 'otpauth://totp/test');
    });
  });

  // ---------------------------------------------------------------------------
  // verify2FA
  // ---------------------------------------------------------------------------
  group('verify2FA', () {
    test('delegates to remote data source and returns Success', () async {
      stubOnline();
      when(() => mockRemoteDs.verify2FA('123456'))
          .thenAnswer((_) async => true);

      final result = await repository.verify2FA('123456');

      expect(result, isA<Success<bool>>());
      expect((result as Success<bool>).data, isTrue);
    });
  });

  // ---------------------------------------------------------------------------
  // validate2FA
  // ---------------------------------------------------------------------------
  group('validate2FA', () {
    test('delegates to remote data source and returns Success', () async {
      stubOnline();
      when(() => mockRemoteDs.validate2FA('654321'))
          .thenAnswer((_) async => false);

      final result = await repository.validate2FA('654321');

      expect(result, isA<Success<bool>>());
      expect((result as Success<bool>).data, isFalse);
    });
  });

  // ---------------------------------------------------------------------------
  // disable2FA
  // ---------------------------------------------------------------------------
  group('disable2FA', () {
    test('delegates to remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.disable2FA('111111'))
          .thenAnswer((_) async {});

      final result = await repository.disable2FA('111111');

      expect(result, isA<Success<void>>());
      verify(() => mockRemoteDs.disable2FA('111111')).called(1);
    });

    test('maps ServerException with 403 to Failure with AccessDeniedFailure', () async {
      stubOnline();
      when(() => mockRemoteDs.disable2FA(any()))
          .thenThrow(const ServerException(message: 'Forbidden', code: 403));

      final result = await repository.disable2FA('bad');

      expect(result, isA<Failure<void>>());
      expect((result as Failure<void>).failure, isA<AccessDeniedFailure>());
    });
  });

  // ---------------------------------------------------------------------------
  // getOAuthAuthorizationUrl
  // ---------------------------------------------------------------------------
  group('getOAuthAuthorizationUrl', () {
    test('delegates to remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.getOAuthAuthorizationUrl(OAuthProvider.github))
          .thenAnswer((_) async => 'https://auth.example.com/github');

      final result = await repository.getOAuthAuthorizationUrl(OAuthProvider.github);

      expect(result, isA<Success<String>>());
      expect((result as Success<String>).data, 'https://auth.example.com/github');
      verify(() => mockRemoteDs.getOAuthAuthorizationUrl(OAuthProvider.github)).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // unlinkOAuth
  // ---------------------------------------------------------------------------
  group('unlinkOAuth', () {
    test('delegates to remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.unlinkOAuth(OAuthProvider.google))
          .thenAnswer((_) async {});

      final result = await repository.unlinkOAuth(OAuthProvider.google);

      expect(result, isA<Success<void>>());
      verify(() => mockRemoteDs.unlinkOAuth(OAuthProvider.google)).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // getDevices
  // ---------------------------------------------------------------------------
  group('getDevices', () {
    test('returns Success with device list from remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.getDevices()).thenAnswer((_) async => tDevices);

      final result = await repository.getDevices();

      expect(result, isA<Success<List<Device>>>());
      final data = (result as Success<List<Device>>).data;
      expect(data, hasLength(1));
      expect(data.first.id, 'dev-1');
    });
  });

  // ---------------------------------------------------------------------------
  // removeDevice
  // ---------------------------------------------------------------------------
  group('removeDevice', () {
    test('delegates to remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.removeDevice('dev-1'))
          .thenAnswer((_) async {});

      final result = await repository.removeDevice('dev-1');

      expect(result, isA<Success<void>>());
      verify(() => mockRemoteDs.removeDevice('dev-1')).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // deleteAccount
  // ---------------------------------------------------------------------------
  group('deleteAccount', () {
    test('delegates with password and optional totp code', () async {
      stubOnline();
      when(() => mockRemoteDs.deleteAccount('pass', totpCode: '123456'))
          .thenAnswer((_) async {});

      final result = await repository.deleteAccount('pass', totpCode: '123456');

      expect(result, isA<Success<void>>());
      verify(() => mockRemoteDs.deleteAccount('pass', totpCode: '123456'))
          .called(1);
    });

    test('maps ServerException with 429 to Failure with RateLimitFailure', () async {
      stubOnline();
      when(() => mockRemoteDs.deleteAccount(any(), totpCode: any(named: 'totpCode')))
          .thenThrow(const ServerException(message: 'Rate limited', code: 429));

      final result = await repository.deleteAccount('pass');

      expect(result, isA<Failure<void>>());
      expect((result as Failure<void>).failure, isA<RateLimitFailure>());
    });
  });
}

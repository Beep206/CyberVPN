import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/network/network_info.dart';
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

  final tProfile = Profile(
    id: 'user-1',
    email: 'test@example.com',
  );

  final tSetup2FA = Setup2FAResult(
    secret: 'SECRET',
    qrCodeUri: 'otpauth://totp/test',
  );

  final tDevices = [
    Device(id: 'dev-1', name: 'Phone', platform: 'iOS'),
  ];

  // ---------------------------------------------------------------------------
  // Network connectivity checks
  // ---------------------------------------------------------------------------
  group('network connectivity', () {
    test('throws NetworkFailure when offline for getProfile', () async {
      stubOffline();

      expect(
        () => repository.getProfile(),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('throws NetworkFailure when offline for setup2FA', () async {
      stubOffline();

      expect(
        () => repository.setup2FA(),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('throws NetworkFailure when offline for linkOAuth', () async {
      stubOffline();

      expect(
        () => repository.linkOAuth(OAuthProvider.github),
        throwsA(isA<NetworkFailure>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // getProfile
  // ---------------------------------------------------------------------------
  group('getProfile', () {
    test('returns Profile from remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.getProfile()).thenAnswer((_) async => tProfile);

      final result = await repository.getProfile();

      expect(result, tProfile);
      verify(() => mockRemoteDs.getProfile()).called(1);
    });

    test('maps ServerException to ServerFailure', () async {
      stubOnline();
      when(() => mockRemoteDs.getProfile())
          .thenThrow(const ServerException(message: 'Server error', code: 500));

      expect(
        () => repository.getProfile(),
        throwsA(isA<ServerFailure>()),
      );
    });

    test('maps AuthException to AuthFailure', () async {
      stubOnline();
      when(() => mockRemoteDs.getProfile())
          .thenThrow(const AuthException(message: 'Unauthorized', code: 401));

      expect(
        () => repository.getProfile(),
        throwsA(isA<AuthFailure>()),
      );
    });

    test('maps NetworkException to NetworkFailure', () async {
      stubOnline();
      when(() => mockRemoteDs.getProfile())
          .thenThrow(const NetworkException(message: 'Timeout'));

      expect(
        () => repository.getProfile(),
        throwsA(isA<NetworkFailure>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // setup2FA
  // ---------------------------------------------------------------------------
  group('setup2FA', () {
    test('returns Setup2FAResult from remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.setup2FA()).thenAnswer((_) async => tSetup2FA);

      final result = await repository.setup2FA();

      expect(result.secret, 'SECRET');
      expect(result.qrCodeUri, 'otpauth://totp/test');
    });
  });

  // ---------------------------------------------------------------------------
  // verify2FA
  // ---------------------------------------------------------------------------
  group('verify2FA', () {
    test('delegates to remote data source and returns result', () async {
      stubOnline();
      when(() => mockRemoteDs.verify2FA('123456'))
          .thenAnswer((_) async => true);

      final result = await repository.verify2FA('123456');

      expect(result, isTrue);
    });
  });

  // ---------------------------------------------------------------------------
  // validate2FA
  // ---------------------------------------------------------------------------
  group('validate2FA', () {
    test('delegates to remote data source and returns result', () async {
      stubOnline();
      when(() => mockRemoteDs.validate2FA('654321'))
          .thenAnswer((_) async => false);

      final result = await repository.validate2FA('654321');

      expect(result, isFalse);
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

      await repository.disable2FA('111111');

      verify(() => mockRemoteDs.disable2FA('111111')).called(1);
    });

    test('maps ServerException with 403 to AccessDeniedFailure', () async {
      stubOnline();
      when(() => mockRemoteDs.disable2FA(any()))
          .thenThrow(const ServerException(message: 'Forbidden', code: 403));

      expect(
        () => repository.disable2FA('bad'),
        throwsA(isA<AccessDeniedFailure>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // linkOAuth
  // ---------------------------------------------------------------------------
  group('linkOAuth', () {
    test('delegates to remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.linkOAuth(OAuthProvider.github))
          .thenAnswer((_) async {});

      await repository.linkOAuth(OAuthProvider.github);

      verify(() => mockRemoteDs.linkOAuth(OAuthProvider.github)).called(1);
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

      await repository.unlinkOAuth(OAuthProvider.google);

      verify(() => mockRemoteDs.unlinkOAuth(OAuthProvider.google)).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // getDevices
  // ---------------------------------------------------------------------------
  group('getDevices', () {
    test('returns device list from remote data source', () async {
      stubOnline();
      when(() => mockRemoteDs.getDevices()).thenAnswer((_) async => tDevices);

      final result = await repository.getDevices();

      expect(result, hasLength(1));
      expect(result.first.id, 'dev-1');
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

      await repository.removeDevice('dev-1');

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

      await repository.deleteAccount('pass', totpCode: '123456');

      verify(() => mockRemoteDs.deleteAccount('pass', totpCode: '123456'))
          .called(1);
    });

    test('maps ServerException with 429 to RateLimitFailure', () async {
      stubOnline();
      when(() => mockRemoteDs.deleteAccount(any(), totpCode: any(named: 'totpCode')))
          .thenThrow(const ServerException(message: 'Rate limited', code: 429));

      expect(
        () => repository.deleteAccount('pass'),
        throwsA(isA<RateLimitFailure>()),
      );
    });
  });
}

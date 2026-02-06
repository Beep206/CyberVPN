import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/domain/usecases/register.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/types/result.dart';

import '../../../../helpers/mock_repositories.dart';
import '../../../../helpers/mock_factories.dart';

void main() {
  late RegisterUseCase useCase;
  late MockAuthRepository mockRepository;

  const testDevice = DeviceInfo(
    deviceId: 'test-device-id',
    platform: DevicePlatform.android,
    platformId: 'test-platform-id',
    osVersion: '14.0',
    appVersion: '1.0.0',
    deviceModel: 'Test Device',
  );

  setUpAll(() {
    registerFallbackValue(testDevice);
  });

  setUp(() {
    mockRepository = MockAuthRepository();
    useCase = RegisterUseCase(mockRepository);
  });

  const validEmail = 'newuser@example.com';
  const validPassword = 'Password1';
  const validReferralCode = 'ABCDEF';
  const accessToken = 'access-token-xyz';

  group('RegisterUseCase', () {
    test('returns (UserEntity, String) when registration data is valid',
        () async {
      final mockUser = createMockUser(email: validEmail);
      when(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
            referralCode: null,
          )).thenAnswer((_) async => Success((mockUser, accessToken)));

      final result = await useCase(
        email: validEmail,
        password: validPassword,
        device: testDevice,
      );

      expect(result, isA<Success<(UserEntity, String)>>());
      final (user, token) = (result as Success<(UserEntity, String)>).data;
      expect(user, equals(mockUser));
      expect(token, equals(accessToken));
      verify(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
            referralCode: null,
          )).called(1);
    });

    test('passes referral code to repository when provided', () async {
      final mockUser = createMockUser(email: validEmail);
      when(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
            referralCode: validReferralCode,
          )).thenAnswer((_) async => Success((mockUser, accessToken)));

      final result = await useCase(
        email: validEmail,
        password: validPassword,
        device: testDevice,
        referralCode: validReferralCode,
      );

      expect(result, isA<Success<(UserEntity, String)>>());
      final (user, token) = (result as Success<(UserEntity, String)>).data;
      expect(user, equals(mockUser));
      expect(token, equals(accessToken));
      verify(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
            referralCode: validReferralCode,
          )).called(1);
    });

    test('throws ArgumentError when email is empty', () async {
      expect(
        () => useCase(email: '', password: validPassword, device: testDevice),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.register(
            email: any(named: 'email'),
            password: any(named: 'password'),
            device: any(named: 'device'),
            referralCode: any(named: 'referralCode'),
          ));
    });

    test('throws ArgumentError when email is invalid format', () async {
      expect(
        () => useCase(email: 'bad-email', password: validPassword, device: testDevice),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when password is empty', () async {
      expect(
        () => useCase(email: validEmail, password: '', device: testDevice),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when password is too weak (short)', () async {
      expect(
        () => useCase(email: validEmail, password: 'Ab1', device: testDevice),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when password lacks uppercase', () async {
      expect(
        () => useCase(email: validEmail, password: 'password1', device: testDevice),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when referral code is invalid', () async {
      // Referral code must be 6-20 alphanumeric chars
      expect(
        () => useCase(
          email: validEmail,
          password: validPassword,
          device: testDevice,
          referralCode: 'AB',
        ),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('propagates AuthFailure for duplicate email', () async {
      when(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
            referralCode: null,
          )).thenThrow(
              const AuthFailure(message: 'Email already exists', code: 409));

      expect(
        () => useCase(email: validEmail, password: validPassword, device: testDevice),
        throwsA(isA<AuthFailure>()),
      );
    });

    test('propagates NetworkFailure from repository', () async {
      when(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
            referralCode: null,
          )).thenThrow(
              const NetworkFailure(message: 'No internet connection'));

      expect(
        () => useCase(email: validEmail, password: validPassword, device: testDevice),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('propagates ServerFailure from repository', () async {
      when(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
            referralCode: null,
          )).thenThrow(
              const ServerFailure(message: 'Server error', code: 500));

      expect(
        () => useCase(email: validEmail, password: validPassword, device: testDevice),
        throwsA(isA<ServerFailure>()),
      );
    });
  });
}

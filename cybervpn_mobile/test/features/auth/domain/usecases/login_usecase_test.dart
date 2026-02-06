import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/domain/usecases/login.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/core/device/device_info.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/types/result.dart';

import '../../../../helpers/mock_repositories.dart';
import '../../../../helpers/mock_factories.dart';

void main() {
  late LoginUseCase useCase;
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
    useCase = LoginUseCase(mockRepository);
  });

  const validEmail = 'test@example.com';
  const validPassword = 'Password1';
  const accessToken = 'access-token-abc';

  group('LoginUseCase', () {
    test('returns (UserEntity, String) when credentials are valid', () async {
      final mockUser = createMockUser();
      when(() => mockRepository.login(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
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
      verify(() => mockRepository.login(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
          )).called(1);
    });

    test('throws ArgumentError when email is empty', () async {
      expect(
        () => useCase(email: '', password: validPassword, device: testDevice),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.login(
            email: any(named: 'email'),
            password: any(named: 'password'),
            device: any(named: 'device'),
          ));
    });

    test('throws ArgumentError when email is invalid format', () async {
      expect(
        () => useCase(email: 'not-an-email', password: validPassword, device: testDevice),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.login(
            email: any(named: 'email'),
            password: any(named: 'password'),
            device: any(named: 'device'),
          ));
    });

    test('throws ArgumentError when password is empty', () async {
      expect(
        () => useCase(email: validEmail, password: '', device: testDevice),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.login(
            email: any(named: 'email'),
            password: any(named: 'password'),
            device: any(named: 'device'),
          ));
    });

    test('throws ArgumentError when password is too short', () async {
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

    test('throws ArgumentError when password lacks lowercase', () async {
      expect(
        () => useCase(email: validEmail, password: 'PASSWORD1', device: testDevice),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when password lacks digit', () async {
      expect(
        () => useCase(email: validEmail, password: 'Passwordx', device: testDevice),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('propagates AuthFailure from repository', () async {
      when(() => mockRepository.login(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
          )).thenThrow(
              const AuthFailure(message: 'Invalid credentials', code: 401));

      expect(
        () => useCase(email: validEmail, password: validPassword, device: testDevice),
        throwsA(isA<AuthFailure>()),
      );
    });

    test('propagates NetworkFailure from repository', () async {
      when(() => mockRepository.login(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
          )).thenThrow(
              const NetworkFailure(message: 'No internet connection'));

      expect(
        () => useCase(email: validEmail, password: validPassword, device: testDevice),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('propagates ServerFailure from repository', () async {
      when(() => mockRepository.login(
            email: validEmail,
            password: validPassword,
            device: any(named: 'device'),
          )).thenThrow(
              const ServerFailure(message: 'Internal server error', code: 500));

      expect(
        () => useCase(email: validEmail, password: validPassword, device: testDevice),
        throwsA(isA<ServerFailure>()),
      );
    });
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/delete_account.dart';

import '../../helpers/mock_repositories.dart';

void main() {
  late MockProfileRepository mockRepository;
  late DeleteAccountUseCase useCase;

  setUp(() {
    mockRepository = MockProfileRepository();
    useCase = DeleteAccountUseCase(mockRepository);
  });

  // ---------------------------------------------------------------------------
  // Password validation
  // ---------------------------------------------------------------------------
  group('password validation', () {
    test('throws ArgumentError when password is empty', () async {
      await expectLater(
        () => useCase(password: '', is2FAEnabled: false),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(
        () => mockRepository.deleteAccount(any(), totpCode: any(named: 'totpCode')),
      );
    });

    test('proceeds when password is provided and 2FA disabled', () async {
      // Arrange
      when(() => mockRepository.deleteAccount('mypassword'))
          .thenAnswer((_) async {});

      // Act
      await useCase(password: 'mypassword', is2FAEnabled: false);

      // Assert
      verify(() => mockRepository.deleteAccount('mypassword')).called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // 2FA enforcement
  // ---------------------------------------------------------------------------
  group('2FA enforcement', () {
    test('throws ArgumentError when 2FA enabled but no TOTP code', () async {
      await expectLater(
        () => useCase(password: 'mypassword', is2FAEnabled: true),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when 2FA enabled but TOTP code is empty',
        () async {
      await expectLater(
        () => useCase(
          password: 'mypassword',
          is2FAEnabled: true,
          totpCode: '',
        ),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when TOTP code is invalid format (non-digits)',
        () {
      expect(
        () => useCase(
          password: 'mypassword',
          is2FAEnabled: true,
          totpCode: 'abc123',
        ),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when TOTP code is too short', () {
      expect(
        () => useCase(
          password: 'mypassword',
          is2FAEnabled: true,
          totpCode: '12345',
        ),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when TOTP code is too long', () {
      expect(
        () => useCase(
          password: 'mypassword',
          is2FAEnabled: true,
          totpCode: '1234567',
        ),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('calls repository with password and TOTP when 2FA enabled', () async {
      // Arrange
      when(() =>
              mockRepository.deleteAccount('mypassword', totpCode: '123456'))
          .thenAnswer((_) async {});

      // Act
      await useCase(
        password: 'mypassword',
        is2FAEnabled: true,
        totpCode: '123456',
      );

      // Assert
      verify(() =>
              mockRepository.deleteAccount('mypassword', totpCode: '123456'))
          .called(1);
    });

    test('ignores TOTP code when 2FA is disabled', () async {
      // Arrange
      when(() =>
              mockRepository.deleteAccount('pass', totpCode: '123456'))
          .thenAnswer((_) async {});

      // Act: passing totpCode even though 2FA is disabled
      await useCase(
        password: 'pass',
        is2FAEnabled: false,
        totpCode: '123456',
      );

      // Assert: totpCode is still passed through to repository
      verify(() => mockRepository.deleteAccount('pass', totpCode: '123456'))
          .called(1);
    });
  });

  // ---------------------------------------------------------------------------
  // Error propagation from repository
  // ---------------------------------------------------------------------------
  group('error propagation', () {
    test('propagates NetworkFailure from repository', () async {
      // Arrange
      when(() => mockRepository.deleteAccount('pass'))
          .thenThrow(const NetworkFailure(message: 'No connection'));

      // Act & Assert
      await expectLater(
        () => useCase(password: 'pass', is2FAEnabled: false),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('propagates ServerFailure from repository', () async {
      // Arrange
      when(() => mockRepository.deleteAccount('pass'))
          .thenThrow(const ServerFailure(message: 'Internal error', code: 500));

      // Act & Assert
      await expectLater(
        () => useCase(password: 'pass', is2FAEnabled: false),
        throwsA(isA<ServerFailure>()),
      );
    });

    test('propagates AuthFailure from repository', () async {
      // Arrange
      when(() => mockRepository.deleteAccount('wrong'))
          .thenThrow(
              const AuthFailure(message: 'Invalid password', code: 401));

      // Act & Assert
      await expectLater(
        () => useCase(password: 'wrong', is2FAEnabled: false),
        throwsA(isA<AuthFailure>()),
      );
    });

    test('propagates RateLimitFailure from repository', () async {
      // Arrange
      when(() => mockRepository.deleteAccount('pass'))
          .thenThrow(
              const RateLimitFailure(message: 'Too many attempts', code: 429));

      // Act & Assert
      await expectLater(
        () => useCase(password: 'pass', is2FAEnabled: false),
        throwsA(isA<RateLimitFailure>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Edge cases
  // ---------------------------------------------------------------------------
  group('edge cases', () {
    test('accepts minimum valid password (single character)', () async {
      // Arrange
      when(() => mockRepository.deleteAccount('x'))
          .thenAnswer((_) async {});

      // Act
      await useCase(password: 'x', is2FAEnabled: false);

      // Assert
      verify(() => mockRepository.deleteAccount('x')).called(1);
    });

    test('accepts password with special characters', () async {
      // Arrange
      const password = r'P@$$w0rd!#%^&*()';
      when(() => mockRepository.deleteAccount(password))
          .thenAnswer((_) async {});

      // Act
      await useCase(password: password, is2FAEnabled: false);

      // Assert
      verify(() => mockRepository.deleteAccount(password)).called(1);
    });

    test('TOTP code with leading zeros is valid', () async {
      // Arrange
      when(() =>
              mockRepository.deleteAccount('pass', totpCode: '000001'))
          .thenAnswer((_) async {});

      // Act
      await useCase(
        password: 'pass',
        is2FAEnabled: true,
        totpCode: '000001',
      );

      // Assert
      verify(() =>
              mockRepository.deleteAccount('pass', totpCode: '000001'))
          .called(1);
    });
  });
}

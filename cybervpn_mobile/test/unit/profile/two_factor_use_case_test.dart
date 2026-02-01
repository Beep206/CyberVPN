import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/setup_2fa.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/verify_2fa.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/disable_2fa.dart';

import '../../helpers/mock_repositories.dart';

void main() {
  late MockProfileRepository mockRepository;

  setUp(() {
    mockRepository = MockProfileRepository();
  });

  // ---------------------------------------------------------------------------
  // Setup2FAUseCase
  // ---------------------------------------------------------------------------
  group('Setup2FAUseCase', () {
    late Setup2FAUseCase useCase;

    setUp(() {
      useCase = Setup2FAUseCase(mockRepository);
    });

    test('returns Setup2FAResult with secret and QR code URI', () async {
      // Arrange
      const result = Setup2FAResult(
        secret: 'JBSWY3DPEHPK3PXP',
        qrCodeUri:
            'otpauth://totp/CyberVPN:user@example.com?secret=JBSWY3DPEHPK3PXP',
      );
      when(() => mockRepository.setup2FA()).thenAnswer((_) async => result);

      // Act
      final actual = await useCase();

      // Assert
      expect(actual, equals(result));
      expect(actual.secret, 'JBSWY3DPEHPK3PXP');
      expect(actual.qrCodeUri, contains('otpauth://'));
      verify(() => mockRepository.setup2FA()).called(1);
    });

    test('propagates repository exceptions', () async {
      // Arrange
      when(() => mockRepository.setup2FA())
          .thenThrow(Exception('Server error'));

      // Act & Assert
      expect(() => useCase(), throwsA(isA<Exception>()));
    });
  });

  // ---------------------------------------------------------------------------
  // Verify2FAUseCase
  // ---------------------------------------------------------------------------
  group('Verify2FAUseCase', () {
    late Verify2FAUseCase useCase;

    setUp(() {
      useCase = Verify2FAUseCase(mockRepository);
    });

    test('returns true when code is valid', () async {
      // Arrange
      when(() => mockRepository.verify2FA('123456'))
          .thenAnswer((_) async => true);

      // Act
      final result = await useCase('123456');

      // Assert
      expect(result, isTrue);
      verify(() => mockRepository.verify2FA('123456')).called(1);
    });

    test('returns false when code is invalid but format is correct', () async {
      // Arrange
      when(() => mockRepository.verify2FA('000000'))
          .thenAnswer((_) async => false);

      // Act
      final result = await useCase('000000');

      // Assert
      expect(result, isFalse);
    });

    test('throws ArgumentError for empty code', () async {
      await expectLater(
        () => useCase(''),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.verify2FA(any()));
    });

    test('throws ArgumentError for code shorter than 6 digits', () async {
      await expectLater(
        () => useCase('12345'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError for code longer than 6 digits', () async {
      await expectLater(
        () => useCase('1234567'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError for non-numeric code', () async {
      await expectLater(
        () => useCase('abcdef'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError for code with spaces', () async {
      await expectLater(
        () => useCase('12 456'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError for mixed alphanumeric code', () async {
      await expectLater(
        () => useCase('12ab56'),
        throwsA(isA<ArgumentError>()),
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Disable2FAUseCase
  // ---------------------------------------------------------------------------
  group('Disable2FAUseCase', () {
    late Disable2FAUseCase useCase;

    setUp(() {
      useCase = Disable2FAUseCase(mockRepository);
    });

    test('calls repository.disable2FA with valid code', () async {
      // Arrange
      when(() => mockRepository.disable2FA('654321'))
          .thenAnswer((_) async {});

      // Act
      await useCase('654321');

      // Assert
      verify(() => mockRepository.disable2FA('654321')).called(1);
    });

    test('throws ArgumentError for empty code', () async {
      await expectLater(
        () => useCase(''),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.disable2FA(any()));
    });

    test('throws ArgumentError for non-digit code', () async {
      await expectLater(
        () => useCase('abc123'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError for short code', () async {
      await expectLater(
        () => useCase('123'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('propagates repository exceptions', () async {
      // Arrange
      when(() => mockRepository.disable2FA('123456'))
          .thenThrow(Exception('Invalid code'));

      // Act & Assert
      expect(() => useCase('123456'), throwsA(isA<Exception>()));
    });
  });

  // ---------------------------------------------------------------------------
  // Full 2FA lifecycle: setup -> verify -> disable
  // ---------------------------------------------------------------------------
  group('Full 2FA lifecycle', () {
    late Setup2FAUseCase setupUseCase;
    late Verify2FAUseCase verifyUseCase;
    late Disable2FAUseCase disableUseCase;

    setUp(() {
      setupUseCase = Setup2FAUseCase(mockRepository);
      verifyUseCase = Verify2FAUseCase(mockRepository);
      disableUseCase = Disable2FAUseCase(mockRepository);
    });

    test('setup -> verify -> enable flow completes successfully', () async {
      // Arrange: setup returns secret
      const setupResult = Setup2FAResult(
        secret: 'SECRET123',
        qrCodeUri: 'otpauth://totp/Test?secret=SECRET123',
      );
      when(() => mockRepository.setup2FA())
          .thenAnswer((_) async => setupResult);
      when(() => mockRepository.verify2FA('111111'))
          .thenAnswer((_) async => true);

      // Act: setup
      final result = await setupUseCase();
      expect(result.secret, 'SECRET123');

      // Act: verify
      final verified = await verifyUseCase('111111');
      expect(verified, isTrue);

      // Assert: both called
      verify(() => mockRepository.setup2FA()).called(1);
      verify(() => mockRepository.verify2FA('111111')).called(1);
    });

    test('setup -> verify (fail) -> verify (success) flow', () async {
      // Arrange
      const setupResult = Setup2FAResult(
        secret: 'SECRET456',
        qrCodeUri: 'otpauth://totp/Test?secret=SECRET456',
      );
      when(() => mockRepository.setup2FA())
          .thenAnswer((_) async => setupResult);
      when(() => mockRepository.verify2FA('111111'))
          .thenAnswer((_) async => false);
      when(() => mockRepository.verify2FA('222222'))
          .thenAnswer((_) async => true);

      // Act
      await setupUseCase();
      final firstAttempt = await verifyUseCase('111111');
      final secondAttempt = await verifyUseCase('222222');

      // Assert
      expect(firstAttempt, isFalse);
      expect(secondAttempt, isTrue);
    });

    test('disable requires valid code format', () async {
      // Arrange
      when(() => mockRepository.disable2FA('999999'))
          .thenAnswer((_) async {});

      // Act
      await disableUseCase('999999');

      // Assert
      verify(() => mockRepository.disable2FA('999999')).called(1);
    });
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/domain/usecases/register.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';

import '../../../../helpers/mock_repositories.dart';
import '../../../../helpers/mock_factories.dart';

void main() {
  late RegisterUseCase useCase;
  late MockAuthRepository mockRepository;

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
            referralCode: null,
          )).thenAnswer((_) async => (mockUser, accessToken));

      final (user, token) = await useCase(
        email: validEmail,
        password: validPassword,
      );

      expect(user, equals(mockUser));
      expect(token, equals(accessToken));
      verify(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            referralCode: null,
          )).called(1);
    });

    test('passes referral code to repository when provided', () async {
      final mockUser = createMockUser(email: validEmail);
      when(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            referralCode: validReferralCode,
          )).thenAnswer((_) async => (mockUser, accessToken));

      final (user, token) = await useCase(
        email: validEmail,
        password: validPassword,
        referralCode: validReferralCode,
      );

      expect(user, equals(mockUser));
      expect(token, equals(accessToken));
      verify(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            referralCode: validReferralCode,
          )).called(1);
    });

    test('throws ArgumentError when email is empty', () async {
      expect(
        () => useCase(email: '', password: validPassword),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.register(
            email: any(named: 'email'),
            password: any(named: 'password'),
            referralCode: any(named: 'referralCode'),
          ));
    });

    test('throws ArgumentError when email is invalid format', () async {
      expect(
        () => useCase(email: 'bad-email', password: validPassword),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when password is empty', () async {
      expect(
        () => useCase(email: validEmail, password: ''),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when password is too weak (short)', () async {
      expect(
        () => useCase(email: validEmail, password: 'Ab1'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when password lacks uppercase', () async {
      expect(
        () => useCase(email: validEmail, password: 'password1'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when referral code is invalid', () async {
      // Referral code must be 6-20 alphanumeric chars
      expect(
        () => useCase(
          email: validEmail,
          password: validPassword,
          referralCode: 'AB',
        ),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('propagates AuthFailure for duplicate email', () async {
      when(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            referralCode: null,
          )).thenThrow(
              const AuthFailure(message: 'Email already exists', code: 409));

      expect(
        () => useCase(email: validEmail, password: validPassword),
        throwsA(isA<AuthFailure>()),
      );
    });

    test('propagates NetworkFailure from repository', () async {
      when(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            referralCode: null,
          )).thenThrow(
              const NetworkFailure(message: 'No internet connection'));

      expect(
        () => useCase(email: validEmail, password: validPassword),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('propagates ServerFailure from repository', () async {
      when(() => mockRepository.register(
            email: validEmail,
            password: validPassword,
            referralCode: null,
          )).thenThrow(
              const ServerFailure(message: 'Server error', code: 500));

      expect(
        () => useCase(email: validEmail, password: validPassword),
        throwsA(isA<ServerFailure>()),
      );
    });
  });
}

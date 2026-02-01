import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/domain/usecases/login.dart';
import 'package:cybervpn_mobile/features/auth/domain/entities/user_entity.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';

import '../../../../helpers/mock_repositories.dart';
import '../../../../helpers/mock_factories.dart';

void main() {
  late LoginUseCase useCase;
  late MockAuthRepository mockRepository;

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
          )).thenAnswer((_) async => (mockUser, accessToken));

      final (user, token) = await useCase(
        email: validEmail,
        password: validPassword,
      );

      expect(user, equals(mockUser));
      expect(token, equals(accessToken));
      verify(() => mockRepository.login(
            email: validEmail,
            password: validPassword,
          )).called(1);
    });

    test('throws ArgumentError when email is empty', () async {
      expect(
        () => useCase(email: '', password: validPassword),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.login(
            email: any(named: 'email'),
            password: any(named: 'password'),
          ));
    });

    test('throws ArgumentError when email is invalid format', () async {
      expect(
        () => useCase(email: 'not-an-email', password: validPassword),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.login(
            email: any(named: 'email'),
            password: any(named: 'password'),
          ));
    });

    test('throws ArgumentError when password is empty', () async {
      expect(
        () => useCase(email: validEmail, password: ''),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.login(
            email: any(named: 'email'),
            password: any(named: 'password'),
          ));
    });

    test('throws ArgumentError when password is too short', () async {
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

    test('throws ArgumentError when password lacks lowercase', () async {
      expect(
        () => useCase(email: validEmail, password: 'PASSWORD1'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('throws ArgumentError when password lacks digit', () async {
      expect(
        () => useCase(email: validEmail, password: 'Passwordx'),
        throwsA(isA<ArgumentError>()),
      );
    });

    test('propagates AuthFailure from repository', () async {
      when(() => mockRepository.login(
            email: validEmail,
            password: validPassword,
          )).thenThrow(
              const AuthFailure(message: 'Invalid credentials', code: 401));

      expect(
        () => useCase(email: validEmail, password: validPassword),
        throwsA(isA<AuthFailure>()),
      );
    });

    test('propagates NetworkFailure from repository', () async {
      when(() => mockRepository.login(
            email: validEmail,
            password: validPassword,
          )).thenThrow(
              const NetworkFailure(message: 'No internet connection'));

      expect(
        () => useCase(email: validEmail, password: validPassword),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('propagates ServerFailure from repository', () async {
      when(() => mockRepository.login(
            email: validEmail,
            password: validPassword,
          )).thenThrow(
              const ServerFailure(message: 'Internal server error', code: 500));

      expect(
        () => useCase(email: validEmail, password: validPassword),
        throwsA(isA<ServerFailure>()),
      );
    });
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/domain/usecases/refresh_token.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';

import '../../../../helpers/mock_repositories.dart';

void main() {
  late RefreshTokenUseCase useCase;
  late MockAuthRepository mockRepository;

  setUp(() {
    mockRepository = MockAuthRepository();
    useCase = RefreshTokenUseCase(mockRepository);
  });

  const validRefreshToken = 'valid-refresh-token-abc123';
  const newAccessToken = 'new-access-token-xyz789';

  group('RefreshTokenUseCase', () {
    test('returns new access token when refresh token is valid', () async {
      when(() => mockRepository.refreshToken(validRefreshToken))
          .thenAnswer((_) async => newAccessToken);

      final result = await useCase(validRefreshToken);

      expect(result, equals(newAccessToken));
      verify(() => mockRepository.refreshToken(validRefreshToken)).called(1);
    });

    test('throws ArgumentError when refresh token is empty', () async {
      expect(
        () => useCase(''),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.refreshToken(any()));
    });

    test('propagates AuthFailure for expired token', () async {
      when(() => mockRepository.refreshToken(validRefreshToken)).thenThrow(
          const AuthFailure(message: 'Token expired', code: 401));

      expect(
        () => useCase(validRefreshToken),
        throwsA(isA<AuthFailure>()),
      );
    });

    test('propagates AuthFailure for invalid token', () async {
      when(() => mockRepository.refreshToken('invalid-token')).thenThrow(
          const AuthFailure(message: 'Invalid token', code: 401));

      expect(
        () => useCase('invalid-token'),
        throwsA(isA<AuthFailure>()),
      );
    });

    test('propagates NetworkFailure from repository', () async {
      when(() => mockRepository.refreshToken(validRefreshToken)).thenThrow(
          const NetworkFailure(message: 'No internet connection'));

      expect(
        () => useCase(validRefreshToken),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('propagates ServerFailure from repository', () async {
      when(() => mockRepository.refreshToken(validRefreshToken)).thenThrow(
          const ServerFailure(message: 'Internal server error', code: 500));

      expect(
        () => useCase(validRefreshToken),
        throwsA(isA<ServerFailure>()),
      );
    });
  });
}

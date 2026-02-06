import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/features/auth/domain/usecases/refresh_token.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/types/result.dart';

import '../../../../helpers/mock_repositories.dart';

void main() {
  late RefreshTokenUseCase useCase;
  late MockAuthRepository mockRepository;

  setUp(() {
    mockRepository = MockAuthRepository();
    useCase = RefreshTokenUseCase(mockRepository);
  });

  const validRefreshToken = 'valid-refresh-token-abc123';
  const validDeviceId = 'test-device-id';
  const newAccessToken = 'new-access-token-xyz789';

  group('RefreshTokenUseCase', () {
    test('returns new access token when refresh token is valid', () async {
      when(() => mockRepository.refreshToken(
            refreshToken: validRefreshToken,
            deviceId: validDeviceId,
          )).thenAnswer((_) async => const Success(newAccessToken));

      final result = await useCase(
        refreshToken: validRefreshToken,
        deviceId: validDeviceId,
      );

      expect(result, isA<Success<String>>());
      expect((result as Success<String>).data, equals(newAccessToken));
      verify(() => mockRepository.refreshToken(
            refreshToken: validRefreshToken,
            deviceId: validDeviceId,
          )).called(1);
    });

    test('throws ArgumentError when refresh token is empty', () async {
      expect(
        () => useCase(refreshToken: '', deviceId: validDeviceId),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.refreshToken(
            refreshToken: any(named: 'refreshToken'),
            deviceId: any(named: 'deviceId'),
          ));
    });

    test('throws ArgumentError when device ID is empty', () async {
      expect(
        () => useCase(refreshToken: validRefreshToken, deviceId: ''),
        throwsA(isA<ArgumentError>()),
      );
      verifyNever(() => mockRepository.refreshToken(
            refreshToken: any(named: 'refreshToken'),
            deviceId: any(named: 'deviceId'),
          ));
    });

    test('propagates AuthFailure for expired token', () async {
      when(() => mockRepository.refreshToken(
            refreshToken: validRefreshToken,
            deviceId: validDeviceId,
          )).thenThrow(
          const AuthFailure(message: 'Token expired', code: 401));

      expect(
        () => useCase(refreshToken: validRefreshToken, deviceId: validDeviceId),
        throwsA(isA<AuthFailure>()),
      );
    });

    test('propagates AuthFailure for invalid token', () async {
      when(() => mockRepository.refreshToken(
            refreshToken: 'invalid-token',
            deviceId: validDeviceId,
          )).thenThrow(
          const AuthFailure(message: 'Invalid token', code: 401));

      expect(
        () => useCase(refreshToken: 'invalid-token', deviceId: validDeviceId),
        throwsA(isA<AuthFailure>()),
      );
    });

    test('propagates NetworkFailure from repository', () async {
      when(() => mockRepository.refreshToken(
            refreshToken: validRefreshToken,
            deviceId: validDeviceId,
          )).thenThrow(
          const NetworkFailure(message: 'No internet connection'));

      expect(
        () => useCase(refreshToken: validRefreshToken, deviceId: validDeviceId),
        throwsA(isA<NetworkFailure>()),
      );
    });

    test('propagates ServerFailure from repository', () async {
      when(() => mockRepository.refreshToken(
            refreshToken: validRefreshToken,
            deviceId: validDeviceId,
          )).thenThrow(
          const ServerFailure(message: 'Internal server error', code: 500));

      expect(
        () => useCase(refreshToken: validRefreshToken, deviceId: validDeviceId),
        throwsA(isA<ServerFailure>()),
      );
    });
  });
}

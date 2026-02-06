import 'package:cybervpn_mobile/core/errors/app_error.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' as failures;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AppError.fromFailure', () {
    test('maps NetworkFailure to NetworkError', () {
      const failure = failures.NetworkFailure(message: 'No connection');
      final error = AppError.fromFailure(failure);
      expect(error, isA<NetworkError>());
      expect(error.message, 'No connection');
    });

    test('maps AuthFailure to AuthError', () {
      const failure = failures.AuthFailure(message: 'Unauthorized', code: 401);
      final error = AppError.fromFailure(failure);
      expect(error, isA<AuthError>());
      expect(error.code, 401);
    });

    test('maps ServerFailure to ServerError', () {
      const failure = failures.ServerFailure(message: 'Internal', code: 500);
      final error = AppError.fromFailure(failure);
      expect(error, isA<ServerError>());
    });

    test('maps SubscriptionFailure to SubscriptionError', () {
      const failure = failures.SubscriptionFailure(message: 'Expired');
      final error = AppError.fromFailure(failure);
      expect(error, isA<SubscriptionError>());
    });

    test('maps VpnFailure to VpnError', () {
      const failure = failures.VpnFailure(message: 'Tunnel failed');
      final error = AppError.fromFailure(failure);
      expect(error, isA<VpnError>());
    });

    test('maps CacheFailure to CacheError', () {
      const failure = failures.CacheFailure(message: 'Read error');
      final error = AppError.fromFailure(failure);
      expect(error, isA<CacheError>());
    });

    test('maps ValidationFailure to ValidationError', () {
      const failure = failures.ValidationFailure(message: 'Invalid email');
      final error = AppError.fromFailure(failure);
      expect(error, isA<ValidationError>());
    });

    test('maps TimeoutFailure to TimeoutError', () {
      const failure = failures.TimeoutFailure(message: 'Timed out');
      final error = AppError.fromFailure(failure);
      expect(error, isA<TimeoutError>());
    });

    test('maps UnknownFailure to UnknownError', () {
      const failure = failures.UnknownFailure(message: 'Unknown');
      final error = AppError.fromFailure(failure);
      expect(error, isA<UnknownError>());
    });
  });

  group('AppError exhaustive switch', () {
    test('all subtypes are matchable', () {
      final errors = <AppError>[
        const NetworkError(message: 'net'),
        const AuthError(message: 'auth'),
        const ServerError(message: 'srv'),
        const SubscriptionError(message: 'sub'),
        const VpnError(message: 'vpn'),
        const CacheError(message: 'cache'),
        const ValidationError(message: 'val'),
        const TimeoutError(message: 'timeout'),
        const UnknownError(message: 'unknown'),
      ];

      for (final error in errors) {
        // This switch must compile exhaustively
        final label = switch (error) {
          NetworkError() => 'network',
          AuthError() => 'auth',
          ServerError() => 'server',
          SubscriptionError() => 'subscription',
          VpnError() => 'vpn',
          CacheError() => 'cache',
          ValidationError() => 'validation',
          TimeoutError() => 'timeout',
          UnknownError() => 'unknown',
        };
        expect(label, isNotEmpty);
      }
    });
  });

  group('AuthErrorCode', () {
    test('AuthError carries errorCode', () {
      const error = AuthError(
        message: 'Bad creds',
        errorCode: AuthErrorCode.invalidCredentials,
      );
      expect(error.errorCode, AuthErrorCode.invalidCredentials);
    });

    test('AuthError defaults to unknown errorCode', () {
      const error = AuthError(message: 'Unknown auth error');
      expect(error.errorCode, AuthErrorCode.unknown);
    });
  });

  group('ResultAppErrorExtension', () {
    test('appErrorOrNull returns null for Success', () {
      const result = Success(42);
      expect(result.appErrorOrNull, isNull);
    });

    test('appErrorOrNull returns AppError for Failure', () {
      const result = Failure<int>(
        failures.NetworkFailure(message: 'No internet'),
      );
      final error = result.appErrorOrNull;
      expect(error, isA<NetworkError>());
      expect(error!.message, 'No internet');
    });
  });
}

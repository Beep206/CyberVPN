import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/network_error_handler.dart';

/// Concrete class that uses the [NetworkErrorHandler] mixin for testing.
class _TestHandler with NetworkErrorHandler {}

void main() {
  late _TestHandler handler;

  setUp(() {
    handler = _TestHandler();
  });

  /// Helper to create a [DioException] with a given status code.
  DioException makeDioException({
    required int statusCode,
    String? statusMessage,
    DioExceptionType type = DioExceptionType.badResponse,
    Map<String, List<String>>? headers,
  }) {
    final requestOptions = RequestOptions(path: '/test');
    return DioException(
      requestOptions: requestOptions,
      type: type,
      response: Response(
        requestOptions: requestOptions,
        statusCode: statusCode,
        statusMessage: statusMessage,
        headers: headers != null ? Headers.fromMap(headers) : null,
      ),
    );
  }

  /// Helper to create a connection-type [DioException].
  DioException makeConnectionException(DioExceptionType type) {
    return DioException(
      requestOptions: RequestOptions(path: '/test'),
      type: type,
    );
  }

  group('NetworkErrorHandler.handleNetworkError', () {
    group('401 Unauthorized', () {
      test('re-throws the DioException for auth interceptor to handle', () {
        final exception = makeDioException(statusCode: 401);

        expect(
          () => handler.handleNetworkError(exception),
          throwsA(isA<DioException>()),
        );
      });
    });

    group('403 Forbidden', () {
      test('returns AccessDeniedFailure', () async {
        final exception = makeDioException(
          statusCode: 403,
          statusMessage: 'Forbidden',
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<AccessDeniedFailure>());
        expect(result.code, 403);
        expect(result.message, 'Forbidden');
      });

      test('returns AccessDeniedFailure with default message when statusMessage is null', () async {
        final exception = makeDioException(statusCode: 403);

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<AccessDeniedFailure>());
        expect(result.message, 'Access denied');
      });
    });

    group('429 Too Many Requests', () {
      test('returns RateLimitFailure', () async {
        final exception = makeDioException(statusCode: 429);

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<RateLimitFailure>());
        expect(result.code, 429);
        expect(result.message, 'Too many requests. Please try again later.');
      });

      test('parses Retry-After header in seconds', () async {
        final exception = makeDioException(
          statusCode: 429,
          headers: {
            'retry-after': ['30'],
          },
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<RateLimitFailure>());
        final rateLimitFailure = result as RateLimitFailure;
        expect(rateLimitFailure.retryAfter, const Duration(seconds: 30));
      });

      test('handles missing Retry-After header', () async {
        final exception = makeDioException(statusCode: 429);

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<RateLimitFailure>());
        final rateLimitFailure = result as RateLimitFailure;
        expect(rateLimitFailure.retryAfter, isNull);
      });

      test('handles non-numeric Retry-After header', () async {
        final exception = makeDioException(
          statusCode: 429,
          headers: {
            'retry-after': ['not-a-number'],
          },
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<RateLimitFailure>());
        final rateLimitFailure = result as RateLimitFailure;
        expect(rateLimitFailure.retryAfter, isNull);
      });
    });

    group('5xx Server Errors', () {
      test('returns ServerFailure when no Dio instance for retry', () async {
        final exception = makeDioException(
          statusCode: 500,
          statusMessage: 'Internal Server Error',
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<ServerFailure>());
        expect(result.code, 500);
      });

      test('returns ServerFailure for 502', () async {
        final exception = makeDioException(statusCode: 502);

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<ServerFailure>());
        expect(result.code, 502);
      });

      test('returns ServerFailure for 503', () async {
        final exception = makeDioException(statusCode: 503);

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<ServerFailure>());
        expect(result.code, 503);
      });
    });

    group('Other 4xx Client Errors', () {
      test('returns ServerFailure for 400', () async {
        final exception = makeDioException(
          statusCode: 400,
          statusMessage: 'Bad Request',
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<ServerFailure>());
        expect(result.code, 400);
        expect(result.message, 'Bad Request');
      });

      test('returns ServerFailure for 404', () async {
        final exception = makeDioException(
          statusCode: 404,
          statusMessage: 'Not Found',
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<ServerFailure>());
        expect(result.code, 404);
      });

      test('returns ServerFailure for 422', () async {
        final exception = makeDioException(statusCode: 422);

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<ServerFailure>());
        expect(result.code, 422);
      });
    });

    group('Connection Errors', () {
      test('returns NetworkFailure for connectionError', () async {
        final exception = makeConnectionException(
          DioExceptionType.connectionError,
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<NetworkFailure>());
        expect(result.message, 'No internet connection available');
      });

      test('returns NetworkFailure for connectionTimeout', () async {
        final exception = makeConnectionException(
          DioExceptionType.connectionTimeout,
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<NetworkFailure>());
        expect(result.message, 'Connection timed out');
      });

      test('returns NetworkFailure for sendTimeout', () async {
        final exception = makeConnectionException(
          DioExceptionType.sendTimeout,
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<NetworkFailure>());
        expect(result.message, 'Connection timed out');
      });

      test('returns NetworkFailure for receiveTimeout', () async {
        final exception = makeConnectionException(
          DioExceptionType.receiveTimeout,
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<NetworkFailure>());
        expect(result.message, 'Connection timed out');
      });

      test('returns NetworkFailure for cancel', () async {
        final exception = makeConnectionException(
          DioExceptionType.cancel,
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<NetworkFailure>());
        expect(result.message, 'Request was cancelled');
      });
    });

    group('Unknown Errors', () {
      test('returns UnknownFailure for unknown DioExceptionType', () async {
        final exception = makeConnectionException(
          DioExceptionType.unknown,
        );

        final result = await handler.handleNetworkError(exception);

        expect(result, isA<UnknownFailure>());
      });
    });
  });

  group('NetworkErrorHandler.mapExceptionToFailure', () {
    test('maps AuthException to AuthFailure', () {
      const exception = AuthException(message: 'Unauthorized', code: 401);

      final result = handler.mapExceptionToFailure(exception);

      expect(result, isA<AuthFailure>());
      expect(result.message, 'Unauthorized');
      expect(result.code, 401);
    });

    test('maps NetworkException to NetworkFailure', () {
      const exception = NetworkException(message: 'No connection');

      final result = handler.mapExceptionToFailure(exception);

      expect(result, isA<NetworkFailure>());
      expect(result.message, 'No connection');
    });

    test('maps ServerException to ServerFailure', () {
      const exception = ServerException(message: 'Internal error', code: 500);

      final result = handler.mapExceptionToFailure(exception);

      expect(result, isA<ServerFailure>());
      expect(result.code, 500);
    });

    test('maps ServerException with 403 to AccessDeniedFailure', () {
      const exception = ServerException(message: 'Forbidden', code: 403);

      final result = handler.mapExceptionToFailure(exception);

      expect(result, isA<AccessDeniedFailure>());
      expect(result.code, 403);
    });

    test('maps ServerException with 429 to RateLimitFailure', () {
      const exception = ServerException(message: 'Too Many Requests', code: 429);

      final result = handler.mapExceptionToFailure(exception);

      expect(result, isA<RateLimitFailure>());
      expect(result.code, 429);
    });

    test('maps CacheException to CacheFailure', () {
      const exception = CacheException(message: 'Cache miss');

      final result = handler.mapExceptionToFailure(exception);

      expect(result, isA<CacheFailure>());
      expect(result.message, 'Cache miss');
    });
  });

  group('NetworkErrorHandler constants', () {
    test('maxRetryAttempts is 3', () {
      expect(NetworkErrorHandler.maxRetryAttempts, 3);
    });

    test('retryDelays has correct exponential backoff durations', () {
      expect(NetworkErrorHandler.retryDelays.length, 3);
      expect(NetworkErrorHandler.retryDelays[0], const Duration(seconds: 1));
      expect(NetworkErrorHandler.retryDelays[1], const Duration(seconds: 2));
      expect(NetworkErrorHandler.retryDelays[2], const Duration(seconds: 4));
    });
  });

  group('Failure types', () {
    test('AccessDeniedFailure supports equality', () {
      const failure1 = AccessDeniedFailure(message: 'Access denied', code: 403);
      const failure2 = AccessDeniedFailure(message: 'Access denied', code: 403);

      expect(failure1, equals(failure2));
    });

    test('RateLimitFailure includes retryAfter in equality', () {
      const failure1 = RateLimitFailure(
        message: 'Rate limited',
        code: 429,
        retryAfter: Duration(seconds: 30),
      );
      const failure2 = RateLimitFailure(
        message: 'Rate limited',
        code: 429,
        retryAfter: Duration(seconds: 30),
      );
      const failure3 = RateLimitFailure(
        message: 'Rate limited',
        code: 429,
        retryAfter: Duration(seconds: 60),
      );

      expect(failure1, equals(failure2));
      expect(failure1, isNot(equals(failure3)));
    });
  });
}

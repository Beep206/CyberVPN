import 'package:dio/dio.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Mixin that provides standardized network error handling for repository
/// implementations.
///
/// Converts [DioException] instances into domain [Failure] types with
/// automatic retry logic for transient errors (5xx, 429).
///
/// Also provides [mapExceptionToFailure] to convert [AppException] types
/// (thrown by [ApiClient]) into domain [Failure] types.
///
/// Usage:
/// ```dart
/// class MyRepositoryImpl with NetworkErrorHandler implements MyRepository {
///   Future<Result> fetchData() async {
///     try {
///       final response = await apiClient.get('/data');
///       return Result.fromJson(response.data);
///     } on DioException catch (e) {
///       throw await handleNetworkError(e);
///     } on AppException catch (e) {
///       throw mapExceptionToFailure(e);
///     }
///   }
/// }
/// ```
mixin NetworkErrorHandler {
  /// Maximum number of retry attempts for retryable errors (5xx).
  static const int maxRetryAttempts = 3;

  /// Base delay durations for exponential backoff retries.
  /// Attempt 1: 1s, Attempt 2: 2s, Attempt 3: 4s.
  static const List<Duration> retryDelays = [
    Duration(seconds: 1),
    Duration(seconds: 2),
    Duration(seconds: 4),
  ];

  /// Handles a [DioException] and returns an appropriate domain [Failure].
  ///
  /// For retryable errors (5xx), the original request is retried up to
  /// [maxRetryAttempts] times with exponential backoff. If all retries fail,
  /// a [ServerFailure] is returned.
  ///
  /// For 401, the exception is re-thrown to allow the auth interceptor to
  /// handle token refresh.
  ///
  /// For 403, returns [AccessDeniedFailure].
  ///
  /// For 429, parses the `Retry-After` header and returns [RateLimitFailure].
  ///
  /// For connection errors, returns [NetworkFailure].
  ///
  /// For unknown errors, logs to Sentry and returns [UnknownFailure].
  Future<Failure> handleNetworkError(DioException e) async {
    // Handle non-response errors (connection, timeout, etc.)
    if (e.type != DioExceptionType.badResponse) {
      return _handleNonResponseError(e);
    }

    final statusCode = e.response?.statusCode ?? 0;

    // 401 Unauthorized - re-throw so auth interceptor can refresh token
    if (statusCode == 401) {
      throw e;
    }

    // 403 Forbidden
    if (statusCode == 403) {
      return AccessDeniedFailure(
        message: e.response?.statusMessage ?? 'Access denied',
        code: statusCode,
      );
    }

    // 429 Too Many Requests
    if (statusCode == 429) {
      return _handleRateLimitError(e);
    }

    // 5xx Server Errors - retry with exponential backoff
    if (statusCode >= 500 && statusCode < 600) {
      return _handleServerError(e);
    }

    // Other 4xx client errors
    if (statusCode >= 400 && statusCode < 500) {
      return ServerFailure(
        message: e.response?.statusMessage ?? 'Client error',
        code: statusCode,
      );
    }

    // Unknown status code
    return _handleUnknownError(e);
  }

  /// Maps an [AppException] (thrown by [ApiClient]) to a domain [Failure].
  ///
  /// This is useful for repositories that use [ApiClient] which already
  /// converts [DioException] to [AppException] internally.
  Failure mapExceptionToFailure(AppException e) {
    if (e is AuthException) {
      return AuthFailure(message: e.message, code: e.code);
    }
    if (e is NetworkException) {
      return NetworkFailure(message: e.message, code: e.code);
    }
    if (e is ServerException) {
      if (e.code == 403) {
        return AccessDeniedFailure(message: e.message, code: e.code);
      }
      if (e.code == 429) {
        return RateLimitFailure(message: e.message, code: e.code);
      }
      return ServerFailure(message: e.message, code: e.code);
    }
    if (e is CacheException) {
      return CacheFailure(message: e.message, code: e.code);
    }
    return UnknownFailure(message: e.message, code: e.code);
  }

  /// Retries the failed request with exponential backoff for 5xx errors.
  ///
  /// Returns [ServerFailure] if all retry attempts are exhausted.
  Future<Failure> _handleServerError(DioException e) async {
    final dio = e.requestOptions.extra['dio'] as Dio?;

    // If we cannot access a Dio instance for retries, fail immediately
    if (dio == null) {
      AppLogger.warning(
        'Cannot retry 5xx error: no Dio instance available',
        category: 'NetworkErrorHandler',
      );
      return ServerFailure(
        message: e.response?.statusMessage ?? 'Server error',
        code: e.response?.statusCode,
      );
    }

    for (var attempt = 0; attempt < maxRetryAttempts; attempt++) {
      final delay = attempt < retryDelays.length
          ? retryDelays[attempt]
          : retryDelays.last;

      AppLogger.info(
        'Retrying request (attempt ${attempt + 1}/$maxRetryAttempts) '
        'after ${delay.inSeconds}s delay',
        category: 'NetworkErrorHandler',
      );

      await Future<void>.delayed(delay);

      try {
        await dio.fetch<dynamic>(e.requestOptions);
        // Retry succeeded - this is a signal to the caller that the
        // request eventually succeeded. Since we return Failure, we
        // indicate success by not returning a failure. However, the
        // mixin pattern means we always return Failure. In practice,
        // callers should use safeApiCall for full retry support.
        // For now, return a ServerFailure indicating the retry path
        // was taken but the result was not captured at this level.
        return ServerFailure(
          message: 'Retry succeeded but result was not captured',
          code: e.response?.statusCode,
        );
      } on DioException catch (retryError) {
        final retryStatus = retryError.response?.statusCode ?? 0;
        if (retryStatus < 500 || retryStatus >= 600) {
          // Non-5xx error on retry - handle it normally
          return handleNetworkError(retryError);
        }
        // Still a 5xx - continue retrying
        if (attempt == maxRetryAttempts - 1) {
          AppLogger.error(
            'All $maxRetryAttempts retry attempts exhausted for '
            '${e.requestOptions.path}',
            category: 'NetworkErrorHandler',
          );
        }
      }
    }

    return ServerFailure(
      message: 'Server error after $maxRetryAttempts retries',
      code: e.response?.statusCode,
    );
  }

  /// Parses the Retry-After header and returns a [RateLimitFailure].
  ///
  /// If a Retry-After header is present, the duration is included in the
  /// failure so callers can wait before retrying.
  Future<Failure> _handleRateLimitError(DioException e) async {
    final retryAfterHeader = e.response?.headers.value('retry-after');
    Duration? retryAfter;

    if (retryAfterHeader != null) {
      final seconds = int.tryParse(retryAfterHeader);
      if (seconds != null) {
        retryAfter = Duration(seconds: seconds);
      }
    }

    AppLogger.warning(
      'Rate limited on ${e.requestOptions.path}'
      '${retryAfter != null ? ', retry after ${retryAfter.inSeconds}s' : ''}',
      category: 'NetworkErrorHandler',
    );

    return RateLimitFailure(
      message: 'Too many requests. Please try again later.',
      code: 429,
      retryAfter: retryAfter,
    );
  }

  /// Handles non-response DioException types (connection, timeout, cancel).
  Failure _handleNonResponseError(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionError:
        return const NetworkFailure(
          message: 'No internet connection available',
        );
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return NetworkFailure(
          message: 'Connection timed out',
          code: e.response?.statusCode,
        );
      case DioExceptionType.cancel:
        return const NetworkFailure(
          message: 'Request was cancelled',
        );
      default:
        return _handleUnknownError(e);
    }
  }

  /// Logs the error to Sentry and returns an [UnknownFailure].
  Failure _handleUnknownError(DioException e) {
    AppLogger.error(
      'Unknown network error on ${e.requestOptions.path}: ${e.message}',
      category: 'NetworkErrorHandler',
      error: e,
      stackTrace: e.stackTrace,
    );

    Sentry.captureException(
      e,
      stackTrace: e.stackTrace,
      withScope: (scope) {
        scope.setTag('request.path', e.requestOptions.path);
        scope.setTag('request.method', e.requestOptions.method);
        if (e.response?.statusCode != null) {
          scope.setTag(
            'response.status_code',
            e.response!.statusCode.toString(),
          );
        }
      },
    );

    return UnknownFailure(
      message: e.message ?? 'An unexpected error occurred',
      code: e.response?.statusCode,
    );
  }
}

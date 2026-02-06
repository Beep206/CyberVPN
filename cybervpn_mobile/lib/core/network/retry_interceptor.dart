import 'dart:async';
import 'dart:math';

import 'package:dio/dio.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Dio interceptor that retries failed requests with exponential backoff.
///
/// Retries on:
/// - 5xx server errors
/// - Connection timeouts
/// - Send timeouts
/// - Receive timeouts (optional)
/// - Connection errors (no internet)
///
/// Does NOT retry:
/// - 4xx client errors (bad request, unauthorized, etc.)
/// - Cancel errors
/// - Non-idempotent methods by default (POST, PATCH, DELETE)
class RetryInterceptor extends Interceptor {
  final Dio _dio;
  final int maxRetries;
  final Duration initialDelay;
  final bool retryOnTimeout;
  final bool retryNonIdempotent;

  RetryInterceptor({
    required Dio dio,
    this.maxRetries = 3,
    this.initialDelay = const Duration(milliseconds: 500),
    this.retryOnTimeout = true,
    this.retryNonIdempotent = false,
  }) : _dio = dio;

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final attempt = _getAttempt(err.requestOptions);

    if (attempt >= maxRetries || !_shouldRetry(err)) {
      return handler.next(err);
    }

    final delay = _calculateDelay(attempt);
    final nextAttempt = attempt + 1;

    AppLogger.debug(
      'Retrying request (attempt $nextAttempt/$maxRetries) '
      'after ${delay.inMilliseconds}ms: '
      '${err.requestOptions.method} ${err.requestOptions.path}',
      category: 'network.retry',
    );

    await Future<void>.delayed(delay);

    try {
      err.requestOptions.extra['_retryAttempt'] = nextAttempt;
      final response = await _dio.fetch<dynamic>(err.requestOptions);
      return handler.resolve(response);
    } on DioException catch (e) {
      return handler.next(e);
    }
  }

  bool _shouldRetry(DioException err) {
    // Don't retry cancelled requests.
    if (err.type == DioExceptionType.cancel) return false;

    // Don't retry non-idempotent methods unless configured.
    if (!retryNonIdempotent) {
      final method = err.requestOptions.method.toUpperCase();
      if (method == 'POST' || method == 'PATCH' || method == 'DELETE') {
        return false;
      }
    }

    // Retry on timeout errors.
    if (retryOnTimeout) {
      if (err.type == DioExceptionType.connectionTimeout ||
          err.type == DioExceptionType.sendTimeout ||
          err.type == DioExceptionType.receiveTimeout) {
        return true;
      }
    }

    // Retry on connection errors (no internet, DNS failure, etc.).
    if (err.type == DioExceptionType.connectionError) return true;

    // Retry on 5xx server errors.
    final statusCode = err.response?.statusCode;
    if (statusCode != null && statusCode >= 500) return true;

    return false;
  }

  int _getAttempt(RequestOptions options) {
    return (options.extra['_retryAttempt'] as int?) ?? 0;
  }

  /// Exponential backoff with jitter: delay = initialDelay * 2^attempt + jitter
  Duration _calculateDelay(int attempt) {
    final baseMs = initialDelay.inMilliseconds * pow(2, attempt);
    final jitter = Random().nextInt(initialDelay.inMilliseconds);
    return Duration(milliseconds: baseMs.toInt() + jitter);
  }
}

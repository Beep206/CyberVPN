import 'dart:async';

import 'package:dio/dio.dart';

import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Represents a queued request waiting for token refresh to complete.
class _QueuedRequest {
  final DioException error;
  final ErrorInterceptorHandler handler;
  final Completer<void> completer;

  _QueuedRequest({
    required this.error,
    required this.handler,
  }) : completer = Completer<void>();
}

/// Interceptor that handles JWT authentication and token refresh.
///
/// Features:
/// - Automatically attaches access token to requests
/// - Handles 401 errors by refreshing the token
/// - Queues concurrent 401 requests to prevent multiple refresh calls
/// - Retries all queued requests after successful refresh
class AuthInterceptor extends Interceptor {
  final SecureStorageWrapper _secureStorage;
  final Dio _dio;

  /// Whether a token refresh is currently in progress.
  bool _isRefreshing = false;

  /// Queue of requests waiting for token refresh to complete.
  final List<_QueuedRequest> _requestQueue = [];

  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';

  /// Extra key used to mark refresh requests so they bypass the 401 handler.
  /// Without this, a 401 response from the refresh endpoint itself would
  /// trigger another refresh attempt, creating an infinite loop.
  static const String _isRefreshRequestKey = '_isRefreshRequest';

  AuthInterceptor({
    required SecureStorageWrapper secureStorage,
    required Dio dio,
  })  : _secureStorage = secureStorage,
        _dio = dio;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _secureStorage.read(key: _accessTokenKey);
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    // Only handle 401 Unauthorized errors
    if (err.response?.statusCode != 401) {
      handler.next(err);
      return;
    }

    // Skip 401 handling for the refresh request itself to prevent
    // an infinite loop when the refresh token is also expired.
    if (err.requestOptions.extra[_isRefreshRequestKey] == true) {
      AppLogger.warning(
        'Refresh request returned 401 -- refresh token is expired',
        category: 'auth.interceptor',
      );
      handler.next(err);
      return;
    }

    // If refresh is already in progress, queue this request
    if (_isRefreshing) {
      AppLogger.debug(
        'Token refresh in progress, queuing request: ${err.requestOptions.path}',
        category: 'auth.interceptor',
      );
      await _queueRequest(err, handler);
      return;
    }

    // Start the refresh process
    _isRefreshing = true;
    AppLogger.info(
      'Starting token refresh for 401 on: ${err.requestOptions.path}',
      category: 'auth.interceptor',
    );

    try {
      final refreshToken = await _secureStorage.read(key: _refreshTokenKey);
      if (refreshToken == null) {
        AppLogger.warning(
          'No refresh token available',
          category: 'auth.interceptor',
        );
        _failAllQueuedRequests(err);
        handler.next(err);
        return;
      }

      // Perform the token refresh. The extra flag prevents the interceptor
      // from attempting to refresh again if this request itself returns 401.
      final response = await _dio.post<Map<String, dynamic>>(
        '/mobile/auth/refresh',
        data: {'refresh_token': refreshToken},
        options: Options(extra: {_isRefreshRequestKey: true}),
      );

      final responseData = response.data!;
      final newAccessToken = responseData['access_token'] as String;
      final newRefreshToken = responseData['refresh_token'] as String?;

      // Store new tokens atomically
      await Future.wait([
        _secureStorage.write(key: _accessTokenKey, value: newAccessToken),
        if (newRefreshToken != null)
          _secureStorage.write(key: _refreshTokenKey, value: newRefreshToken),
      ]);

      AppLogger.info(
        'Token refresh successful, retrying original request and ${_requestQueue.length} queued requests',
        category: 'auth.interceptor',
      );

      // Retry the original request that triggered the refresh
      final retryResponse = await _retryRequest(err.requestOptions, newAccessToken);
      handler.resolve(retryResponse);

      // Retry all queued requests with the new token
      await _retryAllQueuedRequests(newAccessToken);
    } catch (e, st) {
      AppLogger.error(
        'Token refresh failed',
        error: e,
        stackTrace: st,
        category: 'auth.interceptor',
      );

      // Clear tokens on refresh failure
      await _secureStorage.delete(key: _accessTokenKey);
      await _secureStorage.delete(key: _refreshTokenKey);

      // Fail all queued requests
      _failAllQueuedRequests(err);

      // Fail the original request
      handler.next(err);
    } finally {
      _isRefreshing = false;
    }
  }

  /// Queues a request to wait for token refresh to complete.
  Future<void> _queueRequest(
    DioException error,
    ErrorInterceptorHandler handler,
  ) async {
    final queuedRequest = _QueuedRequest(error: error, handler: handler);
    _requestQueue.add(queuedRequest);

    // Wait for this request to be processed (either retried or failed)
    await queuedRequest.completer.future;
  }

  /// Retries all queued requests with the new access token.
  Future<void> _retryAllQueuedRequests(String newAccessToken) async {
    final requests = List<_QueuedRequest>.from(_requestQueue);
    _requestQueue.clear();

    for (final queued in requests) {
      try {
        final response = await _retryRequest(
          queued.error.requestOptions,
          newAccessToken,
        );
        queued.handler.resolve(response);
      } catch (e) {
        // If retry fails, pass the original error
        queued.handler.next(queued.error);
      } finally {
        if (!queued.completer.isCompleted) {
          queued.completer.complete();
        }
      }
    }
  }

  /// Fails all queued requests with the given error.
  void _failAllQueuedRequests(DioException originalError) {
    final requests = List<_QueuedRequest>.from(_requestQueue);
    _requestQueue.clear();

    for (final queued in requests) {
      queued.handler.next(originalError);
      if (!queued.completer.isCompleted) {
        queued.completer.complete();
      }
    }
  }

  /// Retries a request with a new access token.
  Future<Response<dynamic>> _retryRequest(
    RequestOptions options,
    String newAccessToken,
  ) async {
    final retryOptions = options.copyWith(
      headers: {
        ...options.headers,
        'Authorization': 'Bearer $newAccessToken',
      },
    );
    return _dio.fetch(retryOptions);
  }
}

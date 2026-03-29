import 'package:dio/dio.dart';

import 'package:cybervpn_mobile/core/auth/token_refresh_coordinator.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Interceptor that handles JWT authentication and token refresh.
///
/// Features:
/// - Automatically attaches access token to requests
/// - Handles 401 errors by refreshing the token
/// - Queues concurrent 401 requests to prevent multiple refresh calls
/// - Retries all queued requests after successful refresh
class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required SecureStorageWrapper secureStorage,
    required Dio dio,
    required TokenRefreshCoordinator tokenRefreshCoordinator,
  }) : _secureStorage = secureStorage,
       _dio = dio,
       _tokenRefreshCoordinator = tokenRefreshCoordinator;

  final SecureStorageWrapper _secureStorage;
  final Dio _dio;
  final TokenRefreshCoordinator _tokenRefreshCoordinator;

  static const String _accessTokenKey = 'access_token';

  static const String skipAuthHeaderKey = '_skipAuthHeader';
  static const String skipAuthRefreshHandlingKey = '_skipAuthRefreshHandling';
  static const String hasRetriedAfterRefreshKey = '_hasRetriedAfterRefresh';

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    if (options.extra[skipAuthHeaderKey] == true) {
      handler.next(options);
      return;
    }

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

    if (err.requestOptions.extra[skipAuthRefreshHandlingKey] == true ||
        err.requestOptions.extra[hasRetriedAfterRefreshKey] == true) {
      handler.next(err);
      return;
    }

    try {
      final token = await _tokenRefreshCoordinator.refresh(
        reason: 'reactive-401:${err.requestOptions.path}',
      );

      final retryResponse = await _retryRequest(
        err.requestOptions,
        token.accessToken,
      );
      handler.resolve(retryResponse);
    } catch (e, st) {
      AppLogger.error(
        'Reactive token refresh failed',
        error: e,
        stackTrace: st,
        category: 'auth.interceptor',
      );
      handler.next(err);
    }
  }

  /// Retries a request with a new access token.
  Future<Response<dynamic>> _retryRequest(
    RequestOptions options,
    String newAccessToken,
  ) async {
    final retryOptions = options.copyWith(
      headers: {...options.headers, 'Authorization': 'Bearer $newAccessToken'},
      extra: {...options.extra, hasRetriedAfterRefreshKey: true},
    );
    return _dio.fetch(retryOptions);
  }
}

import 'package:dio/dio.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

class AuthInterceptor extends Interceptor {
  final SecureStorageWrapper _secureStorage;
  final Dio _dio;
  bool _isRefreshing = false;

  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';

  AuthInterceptor({required SecureStorageWrapper secureStorage, required Dio dio})
      : _secureStorage = secureStorage,
        _dio = dio;

  @override
  Future<void> onRequest(RequestOptions options, RequestInterceptorHandler handler) async {
    final token = await _secureStorage.read(key: _accessTokenKey);
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(DioException err, ErrorInterceptorHandler handler) async {
    if (err.response?.statusCode == 401 && !_isRefreshing) {
      _isRefreshing = true;
      try {
        final refreshToken = await _secureStorage.read(key: _refreshTokenKey);
        if (refreshToken == null) {
          handler.next(err);
          return;
        }
        final response = await _dio.post('/auth/refresh', data: {'refresh_token': refreshToken});
        final responseData = response.data as Map<String, dynamic>;
        final newAccessToken = responseData['access_token'] as String;
        final newRefreshToken = responseData['refresh_token'] as String?;
        await _secureStorage.write(key: _accessTokenKey, value: newAccessToken);
        if (newRefreshToken != null) {
          await _secureStorage.write(key: _refreshTokenKey, value: newRefreshToken);
        }
        final retryOptions = err.requestOptions;
        retryOptions.headers['Authorization'] = 'Bearer $newAccessToken';
        final retryResponse = await _dio.fetch(retryOptions);
        handler.resolve(retryResponse);
      } catch (e) {
        AppLogger.error('Token refresh failed', error: e);
        await _secureStorage.delete(key: _accessTokenKey);
        await _secureStorage.delete(key: _refreshTokenKey);
        handler.next(err);
      } finally {
        _isRefreshing = false;
      }
    } else {
      handler.next(err);
    }
  }
}

import 'dart:io';
import 'package:dio/dio.dart';
import 'package:dio/io.dart';
import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/security/certificate_pinner.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

class ApiClient {
  late final Dio _dio;

  ApiClient({Dio? dio, String? baseUrl, CertificatePinner? certificatePinner}) {
    _dio = dio ?? Dio();

    _dio.options = BaseOptions(
      baseUrl: baseUrl ?? EnvironmentConfig.baseUrl,
      connectTimeout: const Duration(milliseconds: ApiConstants.connectTimeout),
      receiveTimeout: const Duration(milliseconds: ApiConstants.receiveTimeout),
      sendTimeout: const Duration(milliseconds: ApiConstants.sendTimeout),
      contentType: ApiConstants.contentType,
    );

    // Configure certificate pinning if fingerprints are provided
    final fingerprints = EnvironmentConfig.certificateFingerprints;
    if (fingerprints.isNotEmpty) {
      final pinner = certificatePinner ?? CertificatePinner(
        pinnedFingerprints: fingerprints,
      );
      _configureCertificatePinning(pinner);

      AppLogger.info(
        'Certificate pinning enabled',
        category: 'ApiClient',
        data: {'fingerprints_count': fingerprints.length},
      );
    } else {
      AppLogger.debug(
        'Certificate pinning disabled (no fingerprints configured)',
        category: 'ApiClient',
      );
    }

    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      logPrint: (obj) => AppLogger.debug(obj.toString()),
    ));
  }

  /// Configures the Dio client to use certificate pinning.
  ///
  /// Sets up an [IOHttpClientAdapter] with a custom [HttpClient] that
  /// validates certificates against the provided [pinner].
  void _configureCertificatePinning(CertificatePinner pinner) {
    final adapter = IOHttpClientAdapter(
      createHttpClient: () {
        final client = pinner.createHttpClient();

        // Additional security settings
        client.connectionTimeout = const Duration(
          milliseconds: ApiConstants.connectTimeout,
        );
        client.idleTimeout = const Duration(seconds: 15);

        return client;
      },
    );

    _dio.httpClientAdapter = adapter;
  }

  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? queryParameters, Options? options}) async {
    try {
      return await _dio.get<T>(path, queryParameters: queryParameters, options: options);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<Response<T>> post<T>(String path, {dynamic data, Options? options}) async {
    try {
      return await _dio.post<T>(path, data: data, options: options);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<Response<T>> patch<T>(String path, {dynamic data, Options? options}) async {
    try {
      return await _dio.patch<T>(path, data: data, options: options);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<Response<T>> delete<T>(String path, {Options? options}) async {
    try {
      return await _dio.delete<T>(path, options: options);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  void addInterceptor(Interceptor interceptor) {
    _dio.interceptors.add(interceptor);
  }

  AppException _handleDioError(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return NetworkException(message: 'Connection timed out', code: e.response?.statusCode);
      case DioExceptionType.connectionError:
        return const NetworkException(message: 'No internet connection');
      case DioExceptionType.badResponse:
        final statusCode = e.response?.statusCode ?? 0;
        if (statusCode == 401) {
          return AuthException(message: 'Unauthorized', code: statusCode);
        }
        return ServerException(message: e.response?.statusMessage ?? 'Server error', code: statusCode);
      default:
        return ServerException(message: e.message ?? 'Unknown error');
    }
  }
}

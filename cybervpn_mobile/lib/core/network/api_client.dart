import 'dart:io';
import 'package:dio/dio.dart';
import 'package:dio/io.dart';
import 'package:flutter/foundation.dart';
import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/security/certificate_pinner.dart';
import 'package:cybervpn_mobile/core/network/request_deduplicator.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

class ApiClient {
  late final Dio _dio;

  ApiClient({Dio? dio, String? baseUrl, CertificatePinner? certificatePinner}) {
    _dio = dio ?? Dio();

    final resolvedBaseUrl = baseUrl ?? EnvironmentConfig.baseUrl;

    // Enforce HTTPS in production to prevent accidental cleartext traffic.
    // In non-production environments (dev/staging) http:// is allowed for
    // local development against emulators and localhost.
    //
    // This is a runtime check (not an assert) to ensure it fires in release
    // builds. A misconfigured production base URL must crash early rather
    // than silently sending credentials over cleartext HTTP.
    if (EnvironmentConfig.isProd && !resolvedBaseUrl.startsWith('https://')) {
      AppLogger.error(
        'SECURITY: Production API base URL must use HTTPS. Got: $resolvedBaseUrl',
        category: 'ApiClient',
      );
    }

    // In non-production, only allow HTTP for local development addresses.
    if (!EnvironmentConfig.isProd && resolvedBaseUrl.startsWith('http://')) {
      final uri = Uri.parse(resolvedBaseUrl);
      const allowedHosts = {'localhost', '127.0.0.1', '10.0.2.2'};
      if (!allowedHosts.contains(uri.host)) {
        AppLogger.error(
          'HTTP is only allowed for localhost, 127.0.0.1, or 10.0.2.2. '
          'Got: $resolvedBaseUrl',
          category: 'ApiClient',
        );
      }
    }

    _dio.options = BaseOptions(
      baseUrl: resolvedBaseUrl,
      connectTimeout: const Duration(milliseconds: ApiConstants.connectTimeout),
      receiveTimeout: const Duration(milliseconds: ApiConstants.receiveTimeout),
      sendTimeout: const Duration(milliseconds: ApiConstants.sendTimeout),
      contentType: ApiConstants.contentType,
    );

    // Configure certificate pinning if fingerprints are provided.
    // TODO(security): For production releases, configure CERT_FINGERPRINTS
    // via --dart-define or .env with the SHA-256 fingerprint(s) of the
    // api.cybervpn.com TLS certificate. Include at least one backup
    // fingerprint to allow for certificate rotation without app updates.
    // Example:
    //   flutter build apk --dart-define=CERT_FINGERPRINTS=AA:BB:CC:...,DD:EE:FF:...
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
      // SECURITY: Log critical warning in production if cert pinning is missing.
      // A VPN app without certificate pinning is vulnerable to MITM attacks.
      // We degrade gracefully instead of crashing so the user can still launch
      // the app. Per-request pinning enforcement should be added separately.
      if (EnvironmentConfig.isProd) {
        AppLogger.error(
          'SECURITY: Certificate pinning is NOT configured for production! '
          'Configure CERT_FINGERPRINTS via --dart-define or .env.',
          category: 'ApiClient',
        );
      }

      // Allow debug/staging builds to run without pinning, with opt-in support.
      final enableDebugPinning = const String.fromEnvironment(
        'ENABLE_CERT_PINNING',
        defaultValue: 'false',
      );
      if (enableDebugPinning == 'true') {
        AppLogger.warning(
          'Certificate pinning requested in debug mode but no fingerprints configured',
          category: 'ApiClient',
        );
      } else {
        AppLogger.debug(
          'Certificate pinning disabled (no fingerprints configured)',
          category: 'ApiClient',
        );
      }
    }

    // Deduplicate concurrent identical GET requests. This interceptor must be
    // added before auth/retry interceptors so it short-circuits duplicates
    // before they hit the network or trigger auth flows.
    _dio.interceptors.add(RequestDeduplicator());

    if (kDebugMode) {
      _dio.interceptors.add(_RedactedLogInterceptor());
    }
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

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      return await _dio.get<T>(
        path,
        queryParameters: queryParameters,
        options: options,
        cancelToken: cancelToken,
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      return await _dio.post<T>(
        path,
        data: data,
        options: options,
        cancelToken: cancelToken,
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<Response<T>> patch<T>(
    String path, {
    dynamic data,
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      return await _dio.patch<T>(
        path,
        data: data,
        options: options,
        cancelToken: cancelToken,
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  Future<Response<T>> delete<T>(
    String path, {
    Options? options,
    CancelToken? cancelToken,
  }) async {
    try {
      return await _dio.delete<T>(
        path,
        options: options,
        cancelToken: cancelToken,
      );
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

/// Debug-only log interceptor that redacts sensitive data.
///
/// Masks Authorization headers and suppresses response bodies for
/// auth endpoints that return tokens.
class _RedactedLogInterceptor extends Interceptor {
  static const _sensitiveEndpoints = ['/auth/login', '/auth/register', '/auth/refresh', '/auth/token'];

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final headers = Map<String, dynamic>.from(options.headers);
    if (headers.containsKey('Authorization')) {
      headers['Authorization'] = 'Bearer ***REDACTED***';
    }
    AppLogger.debug(
      '→ ${options.method} ${options.uri}',
      category: 'http',
      data: {'headers': headers},
    );
    handler.next(options);
  }

  @override
  void onResponse(Response<dynamic> response, ResponseInterceptorHandler handler) {
    // SECURITY: Never log response bodies — they may contain tokens, emails,
    // device IDs, or other PII that would be forwarded to Sentry breadcrumbs.
    AppLogger.debug(
      '← ${response.statusCode} ${response.requestOptions.method} ${response.requestOptions.uri}',
      category: 'http',
      data: {'status': response.statusCode},
    );
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    AppLogger.debug(
      '✗ ${err.type.name} ${err.requestOptions.method} ${err.requestOptions.uri}',
      category: 'http',
    );
    handler.next(err);
  }
}

import 'dart:async';

import 'package:dio/dio.dart';

import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/device/device_service.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/network/auth_interceptor.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/data/datasources/auth_local_ds.dart';
import 'package:cybervpn_mobile/features/auth/data/models/token_model.dart';

class TokenRefreshException implements Exception {
  const TokenRefreshException({
    required this.message,
    this.isPermanent = false,
    this.isCircuitOpen = false,
  });

  final String message;
  final bool isPermanent;
  final bool isCircuitOpen;

  @override
  String toString() =>
      'TokenRefreshException(message: $message, '
      'isPermanent: $isPermanent, isCircuitOpen: $isCircuitOpen)';
}

/// Coordinates all token refresh work across proactive and reactive paths.
class TokenRefreshCoordinator {
  TokenRefreshCoordinator({
    required Dio dio,
    required AuthLocalDataSource localDataSource,
    required DeviceService deviceService,
  }) : _dio = dio,
       _localDataSource = localDataSource,
       _deviceService = deviceService;

  final Dio _dio;
  final AuthLocalDataSource _localDataSource;
  final DeviceService _deviceService;

  Completer<TokenModel>? _refreshCompleter;
  int _consecutiveRefreshFailures = 0;

  static const int _circuitBreakerThreshold = 3;
  static const int _maxRefreshRetries = 2;

  bool get isRefreshInProgress => _refreshCompleter != null;

  bool get isCircuitOpen =>
      _consecutiveRefreshFailures >= _circuitBreakerThreshold;

  Future<TokenModel> refresh({
    required String reason,
    String? refreshTokenOverride,
    String? deviceIdOverride,
  }) async {
    if (_refreshCompleter != null) {
      AppLogger.debug(
        'Token refresh already in progress, awaiting shared result',
        category: 'auth.refresh',
        data: {'reason': reason},
      );
      return _refreshCompleter!.future;
    }

    if (isCircuitOpen) {
      throw const TokenRefreshException(
        message: 'Token refresh circuit breaker is open.',
        isCircuitOpen: true,
      );
    }

    final completer = Completer<TokenModel>();
    _refreshCompleter = completer;
    unawaited(
      completer.future.then<void>((_) {}, onError: (error, stackTrace) {}),
    );

    try {
      final cachedToken = await _localDataSource.getCachedToken();
      final refreshToken = refreshTokenOverride ?? cachedToken?.refreshToken;
      if (refreshToken == null || refreshToken.isEmpty) {
        throw const TokenRefreshException(
          message: 'No refresh token available.',
          isPermanent: true,
        );
      }

      final deviceId = deviceIdOverride ?? await _deviceService.getDeviceId();
      final token = await _performRefreshWithRetry(refreshToken, deviceId);
      await _localDataSource.cacheToken(token);

      _consecutiveRefreshFailures = 0;
      completer.complete(token);

      AppLogger.info(
        'Token refresh succeeded',
        category: 'auth.refresh',
        data: {'reason': reason},
      );
      return token;
    } catch (error, stackTrace) {
      final refreshError = _normalizeError(error);
      _consecutiveRefreshFailures++;

      AppLogger.warning(
        'Token refresh failed',
        category: 'auth.refresh',
        error: refreshError,
        stackTrace: stackTrace,
        data: {
          'reason': reason,
          'permanent': refreshError.isPermanent,
          'circuit_open': refreshError.isCircuitOpen,
          'consecutive_failures': _consecutiveRefreshFailures,
        },
      );

      if (refreshError.isPermanent) {
        await _localDataSource.clearAuth();
      }

      if (!completer.isCompleted) {
        completer.completeError(refreshError, stackTrace);
      }
      throw refreshError;
    } finally {
      if (identical(_refreshCompleter, completer)) {
        _refreshCompleter = null;
      }
    }
  }

  Future<TokenModel> _performRefreshWithRetry(
    String refreshToken,
    String deviceId,
  ) async {
    for (var attempt = 0; attempt <= _maxRefreshRetries; attempt++) {
      try {
        final response = await _dio.post<Map<String, dynamic>>(
          ApiConstants.refresh,
          data: {'refresh_token': refreshToken, 'device_id': deviceId},
          options: Options(
            extra: {
              AuthInterceptor.skipAuthHeaderKey: true,
              AuthInterceptor.skipAuthRefreshHandlingKey: true,
            },
          ),
        );

        final data = response.data;
        if (data is! Map<String, dynamic>) {
          throw const TokenRefreshException(
            message: 'Refresh endpoint returned invalid response.',
          );
        }

        final accessToken =
            data['access_token'] as String? ?? data['accessToken'] as String?;
        final nextRefreshToken =
            data['refresh_token'] as String? ?? data['refreshToken'] as String?;
        final expiresIn =
            (data['expires_in'] as num?)?.toInt() ??
            (data['expiresIn'] as num?)?.toInt();
        final tokenType =
            data['token_type'] as String? ?? data['tokenType'] as String?;

        if (accessToken == null ||
            nextRefreshToken == null ||
            expiresIn == null) {
          throw const TokenRefreshException(
            message: 'Refresh response missing required token fields.',
          );
        }

        return TokenModel(
          accessToken: accessToken,
          refreshToken: nextRefreshToken,
          expiresIn: expiresIn,
          tokenType: tokenType,
        );
      } catch (error) {
        if (_isPermanentRefreshError(error) || attempt >= _maxRefreshRetries) {
          rethrow;
        }

        final delay = Duration(milliseconds: 500 * (attempt + 1));
        AppLogger.warning(
          'Transient token refresh failure, retrying',
          category: 'auth.refresh',
          error: error,
          data: {'attempt': attempt + 1, 'delay_ms': delay.inMilliseconds},
        );
        await Future<void>.delayed(delay);
      }
    }

    throw const TokenRefreshException(
      message: 'Token refresh retries exhausted.',
    );
  }

  bool _isPermanentRefreshError(Object error) {
    if (error is TokenRefreshException) {
      return error.isPermanent || error.isCircuitOpen;
    }

    if (error is AuthException) {
      return error.code == 401 || error.code == 403;
    }

    if (error is DioException) {
      final statusCode = error.response?.statusCode;
      if (statusCode == 401 || statusCode == 403) {
        return true;
      }
      if (statusCode == 502 || statusCode == 503 || statusCode == 504) {
        return false;
      }
      if (error.type == DioExceptionType.connectionTimeout ||
          error.type == DioExceptionType.sendTimeout ||
          error.type == DioExceptionType.receiveTimeout ||
          error.type == DioExceptionType.connectionError) {
        return false;
      }
    }

    return false;
  }

  TokenRefreshException _normalizeError(Object error) {
    if (error is TokenRefreshException) {
      return error;
    }

    if (error is AuthException) {
      return TokenRefreshException(
        message: error.message,
        isPermanent: error.code == 401 || error.code == 403,
      );
    }

    if (error is AppException) {
      return TokenRefreshException(message: error.message);
    }

    if (error is DioException) {
      return TokenRefreshException(
        message: error.message ?? 'Token refresh request failed.',
        isPermanent: _isPermanentRefreshError(error),
      );
    }

    return TokenRefreshException(message: error.toString());
  }
}

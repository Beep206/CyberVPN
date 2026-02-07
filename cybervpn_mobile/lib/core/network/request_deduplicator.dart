import 'dart:async';

import 'package:dio/dio.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Generates a unique cache key from a GET request's path and query parameters.
///
/// The key is a deterministic string built from the method, URI, and sorted
/// query parameters so that identical requests always produce the same key
/// regardless of parameter insertion order.
String _buildCacheKey(RequestOptions options) {
  final buffer = StringBuffer()
    ..write(options.method)
    ..write(':')
    ..write(options.path);

  if (options.queryParameters.isNotEmpty) {
    final sortedKeys = options.queryParameters.keys.toList()..sort();
    buffer.write('?');
    for (var i = 0; i < sortedKeys.length; i++) {
      if (i > 0) buffer.write('&');
      buffer
        ..write(Uri.encodeQueryComponent(sortedKeys[i]))
        ..write('=')
        ..write(
          Uri.encodeQueryComponent(
            options.queryParameters[sortedKeys[i]].toString(),
          ),
        );
    }
  }

  return buffer.toString();
}

/// Dio interceptor that deduplicates concurrent GET requests.
///
/// When multiple identical GET requests are made at the same time, only the
/// first request is actually sent over the network. Subsequent identical
/// requests receive the same [Response] once it arrives.
///
/// **Only GET requests** are deduplicated. POST, PATCH, PUT, and DELETE
/// requests are always passed through without deduplication because they
/// are not idempotent and must always reach the server.
///
/// The in-flight cache is automatically cleared after each response (success
/// or error), so the deduplication window is strictly limited to the duration
/// of a single network round-trip.
///
/// Usage:
/// ```dart
/// final dio = Dio();
/// dio.interceptors.add(RequestDeduplicator());
/// ```
class RequestDeduplicator extends Interceptor {
  /// Map of in-flight GET requests keyed by their cache key.
  ///
  /// Each entry holds a [Completer] that resolves with the [Response] once the
  /// first request completes. Subsequent identical requests await this
  /// completer instead of making a new network call.
  final Map<String, Completer<Response<dynamic>>> _inFlight = {};

  /// Returns the number of currently in-flight deduplicated requests.
  ///
  /// Exposed for testing and diagnostics.
  int get pendingCount => _inFlight.length;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    // Only deduplicate GET requests. Mutating methods must always go through.
    if (options.method.toUpperCase() != 'GET') {
      handler.next(options);
      return;
    }

    // Allow individual requests to opt out of deduplication by setting
    // the `_skipDedup` extra flag (useful for forced refreshes).
    if (options.extra['_skipDedup'] == true) {
      handler.next(options);
      return;
    }

    final key = _buildCacheKey(options);

    // If an identical request is already in flight, wait for it and resolve
    // with its response instead of making a duplicate network call.
    if (_inFlight.containsKey(key)) {
      AppLogger.debug(
        'Deduplicating GET request: ${options.path}',
        category: 'network.dedup',
        data: {'key': key},
      );

      try {
        final response = await _inFlight[key]!.future;
        handler.resolve(response);
      } catch (e) {
        // The original request failed -- propagate the error to all waiters.
        if (e is DioException) {
          handler.reject(e);
        } else {
          handler.reject(
            DioException(
              requestOptions: options,
              error: e,
              type: DioExceptionType.unknown,
            ),
          );
        }
      }
      return;
    }

    // First request for this key -- register a completer and proceed.
    _inFlight[key] = Completer<Response<dynamic>>();
    handler.next(options);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    _completeInflight(response.requestOptions, response: response);
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    _completeInflight(err.requestOptions, error: err);
    handler.next(err);
  }

  /// Completes and removes the in-flight completer for the given request.
  ///
  /// Called on both success and error paths to ensure the cache entry is
  /// always cleaned up and waiting futures are resolved.
  void _completeInflight(
    RequestOptions options, {
    Response<dynamic>? response,
    DioException? error,
  }) {
    if (options.method.toUpperCase() != 'GET') return;

    final key = _buildCacheKey(options);
    final completer = _inFlight.remove(key);
    if (completer == null || completer.isCompleted) return;

    if (response != null) {
      completer.complete(response);
    } else if (error != null) {
      completer.completeError(error);
    }
  }
}

import 'dart:async' show unawaited;

import 'package:dio/dio.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

/// Sentry HTTP interceptor for Dio that creates performance spans for HTTP requests.
///
/// Automatically creates Sentry transactions and spans for all HTTP requests,
/// allowing performance monitoring of API calls in Sentry dashboard.
///
/// Each HTTP request creates a span with:
/// - Operation: `http.client`
/// - Description: `{METHOD} {URL}`
/// - Tags: method, status_code, host
/// - Data: request/response headers (sanitized)
class SentryHttpInterceptor extends Interceptor {
  /// Regex patterns for PII that should never appear in Sentry spans.
  static final _jwtPattern = RegExp(
    r'eyJ[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9_-]{10,}',
  );
  static final _emailPattern = RegExp(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}',
  );
  static final _uuidPattern = RegExp(
    r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
  );

  /// Replaces PII patterns in a string with redaction markers.
  static String _redactPii(String input) {
    return input
        .replaceAll(_jwtPattern, '***JWT_REDACTED***')
        .replaceAll(_emailPattern, '***EMAIL_REDACTED***')
        .replaceAll(_uuidPattern, '***UUID_REDACTED***');
  }

  /// Sanitizes headers to remove sensitive values.
  static Map<String, dynamic> _sanitizeHeaders(Map<String, dynamic> headers) {
    final sanitized = <String, dynamic>{};
    for (final entry in headers.entries) {
      if (entry.key.toLowerCase() == 'authorization') {
        sanitized[entry.key] = '***REDACTED***';
      } else {
        final value = entry.value;
        if (value is String) {
          sanitized[entry.key] = _redactPii(value);
        } else {
          sanitized[entry.key] = value;
        }
      }
    }
    return sanitized;
  }

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    // Create a new Sentry span for this HTTP request.
    final transaction = Sentry.getSpan();
    if (transaction != null) {
      final span = transaction.startChild(
        'http.client',
        description: '${options.method} ${options.uri}',
      );

      // Store span in request options for access in onResponse/onError.
      options.extra['sentry_span'] = span;

      // Add request metadata to span.
      span.setTag('http.method', options.method);
      span.setTag('http.url', options.uri.toString());
      span.setTag('http.host', options.uri.host);

      // SECURITY: Sanitize headers before adding to span data.
      final sanitizedHeaders = _sanitizeHeaders(
        Map<String, dynamic>.from(options.headers),
      );
      span.setData('http.request.headers', sanitizedHeaders);
    }

    handler.next(options);
  }

  @override
  void onResponse(Response<dynamic> response, ResponseInterceptorHandler handler) {
    final span = response.requestOptions.extra['sentry_span'] as ISentrySpan?;
    if (span != null) {
      // Add response metadata to span.
      span.setTag('http.status_code', response.statusCode.toString());
      span.status = _getSpanStatusFromHttpCode(response.statusCode ?? 0);

      // SECURITY: Do NOT log response bodies — they may contain tokens or PII.
      // Only log response status and sanitized headers.
      final sanitizedHeaders = _sanitizeHeaders(
        Map<String, dynamic>.from(response.headers.map),
      );
      span.setData('http.response.headers', sanitizedHeaders);

      // Finish the span successfully.
      unawaited(span.finish(status: span.status));
    }

    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final span = err.requestOptions.extra['sentry_span'] as ISentrySpan?;
    if (span != null) {
      // Add error metadata to span.
      final statusCode = err.response?.statusCode;
      if (statusCode != null) {
        span.setTag('http.status_code', statusCode.toString());
        span.status = _getSpanStatusFromHttpCode(statusCode);
      } else {
        span.status = const SpanStatus.internalError();
      }

      // Add error type to span data.
      span.setData('http.error.type', err.type.name);
      span.setData('http.error.message', _redactPii(err.message ?? 'Unknown error'));

      // Finish the span with error status.
      unawaited(span.finish(status: span.status));
    }

    handler.next(err);
  }

  /// Maps HTTP status codes to Sentry span statuses.
  ///
  /// Based on Sentry's HTTP status code mapping:
  /// https://develop.sentry.dev/sdk/event-payloads/span/
  static SpanStatus _getSpanStatusFromHttpCode(int statusCode) {
    if (statusCode >= 200 && statusCode < 300) {
      return const SpanStatus.ok();
    } else if (statusCode == 400) {
      return const SpanStatus.invalidArgument();
    } else if (statusCode == 401) {
      return const SpanStatus.unauthenticated();
    } else if (statusCode == 403) {
      return const SpanStatus.permissionDenied();
    } else if (statusCode == 404) {
      return const SpanStatus.notFound();
    } else if (statusCode == 409) {
      return const SpanStatus.aborted();
    } else if (statusCode == 429) {
      return const SpanStatus.resourceExhausted();
    } else if (statusCode >= 400 && statusCode < 500) {
      return const SpanStatus.failedPrecondition();
    } else if (statusCode == 500) {
      return const SpanStatus.internalError();
    } else if (statusCode == 501) {
      return const SpanStatus.unimplemented();
    } else if (statusCode == 503) {
      return const SpanStatus.unavailable();
    } else if (statusCode == 504) {
      return const SpanStatus.deadlineExceeded();
    } else if (statusCode >= 500 && statusCode < 600) {
      return const SpanStatus.internalError();
    } else {
      return const SpanStatus.unknownError();
    }
  }
}

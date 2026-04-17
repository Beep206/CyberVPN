import 'dart:collection';
import 'dart:developer' as developer;
import 'dart:async';

import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';

// ---------------------------------------------------------------------------
// LogEntry — a single structured log record
// ---------------------------------------------------------------------------

/// Represents a single entry in the in-memory log ring buffer.
class LogEntry {
  /// Creates a [LogEntry].
  const LogEntry({
    required this.timestamp,
    required this.level,
    required this.message,
    this.data,
    this.category,
  });

  /// UTC timestamp of when the log was recorded.
  final DateTime timestamp;

  /// Severity level name (e.g. `debug`, `info`, `warning`, `error`).
  final String level;

  /// Human-readable log message.
  final String message;

  /// Optional structured data attached to the log entry.
  final Map<String, dynamic>? data;

  /// Optional category attached to the log entry.
  final String? category;

  /// Formats this entry as a single line for export.
  ///
  /// Format: `[2024-01-15T12:30:45.123Z] [INFO] Some message {key: value}`
  @override
  String toString() {
    final buf = StringBuffer()
      ..write('[')
      ..write(timestamp.toIso8601String())
      ..write('] [')
      ..write(level.toUpperCase())
      ..write('] ')
      ..write(message);
    if (data != null && data!.isNotEmpty) {
      buf
        ..write(' ')
        ..write(data);
    }
    if (category != null && category!.isNotEmpty) {
      buf
        ..write(' ')
        ..write('{category: ')
        ..write(category)
        ..write('}');
    }
    return buf.toString();
  }
}

/// Severity threshold used by [AppLogger].
enum AppLogSeverity { debug, info, warning, error, none }

/// Sink for hybrid persistent logging.
abstract class AppLogPersistence {
  Future<void> record(LogEntry entry, {String? category});
}

// ---------------------------------------------------------------------------
// AppLogger
// ---------------------------------------------------------------------------

/// A logging utility for the CyberVPN application with an in-memory ring
/// buffer and Sentry breadcrumb integration.
///
/// Uses `dart:developer` [log] for structured log output that integrates
/// with Dart DevTools and the Observatory debugger.
///
/// Each log call:
/// 1. Writes to `dart:developer` for IDE / DevTools output.
/// 2. Appends a [LogEntry] to a fixed-capacity ring buffer (FIFO, max 1000).
/// 3. Records a Sentry [Breadcrumb] when Sentry is enabled.
///
/// Log levels:
/// - [debug]   (level 500)  - Detailed diagnostic information
/// - [info]    (level 800)  - General operational messages
/// - [warning] (level 900)  - Potential issues that are not errors
/// - [error]   (level 1000) - Failures requiring attention
class AppLogger {
  const AppLogger._();

  static const String _name = 'CyberVPN';

  /// Maximum number of entries retained in the ring buffer.
  static const int maxBufferSize = 1000;

  /// In-memory FIFO ring buffer of recent log entries.
  /// Uses [Queue] for O(1) eviction from the front.
  static final Queue<LogEntry> _ringBuffer = Queue<LogEntry>();

  /// Whether Sentry breadcrumb recording is active.
  static bool get _sentryEnabled => EnvironmentConfig.sentryDsn.isNotEmpty;

  /// Configurable severity threshold for runtime logging.
  static AppLogSeverity _minimumLevel = AppLogSeverity.debug;

  /// Optional persistent sink used for file-backed logging.
  static AppLogPersistence? _persistence;

  /// Current effective threshold for application logging.
  static AppLogSeverity get minimumLevel => _minimumLevel;

  /// Bind or replace the persistent sink used for file-backed logging.
  static void bindPersistence(AppLogPersistence? persistence) {
    _persistence = persistence;
  }

  /// Update the minimum severity accepted by the logger.
  static void setMinimumLevel(AppLogSeverity level) {
    _minimumLevel = level;
  }

  @visibleForTesting
  static void resetConfiguration() {
    _minimumLevel = AppLogSeverity.debug;
    _persistence = null;
  }

  // ── Public log methods ──────────────────────────────────────────────

  /// Logs a debug-level message.
  ///
  /// Use for detailed diagnostic information during development.
  static void debug(
    String message, {
    String? category,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? data,
  }) {
    if (!_shouldLog(AppLogSeverity.debug)) {
      return;
    }
    final sanitizedMessage = _sanitizePii(message);
    final sanitizedData = _sanitizeData(data);
    final sanitizedError = error == null
        ? null
        : _sanitizePii(error.toString());
    developer.log(
      sanitizedMessage,
      name: _name,
      level: 500,
      error: sanitizedError,
      stackTrace: stackTrace,
    );
    final entry = _addToBuffer(
      'debug',
      sanitizedMessage,
      data: sanitizedData,
      category: category,
    );
    final persistence = _persistence;
    if (persistence != null) {
      unawaited(persistence.record(entry, category: category));
    }
    _addBreadcrumb(
      sanitizedMessage,
      SentryLevel.debug,
      category: category,
      data: sanitizedData,
    );
  }

  /// Logs an informational message.
  ///
  /// Use for general operational events such as successful connections
  /// or configuration changes.
  static void info(
    String message, {
    String? category,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? data,
  }) {
    if (!_shouldLog(AppLogSeverity.info)) {
      return;
    }
    final sanitizedMessage = _sanitizePii(message);
    final sanitizedData = _sanitizeData(data);
    final sanitizedError = error == null
        ? null
        : _sanitizePii(error.toString());
    developer.log(
      sanitizedMessage,
      name: _name,
      level: 800,
      error: sanitizedError,
      stackTrace: stackTrace,
    );
    final entry = _addToBuffer(
      'info',
      sanitizedMessage,
      data: sanitizedData,
      category: category,
    );
    final persistence = _persistence;
    if (persistence != null) {
      unawaited(persistence.record(entry, category: category));
    }
    _addBreadcrumb(
      sanitizedMessage,
      SentryLevel.info,
      category: category,
      data: sanitizedData,
    );
  }

  /// Logs a warning message.
  ///
  /// Use for recoverable issues or situations that may lead to errors,
  /// such as slow network responses or deprecated API usage.
  static void warning(
    String message, {
    String? category,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? data,
  }) {
    if (!_shouldLog(AppLogSeverity.warning)) {
      return;
    }
    final sanitizedMessage = _sanitizePii(message);
    final sanitizedData = _sanitizeData(data);
    final sanitizedError = error == null
        ? null
        : _sanitizePii(error.toString());
    developer.log(
      sanitizedMessage,
      name: _name,
      level: 900,
      error: sanitizedError,
      stackTrace: stackTrace,
    );
    final entry = _addToBuffer(
      'warning',
      sanitizedMessage,
      data: sanitizedData,
      category: category,
    );
    final persistence = _persistence;
    if (persistence != null) {
      unawaited(persistence.record(entry, category: category));
    }
    _addBreadcrumb(
      sanitizedMessage,
      SentryLevel.warning,
      category: category,
      data: sanitizedData,
    );
  }

  /// Logs an error message.
  ///
  /// Use for failures that need attention, such as failed API calls,
  /// unexpected exceptions, or VPN connection errors.
  static void error(
    String message, {
    String? category,
    Object? error,
    StackTrace? stackTrace,
    Map<String, dynamic>? data,
  }) {
    if (!_shouldLog(AppLogSeverity.error)) {
      return;
    }
    final sanitizedMessage = _sanitizePii(message);
    final sanitizedData = _sanitizeData(data);
    final sanitizedError = error == null
        ? null
        : _sanitizePii(error.toString());
    developer.log(
      sanitizedMessage,
      name: _name,
      level: 1000,
      error: sanitizedError,
      stackTrace: stackTrace,
    );
    final entry = _addToBuffer(
      'error',
      sanitizedMessage,
      data: sanitizedData,
      category: category,
    );
    final persistence = _persistence;
    if (persistence != null) {
      unawaited(persistence.record(entry, category: category));
    }
    _addBreadcrumb(
      sanitizedMessage,
      SentryLevel.error,
      category: category,
      data: sanitizedData,
    );
  }

  // ── Ring buffer access ──────────────────────────────────────────────

  /// Returns a read-only snapshot of the current ring buffer entries.
  static List<LogEntry> get entries => _ringBuffer.toList(growable: false);

  /// Returns the current number of entries in the ring buffer.
  static int get entryCount => _ringBuffer.length;

  /// Exports all buffered log entries as a single formatted [String].
  ///
  /// Each entry is rendered on its own line using [LogEntry.toString].
  /// Returns an empty string when the buffer is empty.
  /// PII patterns (JWTs, emails, UUIDs) are sanitized before export.
  static String exportLogs() {
    if (_ringBuffer.isEmpty) return '';
    return _ringBuffer.map((e) => _sanitizePii(e.toString())).join('\n');
  }

  /// Replaces PII patterns in a string with redaction markers.
  static final _jwtPattern = RegExp(
    r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
  );
  static final _emailPattern = RegExp(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
  );
  static final _bearerPattern = RegExp(r'Bearer\s+[A-Za-z0-9._\-]+');
  static final _queryTokenPattern = RegExp(
    r'([?&](?:ticket|token|access_token|refresh_token|oauth_code|oauth_state|telegram_auth_data|telegram_bot_token)=)[^&\s]+',
    caseSensitive: false,
  );
  static final _jsonTokenPattern = RegExp(
    r'("(?:access_token|refresh_token|ticket|token|oauth_code|oauth_state|telegram_auth_data|telegram_bot_token)"\s*:\s*")[^"]+(")',
    caseSensitive: false,
  );
  static final _mapTokenPattern = RegExp(
    r'((?:access_token|refresh_token|ticket|token|oauth_code|oauth_state|telegram_auth_data|telegram_bot_token):\s*)[^,}\]]+',
    caseSensitive: false,
  );

  static String _sanitizePii(String input) {
    return input
        .replaceAll(_jwtPattern, '***JWT***')
        .replaceAll(_emailPattern, '***EMAIL***')
        .replaceAll(_bearerPattern, 'Bearer ***REDACTED***')
        .replaceAllMapped(
          _queryTokenPattern,
          (match) => '${match.group(1)}***REDACTED***',
        )
        .replaceAllMapped(
          _jsonTokenPattern,
          (match) => '${match.group(1)}***REDACTED***${match.group(2)}',
        )
        .replaceAllMapped(
          _mapTokenPattern,
          (match) => '${match.group(1)}***REDACTED***',
        );
  }

  static Map<String, dynamic>? _sanitizeData(Map<String, dynamic>? data) {
    if (data == null) return null;
    return data.map<String, dynamic>((key, value) {
      return MapEntry<String, dynamic>(key, _sanitizeValue(value));
    });
  }

  static dynamic _sanitizeValue(dynamic value) {
    if (value is String) {
      return _sanitizePii(value);
    }
    if (value is Map<String, dynamic>) {
      return _sanitizeData(value);
    }
    if (value is Iterable) {
      return value.map(_sanitizeValue).toList(growable: false);
    }
    return value;
  }

  /// Removes all entries from the ring buffer.
  static void clearLogs() {
    _ringBuffer.clear();
  }

  // ── Private helpers ─────────────────────────────────────────────────

  /// Appends a [LogEntry] to the ring buffer, evicting the oldest entry
  /// when the buffer is at capacity.
  static LogEntry _addToBuffer(
    String level,
    String message, {
    Map<String, dynamic>? data,
    String? category,
  }) {
    if (_ringBuffer.length >= maxBufferSize) {
      _ringBuffer.removeFirst();
    }
    final entry = LogEntry(
      timestamp: DateTime.now().toUtc(),
      level: level,
      message: message,
      data: data,
      category: category,
    );
    _ringBuffer.add(entry);
    return entry;
  }

  static bool _shouldLog(AppLogSeverity severity) {
    if (_minimumLevel == AppLogSeverity.none) {
      return false;
    }
    return severity.index >= _minimumLevel.index;
  }

  /// Records a Sentry breadcrumb if Sentry is initialised.
  static void _addBreadcrumb(
    String message,
    SentryLevel level, {
    String? category,
    Map<String, dynamic>? data,
  }) {
    if (!_sentryEnabled) return;
    unawaited(
      Sentry.addBreadcrumb(
        Breadcrumb(
          message: message,
          level: level,
          category: category ?? _name,
          timestamp: DateTime.now().toUtc(),
          data: data,
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Riverpod provider
// ---------------------------------------------------------------------------

/// Provides read-only access to the [AppLogger] ring buffer for UI screens
/// such as the log viewer.
///
/// Usage:
/// ```dart
/// final logs = ref.watch(appLoggerProvider);
/// final formatted = AppLogger.exportLogs();
/// ```
///
/// The provider returns the singleton [AppLogger] class type so consumers
/// can call its static methods. It exists primarily as a dependency-injection
/// anchor for screens that need to declare their reliance on the logger.
final appLoggerProvider = Provider<Type>((ref) => AppLogger);

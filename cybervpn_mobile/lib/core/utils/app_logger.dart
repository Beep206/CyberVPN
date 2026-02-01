import 'dart:developer' as developer;

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
  });

  /// UTC timestamp of when the log was recorded.
  final DateTime timestamp;

  /// Severity level name (e.g. `debug`, `info`, `warning`, `error`).
  final String level;

  /// Human-readable log message.
  final String message;

  /// Optional structured data attached to the log entry.
  final Map<String, dynamic>? data;

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
    return buf.toString();
  }
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
  static final List<LogEntry> _ringBuffer = <LogEntry>[];

  /// Whether Sentry breadcrumb recording is active.
  static bool get _sentryEnabled => EnvironmentConfig.sentryDsn.isNotEmpty;

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
    developer.log(
      message,
      name: _name,
      level: 500,
      error: error,
      stackTrace: stackTrace,
    );
    _addToBuffer('debug', message, data: data);
    _addBreadcrumb(message, SentryLevel.debug, category: category, data: data);
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
    developer.log(
      message,
      name: _name,
      level: 800,
      error: error,
      stackTrace: stackTrace,
    );
    _addToBuffer('info', message, data: data);
    _addBreadcrumb(message, SentryLevel.info, category: category, data: data);
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
    developer.log(
      message,
      name: _name,
      level: 900,
      error: error,
      stackTrace: stackTrace,
    );
    _addToBuffer('warning', message, data: data);
    _addBreadcrumb(
      message,
      SentryLevel.warning,
      category: category,
      data: data,
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
    developer.log(
      message,
      name: _name,
      level: 1000,
      error: error,
      stackTrace: stackTrace,
    );
    _addToBuffer('error', message, data: data);
    _addBreadcrumb(
      message,
      SentryLevel.error,
      category: category,
      data: data,
    );
  }

  // ── Ring buffer access ──────────────────────────────────────────────

  /// Returns a read-only view of the current ring buffer entries.
  static List<LogEntry> get entries => List<LogEntry>.unmodifiable(_ringBuffer);

  /// Returns the current number of entries in the ring buffer.
  static int get entryCount => _ringBuffer.length;

  /// Exports all buffered log entries as a single formatted [String].
  ///
  /// Each entry is rendered on its own line using [LogEntry.toString].
  /// Returns an empty string when the buffer is empty.
  static String exportLogs() {
    if (_ringBuffer.isEmpty) return '';
    return _ringBuffer.map((e) => e.toString()).join('\n');
  }

  /// Removes all entries from the ring buffer.
  static void clearLogs() {
    _ringBuffer.clear();
  }

  // ── Private helpers ─────────────────────────────────────────────────

  /// Appends a [LogEntry] to the ring buffer, evicting the oldest entry
  /// when the buffer is at capacity.
  static void _addToBuffer(
    String level,
    String message, {
    Map<String, dynamic>? data,
  }) {
    if (_ringBuffer.length >= maxBufferSize) {
      _ringBuffer.removeAt(0);
    }
    _ringBuffer.add(
      LogEntry(
        timestamp: DateTime.now().toUtc(),
        level: level,
        message: message,
        data: data,
      ),
    );
  }

  /// Records a Sentry breadcrumb if Sentry is initialised.
  static void _addBreadcrumb(
    String message,
    SentryLevel level, {
    String? category,
    Map<String, dynamic>? data,
  }) {
    if (!_sentryEnabled) return;
    Sentry.addBreadcrumb(
      Breadcrumb(
        message: message,
        level: level,
        category: category ?? _name,
        timestamp: DateTime.now().toUtc(),
        data: data,
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

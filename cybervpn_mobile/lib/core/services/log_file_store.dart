import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

typedef LogSupportDirectoryLoader = Future<Directory> Function();
typedef LogClock = DateTime Function();

enum PersistentLogFileKind { access, subscription, xraySnapshot }

class PersistentLogFile {
  const PersistentLogFile({
    required this.name,
    required this.path,
    required this.kind,
    required this.sizeBytes,
    required this.modifiedAt,
  });

  final String name;
  final String path;
  final PersistentLogFileKind kind;
  final int sizeBytes;
  final DateTime modifiedAt;
}

class LogFileStore implements AppLogPersistence {
  LogFileStore({
    LogSupportDirectoryLoader? supportDirectoryLoader,
    LogClock? clock,
  }) : _supportDirectoryLoader =
           supportDirectoryLoader ?? getApplicationSupportDirectory,
       _clock = clock ?? DateTime.now;

  static const accessLogFileName = 'access_log.txt';
  static const subscriptionLogFileName = 'subscription_log.txt';
  static const _xraySnapshotPrefix = 'xray_runtime_';
  static const _xraySnapshotExtension = '.json';
  static const _logsFolderName = 'logs';
  static const _maxTextLogBytes = 256 * 1024;
  static const _maxXraySnapshotCount = 5;

  final LogSupportDirectoryLoader _supportDirectoryLoader;
  final LogClock _clock;

  Directory? _logsDirectory;
  Future<void> _writeQueue = Future<void>.value();

  Future<Directory> initialize() async {
    if (_logsDirectory != null) {
      return _logsDirectory!;
    }

    final supportDirectory = await _supportDirectoryLoader();
    final logsDirectory = Directory(
      '${supportDirectory.path}${Platform.pathSeparator}$_logsFolderName',
    );

    if (!await logsDirectory.exists()) {
      await logsDirectory.create(recursive: true);
    }

    _logsDirectory = logsDirectory;
    return logsDirectory;
  }

  Future<File> _resolveFile(String name) async {
    final directory = await initialize();
    return File('${directory.path}${Platform.pathSeparator}$name');
  }

  @override
  Future<void> record(LogEntry entry, {String? category}) {
    return _enqueue(() async {
      final accessLog = await _resolveFile(accessLogFileName);
      await accessLog.writeAsString(
        '${entry.toString()}\n',
        mode: FileMode.append,
        flush: true,
      );
      await _trimTextLog(accessLog);

      if (_isSubscriptionCategory(category)) {
        final subscriptionLog = await _resolveFile(subscriptionLogFileName);
        await subscriptionLog.writeAsString(
          '${entry.toString()}\n',
          mode: FileMode.append,
          flush: true,
        );
        await _trimTextLog(subscriptionLog);
      }
    });
  }

  Future<void> clearPersistentLogs() {
    return _enqueue(() async {
      final files = await listFiles();
      for (final file in files) {
        final ioFile = File(file.path);
        if (await ioFile.exists()) {
          await ioFile.delete();
        }
      }
    });
  }

  Future<List<PersistentLogFile>> listFiles() async {
    final directory = await initialize();
    final entities = await directory.list().where((entity) {
      return entity is File;
    }).cast<File>().toList();

    final descriptors = <PersistentLogFile>[];

    for (final file in entities) {
      final stat = await file.stat();
      descriptors.add(
        PersistentLogFile(
          name: _basename(file.path),
          path: file.path,
          kind: _kindForPath(file.path),
          sizeBytes: stat.size,
          modifiedAt: stat.modified,
        ),
      );
    }

    descriptors.sort((a, b) => b.modifiedAt.compareTo(a.modifiedAt));
    return descriptors;
  }

  Future<String> readFile(String path) async {
    final file = File(path);
    if (!await file.exists()) {
      return '';
    }
    return file.readAsString();
  }

  Future<void> writeXrayRuntimeSnapshot(
    String rawConfig, {
    String? remark,
  }) {
    return _enqueue(() async {
      final directory = await initialize();
      final timestamp = _snapshotTimestamp(_clock().toUtc());
      final remarkSuffix = _sanitizeRemark(remark);
      final fileName = remarkSuffix == null
          ? '$_xraySnapshotPrefix$timestamp$_xraySnapshotExtension'
          : '$_xraySnapshotPrefix${timestamp}_$remarkSuffix$_xraySnapshotExtension';
      final file = File(
        '${directory.path}${Platform.pathSeparator}$fileName',
      );
      final sanitized = _sanitizeXrayConfig(rawConfig);
      await file.writeAsString(sanitized, flush: true);
      await _pruneXraySnapshots(directory);
    });
  }

  Future<void> _trimTextLog(File file) async {
    final stat = await file.stat();
    if (stat.size <= _maxTextLogBytes) {
      return;
    }

    final content = await file.readAsString();
    final bytes = utf8.encode(content);
    final trimmedBytes = bytes.sublist(bytes.length - _maxTextLogBytes);
    await file.writeAsString(
      utf8.decode(trimmedBytes, allowMalformed: true),
      flush: true,
    );
  }

  Future<void> _pruneXraySnapshots(Directory directory) async {
    final snapshots = await directory
        .list()
        .where(
          (entity) =>
              entity is File &&
              _basename(entity.path).startsWith(_xraySnapshotPrefix),
        )
        .cast<File>()
        .toList();

    if (snapshots.length <= _maxXraySnapshotCount) {
      return;
    }

    snapshots.sort(
      (a, b) => a.statSync().modified.compareTo(b.statSync().modified),
    );

    final overflow = snapshots.length - _maxXraySnapshotCount;
    for (var i = 0; i < overflow; i++) {
      await snapshots[i].delete();
    }
  }

  Future<void> _enqueue(Future<void> Function() action) {
    _writeQueue = _writeQueue
        .catchError((Object _) {})
        .then((_) => action())
        .catchError((Object _) {});
    return _writeQueue;
  }

  bool _isSubscriptionCategory(String? category) {
    if (category == null || category.isEmpty) {
      return false;
    }
    return category == 'subscription' || category.startsWith('subscription.');
  }

  PersistentLogFileKind _kindForPath(String path) {
    final name = _basename(path);
    if (name == subscriptionLogFileName) {
      return PersistentLogFileKind.subscription;
    }
    if (name.startsWith(_xraySnapshotPrefix)) {
      return PersistentLogFileKind.xraySnapshot;
    }
    return PersistentLogFileKind.access;
  }

  String _basename(String path) {
    return path.split(Platform.pathSeparator).last;
  }

  String _snapshotTimestamp(DateTime value) {
    String twoDigits(int input) => input.toString().padLeft(2, '0');
    return '${value.year}'
        '${twoDigits(value.month)}'
        '${twoDigits(value.day)}'
        '_'
        '${twoDigits(value.hour)}'
        '${twoDigits(value.minute)}'
        '${twoDigits(value.second)}';
  }

  String? _sanitizeRemark(String? remark) {
    if (remark == null) {
      return null;
    }
    final normalized = remark
        .trim()
        .replaceAll(RegExp(r'[^a-zA-Z0-9_-]+'), '_')
        .replaceAll(RegExp(r'_+'), '_');
    if (normalized.isEmpty) {
      return null;
    }
    return normalized.length > 32
        ? normalized.substring(0, 32)
        : normalized;
  }

  String _sanitizeXrayConfig(String rawConfig) {
    try {
      final decoded = jsonDecode(rawConfig);
      if (decoded is Map<String, dynamic>) {
        final sanitized = _redactSensitiveMap(decoded);
        return const JsonEncoder.withIndent('  ').convert(sanitized);
      }
    } catch (_) {
      return rawConfig;
    }
    return rawConfig;
  }

  Map<String, dynamic> _redactSensitiveMap(Map<String, dynamic> source) {
    final result = <String, dynamic>{};

    for (final entry in source.entries) {
      final key = entry.key;
      final value = entry.value;
      if (_isSensitiveKey(key)) {
        result[key] = '***REDACTED***';
        continue;
      }

      if (value is Map<String, dynamic>) {
        result[key] = _redactSensitiveMap(value);
      } else if (value is Map) {
        result[key] = _redactSensitiveMap(
          value.cast<String, dynamic>(),
        );
      } else if (value is List) {
        result[key] = value.map(_redactSensitiveValue).toList(growable: false);
      } else {
        result[key] = value;
      }
    }

    return result;
  }

  dynamic _redactSensitiveValue(dynamic value) {
    if (value is Map<String, dynamic>) {
      return _redactSensitiveMap(value);
    }
    if (value is Map) {
      return _redactSensitiveMap(value.cast<String, dynamic>());
    }
    if (value is List) {
      return value.map(_redactSensitiveValue).toList(growable: false);
    }
    return value;
  }

  bool _isSensitiveKey(String key) {
    final lower = key.toLowerCase();
    return lower == 'id' ||
        lower == 'uuid' ||
        lower == 'password' ||
        lower == 'token' ||
        lower == 'access_token' ||
        lower == 'refresh_token' ||
        lower == 'secret' ||
        lower == 'secretkey' ||
        lower == 'privatekey' ||
        lower == 'peerpublickey';
  }
}

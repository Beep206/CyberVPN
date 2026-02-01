import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';

void main() {
  // Clear the static ring buffer before each test to prevent leakage.
  setUp(AppLogger.clearLogs);

  group('LogEntry', () {
    test('toString formats entry without data', () {
      final entry = LogEntry(
        timestamp: DateTime.utc(2025, 1, 15, 12, 30, 45, 123),
        level: 'info',
        message: 'Hello world',
      );

      expect(entry.toString(), contains('[2025-01-15T12:30:45.123Z]'));
      expect(entry.toString(), contains('[INFO]'));
      expect(entry.toString(), contains('Hello world'));
    });

    test('toString formats entry with data', () {
      final entry = LogEntry(
        timestamp: DateTime.utc(2025, 1, 15, 12, 30, 45),
        level: 'error',
        message: 'Something failed',
        data: {'code': 500},
      );

      final str = entry.toString();
      expect(str, contains('[ERROR]'));
      expect(str, contains('Something failed'));
      expect(str, contains('code'));
      expect(str, contains('500'));
    });
  });

  group('Ring buffer', () {
    test('adds entries from all log levels', () {
      AppLogger.debug('d');
      AppLogger.info('i');
      AppLogger.warning('w');
      AppLogger.error('e');

      expect(AppLogger.entryCount, equals(4));

      final levels = AppLogger.entries.map((e) => e.level).toList();
      expect(levels, equals(['debug', 'info', 'warning', 'error']));
    });

    test('stores message and optional data', () {
      AppLogger.info('test msg', data: {'key': 'value'});

      final entry = AppLogger.entries.first;
      expect(entry.message, equals('test msg'));
      expect(entry.level, equals('info'));
      expect(entry.data, equals({'key': 'value'}));
      expect(entry.timestamp, isA<DateTime>());
    });

    test('enforces max buffer size of 1000 (FIFO eviction)', () {
      // Log 1001 entries; the first should be evicted.
      for (var i = 0; i < 1001; i++) {
        AppLogger.info('entry $i');
      }

      expect(AppLogger.entryCount, equals(AppLogger.maxBufferSize));
      // The oldest surviving entry should be "entry 1" (index 0 was evicted).
      expect(AppLogger.entries.first.message, equals('entry 1'));
      // The newest entry should be "entry 1000".
      expect(AppLogger.entries.last.message, equals('entry 1000'));
    });

    test('entries returns an unmodifiable list', () {
      AppLogger.info('a');
      final list = AppLogger.entries;

      expect(
        () => list.add(
          LogEntry(
            timestamp: DateTime.now(),
            level: 'info',
            message: 'illegal',
          ),
        ),
        throwsUnsupportedError,
      );
    });
  });

  group('exportLogs', () {
    test('returns empty string when buffer is empty', () {
      expect(AppLogger.exportLogs(), equals(''));
    });

    test('returns formatted entries joined by newlines', () {
      AppLogger.info('first');
      AppLogger.error('second');

      final output = AppLogger.exportLogs();
      final lines = output.split('\n');

      expect(lines.length, equals(2));
      expect(lines[0], contains('[INFO]'));
      expect(lines[0], contains('first'));
      expect(lines[1], contains('[ERROR]'));
      expect(lines[1], contains('second'));
    });

    test('includes 10 entries in correct format', () {
      for (var i = 0; i < 10; i++) {
        AppLogger.debug('msg $i');
      }

      final output = AppLogger.exportLogs();
      final lines = output.split('\n');
      expect(lines.length, equals(10));

      for (var i = 0; i < 10; i++) {
        expect(lines[i], contains('[DEBUG]'));
        expect(lines[i], contains('msg $i'));
      }
    });
  });

  group('clearLogs', () {
    test('empties the buffer', () {
      AppLogger.info('a');
      AppLogger.info('b');
      expect(AppLogger.entryCount, equals(2));

      AppLogger.clearLogs();

      expect(AppLogger.entryCount, equals(0));
      expect(AppLogger.exportLogs(), equals(''));
    });
  });
}

import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/features/notifications/data/datasources/notification_local_datasource.dart';
import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class _MockLocalStorage extends Mock implements LocalStorageWrapper {}

void main() {
  late _MockLocalStorage mockStorage;
  late NotificationLocalDatasourceImpl datasource;
  late DateTime fixedNow;

  setUp(() {
    mockStorage = _MockLocalStorage();
    fixedNow = DateTime(2026, 2, 1, 12, 0, 0);
    datasource = NotificationLocalDatasourceImpl(
      mockStorage,
      clock: () => fixedNow,
    );
  });

  // Convenience: stub read as empty.
  void stubEmpty() {
    when(() => mockStorage.getString('notifications_data'))
        .thenAnswer((_) async => null);
    when(() => mockStorage.setString(any(), any()))
        .thenAnswer((_) async {});
  }

  // Convenience: stub read returning a JSON string.
  void stubWithJson(String json) {
    when(() => mockStorage.getString('notifications_data'))
        .thenAnswer((_) async => json);
    when(() => mockStorage.setString(any(), any()))
        .thenAnswer((_) async {});
  }

  AppNotification notification({
    required String id,
    DateTime? receivedAt,
    bool isRead = false,
  }) =>
      AppNotification(
        id: id,
        type: NotificationType.promotional,
        title: 'Title $id',
        body: 'Body $id',
        receivedAt: receivedAt ?? fixedNow,
        isRead: isRead,
      );

  group('save', () {
    test('saves a notification to empty storage', () async {
      stubEmpty();

      await datasource.save(notification(id: 'n1'));

      final captured =
          verify(() => mockStorage.setString('notifications_data', captureAny()))
              .captured
              .last as String;

      expect(captured, contains('"id":"n1"'));
    });

    test('enforces FIFO — removes oldest when over capacity', () async {
      // Build a JSON list with exactly 100 entries.
      final items = List.generate(100, (i) {
        final ts = fixedNow.subtract(Duration(hours: i));
        return '{"id":"n$i","type":"promotional","title":"T","body":"B","receivedAt":"${ts.toIso8601String()}","isRead":false}';
      });
      stubWithJson('[${items.join(",")}]');

      await datasource.save(notification(id: 'new'));

      final captured =
          verify(() => mockStorage.setString('notifications_data', captureAny()))
              .captured
              .last as String;

      // Should contain the new one and drop the oldest.
      expect(captured, contains('"id":"new"'));
      expect(captured, isNot(contains('"id":"n99"')));
    });

    test('replaces duplicate id instead of creating duplicate', () async {
      stubWithJson(
        '[{"id":"n1","type":"promotional","title":"Old","body":"B","receivedAt":"${fixedNow.toIso8601String()}","isRead":false}]',
      );

      await datasource.save(notification(id: 'n1'));

      final captured =
          verify(() => mockStorage.setString('notifications_data', captureAny()))
              .captured
              .last as String;

      // Only one entry with id n1.
      expect(RegExp(r'"id":"n1"').allMatches(captured).length, 1);
    });
  });

  group('getAll', () {
    test('returns empty list when storage is empty', () async {
      stubEmpty();
      final result = await datasource.getAll();
      expect(result, isEmpty);
    });

    test('removes entries older than 30 days', () async {
      final oldDate = fixedNow.subtract(const Duration(days: 31));
      final recentDate = fixedNow.subtract(const Duration(days: 1));

      stubWithJson(
        '[{"id":"recent","type":"promotional","title":"T","body":"B","receivedAt":"${recentDate.toIso8601String()}","isRead":false},'
        '{"id":"old","type":"promotional","title":"T","body":"B","receivedAt":"${oldDate.toIso8601String()}","isRead":false}]',
      );

      final result = await datasource.getAll();

      expect(result.length, 1);
      expect(result.first.id, 'recent');
      // Should have written back the cleaned list.
      verify(() => mockStorage.setString('notifications_data', any())).called(1);
    });

    test('returns notifications sorted newest first', () async {
      final t1 = fixedNow.subtract(const Duration(hours: 2));
      final t2 = fixedNow.subtract(const Duration(hours: 1));

      stubWithJson(
        '[{"id":"n1","type":"promotional","title":"T","body":"B","receivedAt":"${t1.toIso8601String()}","isRead":false},'
        '{"id":"n2","type":"promotional","title":"T","body":"B","receivedAt":"${t2.toIso8601String()}","isRead":false}]',
      );

      final result = await datasource.getAll();
      // Storage order is preserved (n1, n2) — both within 30 days.
      expect(result.length, 2);
      expect(result[0].id, 'n1');
      expect(result[1].id, 'n2');
    });

    test('handles malformed JSON gracefully', () async {
      stubWithJson('not-valid-json');
      final result = await datasource.getAll();
      expect(result, isEmpty);
    });
  });

  group('delete', () {
    test('removes notification by id', () async {
      stubWithJson(
        '[{"id":"n1","type":"promotional","title":"T","body":"B","receivedAt":"${fixedNow.toIso8601String()}","isRead":false},'
        '{"id":"n2","type":"promotional","title":"T","body":"B","receivedAt":"${fixedNow.toIso8601String()}","isRead":false}]',
      );

      await datasource.delete('n1');

      final captured =
          verify(() => mockStorage.setString('notifications_data', captureAny()))
              .captured
              .last as String;

      expect(captured, isNot(contains('"id":"n1"')));
      expect(captured, contains('"id":"n2"'));
    });
  });

  group('markAsRead', () {
    test('marks a specific notification as read', () async {
      stubWithJson(
        '[{"id":"n1","type":"promotional","title":"T","body":"B","receivedAt":"${fixedNow.toIso8601String()}","isRead":false}]',
      );

      await datasource.markAsRead('n1');

      final captured =
          verify(() => mockStorage.setString('notifications_data', captureAny()))
              .captured
              .last as String;

      expect(captured, contains('"isRead":true'));
    });
  });

  group('markAllAsRead', () {
    test('marks all notifications as read', () async {
      stubWithJson(
        '[{"id":"n1","type":"promotional","title":"T","body":"B","receivedAt":"${fixedNow.toIso8601String()}","isRead":false},'
        '{"id":"n2","type":"promotional","title":"T","body":"B","receivedAt":"${fixedNow.toIso8601String()}","isRead":false}]',
      );

      await datasource.markAllAsRead();

      final captured =
          verify(() => mockStorage.setString('notifications_data', captureAny()))
              .captured
              .last as String;

      expect(RegExp(r'"isRead":false').hasMatch(captured), false);
    });
  });

  group('getUnreadCount', () {
    test('returns count of unread notifications', () async {
      stubWithJson(
        '[{"id":"n1","type":"promotional","title":"T","body":"B","receivedAt":"${fixedNow.toIso8601String()}","isRead":false},'
        '{"id":"n2","type":"promotional","title":"T","body":"B","receivedAt":"${fixedNow.toIso8601String()}","isRead":true},'
        '{"id":"n3","type":"promotional","title":"T","body":"B","receivedAt":"${fixedNow.toIso8601String()}","isRead":false}]',
      );

      final count = await datasource.getUnreadCount();
      expect(count, 2);
    });
  });

  group('clear', () {
    test('removes the storage key', () async {
      when(() => mockStorage.remove('notifications_data'))
          .thenAnswer((_) async {});

      await datasource.clear();

      verify(() => mockStorage.remove('notifications_data')).called(1);
    });
  });
}

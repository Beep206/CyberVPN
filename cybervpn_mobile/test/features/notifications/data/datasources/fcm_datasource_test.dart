import 'package:cybervpn_mobile/features/notifications/data/datasources/fcm_datasource.dart';
import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('FcmDatasourceImpl.parseMessage', () {
    test('parses a fully populated data payload', () {
      final message = _remoteMessage(
        messageId: 'msg-1',
        data: {
          'id': 'n-100',
          'type': 'payment_confirmed',
          'title': 'Payment received',
          'body': 'Your payment was confirmed.',
          'action_route': '/payments',
        },
        sentTime: DateTime(2026, 1, 31, 10, 0),
      );

      final result = FcmDatasourceImpl.parseMessage(message);

      expect(result, isNotNull);
      expect(result!.id, 'n-100');
      expect(result.type, NotificationType.paymentConfirmed);
      expect(result.title, 'Payment received');
      expect(result.body, 'Your payment was confirmed.');
      expect(result.actionRoute, '/payments');
      expect(result.receivedAt, DateTime(2026, 1, 31, 10, 0));
      expect(result.isRead, false);
    });

    test('falls back to notification payload for title and body', () {
      final message = _remoteMessage(
        messageId: 'msg-2',
        data: {'type': 'security_alert'},
        notificationTitle: 'Alert!',
        notificationBody: 'Suspicious login detected.',
        sentTime: DateTime(2026, 1, 31),
      );

      final result = FcmDatasourceImpl.parseMessage(message);

      expect(result, isNotNull);
      expect(result!.title, 'Alert!');
      expect(result.body, 'Suspicious login detected.');
      expect(result.type, NotificationType.securityAlert);
    });

    test('returns null when title is missing', () {
      final message = _remoteMessage(
        messageId: 'msg-3',
        data: {'body': 'Only body provided'},
      );

      expect(FcmDatasourceImpl.parseMessage(message), isNull);
    });

    test('returns null when body is missing', () {
      final message = _remoteMessage(
        messageId: 'msg-4',
        data: {'title': 'Only title provided'},
      );

      expect(FcmDatasourceImpl.parseMessage(message), isNull);
    });

    test('defaults to promotional type for unknown type string', () {
      final message = _remoteMessage(
        messageId: 'msg-5',
        data: {
          'title': 'Hello',
          'body': 'World',
          'type': 'unknown_type_xyz',
        },
        sentTime: DateTime(2026, 1, 31),
      );

      final result = FcmDatasourceImpl.parseMessage(message);
      expect(result!.type, NotificationType.promotional);
    });

    test('defaults to promotional type when type is absent', () {
      final message = _remoteMessage(
        messageId: 'msg-6',
        data: {'title': 'Hi', 'body': 'Bye'},
        sentTime: DateTime(2026, 1, 31),
      );

      final result = FcmDatasourceImpl.parseMessage(message);
      expect(result!.type, NotificationType.promotional);
    });

    test('uses messageId as fallback id', () {
      final message = _remoteMessage(
        messageId: 'firebase-id-99',
        data: {'title': 'T', 'body': 'B'},
        sentTime: DateTime(2026, 1, 31),
      );

      final result = FcmDatasourceImpl.parseMessage(message);
      expect(result!.id, 'firebase-id-99');
    });

    test('parses all notification types correctly', () {
      const typeMap = {
        'subscription_expiring': NotificationType.subscriptionExpiring,
        'expired': NotificationType.expired,
        'payment_confirmed': NotificationType.paymentConfirmed,
        'referral_joined': NotificationType.referralJoined,
        'security_alert': NotificationType.securityAlert,
        'promotional': NotificationType.promotional,
        'server_maintenance': NotificationType.serverMaintenance,
        'app_update': NotificationType.appUpdate,
      };

      for (final entry in typeMap.entries) {
        final message = _remoteMessage(
          messageId: 'type-test',
          data: {'title': 'T', 'body': 'B', 'type': entry.key},
          sentTime: DateTime(2026, 1, 31),
        );
        final result = FcmDatasourceImpl.parseMessage(message);
        expect(result!.type, entry.value,
            reason: 'Expected ${entry.value} for "${entry.key}"');
      }
    });

    test('attaches data map when data payload is not empty', () {
      final message = _remoteMessage(
        messageId: 'msg-data',
        data: {
          'title': 'T',
          'body': 'B',
          'custom_key': 'custom_value',
        },
        sentTime: DateTime(2026, 1, 31),
      );

      final result = FcmDatasourceImpl.parseMessage(message);
      expect(result!.data, isNotNull);
      expect(result.data!['custom_key'], 'custom_value');
    });
  });
}

// ---------------------------------------------------------------------------
// Helper — Construct a minimal RemoteMessage for testing.
// ---------------------------------------------------------------------------

RemoteMessage _remoteMessage({
  String? messageId,
  Map<String, String> data = const {},
  String? notificationTitle,
  String? notificationBody,
  DateTime? sentTime,
}) {
  return RemoteMessage(
    messageId: messageId,
    data: data,
    notification: (notificationTitle != null || notificationBody != null)
        ? RemoteNotification(
            title: notificationTitle,
            body: notificationBody,
          )
        : null,
    sentTime: sentTime,
  );
}

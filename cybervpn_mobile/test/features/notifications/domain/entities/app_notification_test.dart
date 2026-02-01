import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('NotificationType', () {
    test('has all expected values', () {
      expect(NotificationType.values, hasLength(8));
      expect(NotificationType.values, contains(NotificationType.subscriptionExpiring));
      expect(NotificationType.values, contains(NotificationType.expired));
      expect(NotificationType.values, contains(NotificationType.paymentConfirmed));
      expect(NotificationType.values, contains(NotificationType.referralJoined));
      expect(NotificationType.values, contains(NotificationType.securityAlert));
      expect(NotificationType.values, contains(NotificationType.promotional));
      expect(NotificationType.values, contains(NotificationType.serverMaintenance));
      expect(NotificationType.values, contains(NotificationType.appUpdate));
    });
  });

  group('AppNotification', () {
    late DateTime receivedAt;

    setUp(() {
      receivedAt = DateTime(2026, 1, 31, 12, 0, 0);
    });

    test('creates notification with required fields and defaults', () {
      final notification = AppNotification(
        id: 'n1',
        type: NotificationType.paymentConfirmed,
        title: 'Payment received',
        body: 'Your payment of \$9.99 has been confirmed.',
        receivedAt: receivedAt,
      );

      expect(notification.id, 'n1');
      expect(notification.type, NotificationType.paymentConfirmed);
      expect(notification.title, 'Payment received');
      expect(notification.body, 'Your payment of \$9.99 has been confirmed.');
      expect(notification.receivedAt, receivedAt);
      expect(notification.isRead, false);
      expect(notification.actionRoute, isNull);
      expect(notification.data, isNull);
    });

    test('creates notification with all optional fields', () {
      final notification = AppNotification(
        id: 'n2',
        type: NotificationType.subscriptionExpiring,
        title: 'Subscription expiring',
        body: 'Your subscription expires in 3 days.',
        receivedAt: receivedAt,
        isRead: true,
        actionRoute: '/subscription/renew',
        data: {'daysLeft': 3, 'planId': 'pro'},
      );

      expect(notification.isRead, true);
      expect(notification.actionRoute, '/subscription/renew');
      expect(notification.data, {'daysLeft': 3, 'planId': 'pro'});
    });

    test('copyWith updates specified fields', () {
      final notification = AppNotification(
        id: 'n3',
        type: NotificationType.securityAlert,
        title: 'New login detected',
        body: 'A new device logged into your account.',
        receivedAt: receivedAt,
      );

      final updated = notification.copyWith(isRead: true);

      expect(updated.id, 'n3');
      expect(updated.type, NotificationType.securityAlert);
      expect(updated.title, 'New login detected');
      expect(updated.isRead, true);
    });

    test('equality for identical notifications', () {
      final n1 = AppNotification(
        id: 'n4',
        type: NotificationType.referralJoined,
        title: 'Referral joined',
        body: 'Your friend joined CyberVPN!',
        receivedAt: receivedAt,
      );
      final n2 = AppNotification(
        id: 'n4',
        type: NotificationType.referralJoined,
        title: 'Referral joined',
        body: 'Your friend joined CyberVPN!',
        receivedAt: receivedAt,
      );

      expect(n1, equals(n2));
      expect(n1.hashCode, equals(n2.hashCode));
    });

    test('inequality for different notifications', () {
      final n1 = AppNotification(
        id: 'n5',
        type: NotificationType.promotional,
        title: 'Sale!',
        body: '50% off all plans.',
        receivedAt: receivedAt,
      );
      final n2 = AppNotification(
        id: 'n6',
        type: NotificationType.appUpdate,
        title: 'Update available',
        body: 'Version 2.0 is out.',
        receivedAt: receivedAt,
      );

      expect(n1, isNot(equals(n2)));
    });

    test('toString returns meaningful representation', () {
      final notification = AppNotification(
        id: 'n7',
        type: NotificationType.serverMaintenance,
        title: 'Server maintenance',
        body: 'US-East server will be down for maintenance.',
        receivedAt: receivedAt,
      );

      final str = notification.toString();
      expect(str, contains('AppNotification'));
    });
  });
}

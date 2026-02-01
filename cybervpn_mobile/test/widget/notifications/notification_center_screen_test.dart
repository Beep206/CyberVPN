import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/providers/notification_provider.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/providers/notification_state.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/screens/notification_center_screen.dart';

// ---------------------------------------------------------------------------
// Test data
// ---------------------------------------------------------------------------

List<AppNotification> _buildTestNotifications() {
  return [
    AppNotification(
      id: 'notif-1',
      type: NotificationType.paymentConfirmed,
      title: 'Payment Received',
      body: 'Your payment of \$9.99 has been confirmed successfully.',
      receivedAt: DateTime.now().subtract(const Duration(minutes: 5)),
      isRead: false,
      actionRoute: '/billing',
    ),
    AppNotification(
      id: 'notif-2',
      type: NotificationType.subscriptionExpiring,
      title: 'Subscription Expiring',
      body: 'Your subscription will expire in 3 days. Renew now!',
      receivedAt: DateTime.now().subtract(const Duration(hours: 2)),
      isRead: false,
    ),
    AppNotification(
      id: 'notif-3',
      type: NotificationType.securityAlert,
      title: 'New Login Detected',
      body: 'A new login was detected from Chrome on Windows.',
      receivedAt: DateTime.now().subtract(const Duration(days: 1)),
      isRead: true,
    ),
  ];
}

// ---------------------------------------------------------------------------
// Fake notifier
// ---------------------------------------------------------------------------

/// A fake [NotificationNotifier] that uses pre-built state, tracks method calls
/// and performs no async or real IO.
class _FakeNotificationNotifier extends AsyncNotifier<NotificationState>
    implements NotificationNotifier {
  _FakeNotificationNotifier(this._initialState);

  final NotificationState _initialState;

  /// Tracks calls to [markAsRead].
  final List<String> markedAsReadIds = [];

  /// Tracks calls to [delete].
  final List<String> deletedIds = [];

  /// Tracks whether [markAllAsRead] was called.
  bool markAllAsReadCalled = false;

  @override
  Future<NotificationState> build() async => _initialState;

  @override
  Future<void> addNotification(AppNotification notification) async {}

  @override
  Future<void> markAsRead(String id) async {
    markedAsReadIds.add(id);
    final current = state.value;
    if (current == null) return;
    final updated = current.notifications.map((n) {
      if (n.id == id && !n.isRead) return n.copyWith(isRead: true);
      return n;
    }).toList();
    final wasUnread = current.notifications.any((n) => n.id == id && !n.isRead);
    state = AsyncData(current.copyWith(
      notifications: updated,
      unreadCount:
          wasUnread ? (current.unreadCount - 1).clamp(0, 999) : current.unreadCount,
    ));
  }

  @override
  Future<void> markAllAsRead() async {
    markAllAsReadCalled = true;
    final current = state.value;
    if (current == null) return;
    final updated =
        current.notifications.map((n) => n.copyWith(isRead: true)).toList();
    state = AsyncData(current.copyWith(notifications: updated, unreadCount: 0));
  }

  @override
  Future<void> delete(String id) async {
    deletedIds.add(id);
    final current = state.value;
    if (current == null) return;
    final wasUnread = current.notifications.any((n) => n.id == id && !n.isRead);
    final updated = current.notifications.where((n) => n.id != id).toList();
    state = AsyncData(current.copyWith(
      notifications: updated,
      unreadCount:
          wasUnread ? (current.unreadCount - 1).clamp(0, 999) : current.unreadCount,
    ));
  }
}

/// Loading notifier that never resolves.
class _LoadingNotifier extends AsyncNotifier<NotificationState>
    implements NotificationNotifier {
  final _completer = Completer<NotificationState>();

  @override
  Future<NotificationState> build() => _completer.future;

  @override
  Future<void> addNotification(AppNotification notification) async {}
  @override
  Future<void> markAsRead(String id) async {}
  @override
  Future<void> markAllAsRead() async {}
  @override
  Future<void> delete(String id) async {}
}

// ---------------------------------------------------------------------------
// Helper: build widget under test
// ---------------------------------------------------------------------------

Widget _buildTestWidget({
  required NotificationState state,
  _FakeNotificationNotifier? notifier,
}) {
  final fakeNotifier = notifier ?? _FakeNotificationNotifier(state);
  return ProviderScope(
    overrides: [
      notificationProvider.overrideWith(() => fakeNotifier),
    ],
    child: MaterialApp(
      home: const NotificationCenterScreen(),
      onGenerateRoute: (settings) {
        // Catch navigation pushes for testing actionRoute.
        return MaterialPageRoute(
          builder: (_) => Scaffold(
            body: Text('Navigated: ${settings.name}'),
          ),
          settings: settings,
        );
      },
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  // =========================================================================
  // Group 1: Rendering
  // =========================================================================

  group('NotificationCenterScreen - rendering', () {
    testWidgets('renders app bar with "Notifications" title', (tester) async {
      final notifications = _buildTestNotifications();
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 2,
      );

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.text('Notifications'), findsOneWidget);
    });

    testWidgets('renders notification tiles for all items', (tester) async {
      final notifications = _buildTestNotifications();
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 2,
      );

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.text('Payment Received'), findsOneWidget);
      expect(find.text('Subscription Expiring'), findsOneWidget);
      expect(find.text('New Login Detected'), findsOneWidget);
    });

    testWidgets('shows body preview for notifications', (tester) async {
      final notifications = _buildTestNotifications();
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 2,
      );

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Your payment of'),
        findsOneWidget,
      );
    });

    testWidgets('shows unread dot for unread notifications', (tester) async {
      final notifications = _buildTestNotifications();
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 2,
      );

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      // Two unread notifications should have unread dots.
      expect(find.byKey(const Key('unread_dot')), findsNWidgets(2));
    });

    testWidgets('shows relative timestamp', (tester) async {
      final notifications = [
        AppNotification(
          id: 'ts-test',
          type: NotificationType.promotional,
          title: 'Promo',
          body: 'Check this out',
          receivedAt: DateTime.now().subtract(const Duration(hours: 3)),
          isRead: true,
        ),
      ];
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 0,
      );

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.text('3h ago'), findsOneWidget);
    });

    testWidgets('shows loading indicator in loading state', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            notificationProvider.overrideWith(_LoadingNotifier.new),
          ],
          child: const MaterialApp(
            home: NotificationCenterScreen(),
          ),
        ),
      );
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    }, timeout: const Timeout(Duration(seconds: 10)));
  });

  // =========================================================================
  // Group 2: Empty state
  // =========================================================================

  group('NotificationCenterScreen - empty state', () {
    testWidgets('shows empty state when no notifications', (tester) async {
      const state = NotificationState(notifications: [], unreadCount: 0);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.text('No notifications yet'), findsOneWidget);
      expect(find.byKey(const Key('empty_state')), findsOneWidget);
      expect(find.byIcon(Icons.notifications_off_outlined), findsOneWidget);
    });

    testWidgets('hides "Mark all read" when no unread', (tester) async {
      const state = NotificationState(notifications: [], unreadCount: 0);

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.text('Mark all read'), findsNothing);
    });
  });

  // =========================================================================
  // Group 3: Mark all as read
  // =========================================================================

  group('NotificationCenterScreen - mark all as read', () {
    testWidgets('shows "Mark all read" when unread count > 0', (tester) async {
      final notifications = _buildTestNotifications();
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 2,
      );

      await tester.pumpWidget(_buildTestWidget(state: state));
      await tester.pumpAndSettle();

      expect(find.text('Mark all read'), findsOneWidget);
    });

    testWidgets('tapping "Mark all read" calls markAllAsRead',
        (tester) async {
      final notifications = _buildTestNotifications();
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 2,
      );
      final notifier = _FakeNotificationNotifier(state);

      await tester.pumpWidget(
        _buildTestWidget(state: state, notifier: notifier),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Mark all read'));
      await tester.pumpAndSettle();

      expect(notifier.markAllAsReadCalled, isTrue);
    });
  });

  // =========================================================================
  // Group 4: Tap to mark as read
  // =========================================================================

  group('NotificationCenterScreen - tap to read', () {
    testWidgets('tapping unread notification calls markAsRead', (tester) async {
      final notifications = _buildTestNotifications();
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 2,
      );
      final notifier = _FakeNotificationNotifier(state);

      await tester.pumpWidget(
        _buildTestWidget(state: state, notifier: notifier),
      );
      await tester.pumpAndSettle();

      // Tap on the first unread notification.
      await tester.tap(find.text('Payment Received'));
      await tester.pumpAndSettle();

      expect(notifier.markedAsReadIds, contains('notif-1'));
    });

    testWidgets('tapping read notification does not call markAsRead',
        (tester) async {
      final notifications = _buildTestNotifications();
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 2,
      );
      final notifier = _FakeNotificationNotifier(state);

      await tester.pumpWidget(
        _buildTestWidget(state: state, notifier: notifier),
      );
      await tester.pumpAndSettle();

      // Tap on the read notification (notif-3).
      await tester.tap(find.text('New Login Detected'));
      await tester.pumpAndSettle();

      expect(notifier.markedAsReadIds, isNot(contains('notif-3')));
    });
  });

  // =========================================================================
  // Group 5: Swipe to dismiss
  // =========================================================================

  group('NotificationCenterScreen - swipe to dismiss', () {
    testWidgets('swiping a notification calls delete', (tester) async {
      final notifications = _buildTestNotifications();
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 2,
      );
      final notifier = _FakeNotificationNotifier(state);

      await tester.pumpWidget(
        _buildTestWidget(state: state, notifier: notifier),
      );
      await tester.pumpAndSettle();

      // Swipe the first notification to the left.
      await tester.drag(
        find.text('Payment Received'),
        const Offset(-500, 0),
      );
      await tester.pumpAndSettle();

      expect(notifier.deletedIds, contains('notif-1'));
    });

    testWidgets('swiping shows SnackBar confirmation', (tester) async {
      final notifications = _buildTestNotifications();
      final state = NotificationState(
        notifications: notifications,
        unreadCount: 2,
      );
      final notifier = _FakeNotificationNotifier(state);

      await tester.pumpWidget(
        _buildTestWidget(state: state, notifier: notifier),
      );
      await tester.pumpAndSettle();

      await tester.drag(
        find.text('Payment Received'),
        const Offset(-500, 0),
      );
      await tester.pumpAndSettle();

      expect(find.text('Notification dismissed'), findsOneWidget);
    });
  });
}

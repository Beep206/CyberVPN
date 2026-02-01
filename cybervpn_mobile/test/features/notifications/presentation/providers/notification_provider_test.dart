import 'dart:async';

import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/features/notifications/data/datasources/fcm_datasource.dart';
import 'package:cybervpn_mobile/features/notifications/data/repositories/notification_repository_impl.dart';
import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:cybervpn_mobile/features/notifications/domain/repositories/notification_repository.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/providers/notification_provider.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/providers/notification_state.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mock NotificationRepository
// ---------------------------------------------------------------------------

class MockNotificationRepository implements NotificationRepository {
  List<AppNotification> _notifications = [];
  bool registerFcmTokenCalled = false;
  String? lastRegisteredToken;

  void seed(List<AppNotification> notifications) {
    _notifications = List.from(notifications);
  }

  @override
  Future<List<AppNotification>> getNotifications() async {
    return List.unmodifiable(_notifications);
  }

  @override
  Future<void> markAsRead(String id) async {
    _notifications = _notifications.map((n) {
      if (n.id == id) return n.copyWith(isRead: true);
      return n;
    }).toList();
  }

  @override
  Future<void> markAllAsRead() async {
    _notifications =
        _notifications.map((n) => n.copyWith(isRead: true)).toList();
  }

  @override
  Future<void> deleteNotification(String id) async {
    _notifications = _notifications.where((n) => n.id != id).toList();
  }

  @override
  Future<void> registerFcmToken(String token) async {
    registerFcmTokenCalled = true;
    lastRegisteredToken = token;
  }

  @override
  Future<int> getUnreadCount() async {
    return _notifications.where((n) => !n.isRead).length;
  }
}

// ---------------------------------------------------------------------------
// Mock NotificationRepositoryImpl (for incoming stream)
// ---------------------------------------------------------------------------

class MockNotificationRepositoryImpl extends MockNotificationRepository
    implements NotificationRepositoryImpl {
  final StreamController<AppNotification> _incomingController =
      StreamController<AppNotification>.broadcast();

  @override
  Stream<AppNotification> get incoming => _incomingController.stream;

  void emitIncoming(AppNotification notification) {
    _incomingController.add(notification);
  }

  @override
  Future<void> init() async {}

  @override
  void dispose() {
    _incomingController.close();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Mock FcmDatasource
// ---------------------------------------------------------------------------

class MockFcmDatasource implements FcmDatasource {
  String? tokenToReturn = 'mock-fcm-token';
  final StreamController<String> _tokenRefreshController =
      StreamController<String>.broadcast();

  @override
  Future<String?> getToken() async => tokenToReturn;

  @override
  Stream<String> get onTokenRefresh => _tokenRefreshController.stream;

  @override
  Stream<AppNotification> get onForegroundMessage => const Stream.empty();

  @override
  Stream<AppNotification> get onBackgroundTap => const Stream.empty();

  @override
  Future<void> configure() async {}

  @override
  Future<AppNotification?> getInitialNotification() async => null;

  @override
  void dispose() {
    _tokenRefreshController.close();
  }
}

// ---------------------------------------------------------------------------
// Mock WebSocketClient
// ---------------------------------------------------------------------------

class MockWebSocketClient implements WebSocketClient {
  final StreamController<NotificationReceived> _notificationController =
      StreamController<NotificationReceived>.broadcast();

  @override
  Stream<NotificationReceived> get notificationEvents =>
      _notificationController.stream;

  void emitNotification(NotificationReceived event) {
    _notificationController.add(event);
  }

  @override
  Future<void> dispose() async {
    await _notificationController.close();
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

AppNotification _makeNotification({
  required String id,
  bool isRead = false,
  NotificationType type = NotificationType.promotional,
}) {
  return AppNotification(
    id: id,
    type: type,
    title: 'Test $id',
    body: 'Body for $id',
    receivedAt: DateTime(2025, 1, 1),
    isRead: isRead,
  );
}

/// Creates a [ProviderContainer] with all mocks wired up.
ProviderContainer createContainer({
  required MockNotificationRepositoryImpl repoImpl,
  required MockFcmDatasource fcm,
  required MockWebSocketClient wsClient,
}) {
  return ProviderContainer(
    overrides: [
      notificationRepositoryProvider.overrideWithValue(repoImpl),
      notificationRepositoryImplProvider.overrideWithValue(repoImpl),
      fcmDatasourceProvider.overrideWithValue(fcm),
      webSocketClientProvider.overrideWithValue(wsClient),
    ],
  );
}

/// Waits for the [notificationProvider] to finish loading.
Future<NotificationState> waitForState(ProviderContainer container) async {
  final sub = container.listen(notificationProvider, (_, _) {});
  await container.read(notificationProvider.future);
  sub.close();
  return container.read(notificationProvider).requireValue;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('NotificationState', () {
    test('default state has empty notifications and zero unread', () {
      const state = NotificationState();
      expect(state.notifications, isEmpty);
      expect(state.unreadCount, 0);
    });

    test('copyWith replaces fields correctly', () {
      final n = _makeNotification(id: '1');
      const state = NotificationState();
      final updated = state.copyWith(notifications: [n], unreadCount: 1);
      expect(updated.notifications, hasLength(1));
      expect(updated.unreadCount, 1);
    });

    test('equality works correctly', () {
      const a = NotificationState();
      const b = NotificationState();
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  group('NotificationNotifier', () {
    late MockNotificationRepositoryImpl repoImpl;
    late MockFcmDatasource fcm;
    late MockWebSocketClient wsClient;
    late ProviderContainer container;

    setUp(() {
      repoImpl = MockNotificationRepositoryImpl();
      fcm = MockFcmDatasource();
      wsClient = MockWebSocketClient();
    });

    tearDown(() {
      container.dispose();
    });

    test('initial state loads notifications from repository', () async {
      repoImpl.seed([
        _makeNotification(id: '1'),
        _makeNotification(id: '2', isRead: true),
      ]);

      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      final state = await waitForState(container);
      expect(state.notifications, hasLength(2));
      expect(state.unreadCount, 1); // only '1' is unread
    });

    test('addNotification increments unread count', () async {
      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);

      final notifier = container.read(notificationProvider.notifier);
      await notifier.addNotification(_makeNotification(id: 'new-1'));

      final state = container.read(notificationProvider).requireValue;
      expect(state.notifications, hasLength(1));
      expect(state.unreadCount, 1);
    });

    test('addNotification does not add duplicates', () async {
      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);

      final notifier = container.read(notificationProvider.notifier);
      await notifier.addNotification(_makeNotification(id: 'dup-1'));
      await notifier.addNotification(_makeNotification(id: 'dup-1'));

      final state = container.read(notificationProvider).requireValue;
      expect(state.notifications, hasLength(1));
      expect(state.unreadCount, 1);
    });

    test('markAsRead decrements unread count', () async {
      repoImpl.seed([_makeNotification(id: '1')]);

      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);

      // Verify initially unread.
      var state = container.read(notificationProvider).requireValue;
      expect(state.unreadCount, 1);

      final notifier = container.read(notificationProvider.notifier);
      await notifier.markAsRead('1');

      state = container.read(notificationProvider).requireValue;
      expect(state.unreadCount, 0);
      expect(state.notifications.first.isRead, isTrue);
    });

    test('markAsRead on already-read notification does not change count',
        () async {
      repoImpl.seed([_makeNotification(id: '1', isRead: true)]);

      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);

      final notifier = container.read(notificationProvider.notifier);
      await notifier.markAsRead('1');

      final state = container.read(notificationProvider).requireValue;
      expect(state.unreadCount, 0);
    });

    test('markAllAsRead sets unread count to zero', () async {
      repoImpl.seed([
        _makeNotification(id: '1'),
        _makeNotification(id: '2'),
        _makeNotification(id: '3'),
      ]);

      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);

      var state = container.read(notificationProvider).requireValue;
      expect(state.unreadCount, 3);

      final notifier = container.read(notificationProvider.notifier);
      await notifier.markAllAsRead();

      state = container.read(notificationProvider).requireValue;
      expect(state.unreadCount, 0);
      expect(state.notifications.every((n) => n.isRead), isTrue);
    });

    test('delete removes notification and updates unread count', () async {
      repoImpl.seed([
        _makeNotification(id: '1'),
        _makeNotification(id: '2', isRead: true),
      ]);

      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);

      final notifier = container.read(notificationProvider.notifier);
      await notifier.delete('1');

      final state = container.read(notificationProvider).requireValue;
      expect(state.notifications, hasLength(1));
      expect(state.notifications.first.id, '2');
      expect(state.unreadCount, 0);
    });

    test('delete read notification does not change unread count', () async {
      repoImpl.seed([
        _makeNotification(id: '1'),
        _makeNotification(id: '2', isRead: true),
      ]);

      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);

      final notifier = container.read(notificationProvider.notifier);
      await notifier.delete('2');

      final state = container.read(notificationProvider).requireValue;
      expect(state.notifications, hasLength(1));
      expect(state.unreadCount, 1);
    });

    test('FCM token registration is called on init', () async {
      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);

      // Give the fire-and-forget future a tick to complete.
      await Future<void>.delayed(Duration.zero);

      expect(repoImpl.registerFcmTokenCalled, isTrue);
      expect(repoImpl.lastRegisteredToken, 'mock-fcm-token');
    });
  });

  group('Derived providers', () {
    late MockNotificationRepositoryImpl repoImpl;
    late MockFcmDatasource fcm;
    late MockWebSocketClient wsClient;
    late ProviderContainer container;

    setUp(() {
      repoImpl = MockNotificationRepositoryImpl();
      fcm = MockFcmDatasource();
      wsClient = MockWebSocketClient();
    });

    tearDown(() {
      container.dispose();
    });

    test('unreadCountProvider returns 0 initially', () async {
      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);
      final count = container.read(unreadCountProvider);
      expect(count, 0);
    });

    test('unreadCountProvider reflects correct count', () async {
      repoImpl.seed([
        _makeNotification(id: '1'),
        _makeNotification(id: '2'),
        _makeNotification(id: '3', isRead: true),
      ]);

      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);
      final count = container.read(unreadCountProvider);
      expect(count, 2);
    });

    test('notificationsListProvider returns loaded notifications', () async {
      repoImpl.seed([_makeNotification(id: '1')]);

      container = createContainer(
        repoImpl: repoImpl,
        fcm: fcm,
        wsClient: wsClient,
      );

      await waitForState(container);
      final list = container.read(notificationsListProvider);
      expect(list, hasLength(1));
      expect(list.first.id, '1');
    });
  });
}

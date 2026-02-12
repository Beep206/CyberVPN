import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/network/websocket_client.dart';
import 'package:cybervpn_mobile/core/network/websocket_provider.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

import 'package:cybervpn_mobile/features/notifications/data/repositories/notification_repository_impl.dart';
import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:cybervpn_mobile/features/notifications/domain/repositories/notification_repository.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/providers/notification_state.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show
        fcmDatasourceProvider,
        notificationRepositoryImplProvider,
        notificationRepositoryProvider;

// ---------------------------------------------------------------------------
// Notification notifier
// ---------------------------------------------------------------------------

/// Manages notification state for the entire app.
///
/// On [build] it loads stored notifications from local storage and
/// registers the FCM device token with the backend. Subsequent
/// mutations (add, markAsRead, markAllAsRead, delete) update the
/// inner [NotificationState] synchronously.
///
/// Listens to:
/// - FCM foreground messages via [NotificationRepositoryImpl.incoming]
/// - WebSocket [NotificationReceived] events via [notificationEventsProvider]
class NotificationNotifier extends AsyncNotifier<NotificationState> {
  NotificationRepository get _repo => ref.read(notificationRepositoryProvider);

  StreamSubscription<AppNotification>? _incomingSub;
  StreamSubscription<NotificationReceived>? _webSocketSub;

  // ---- Lifecycle -----------------------------------------------------------

  @override
  FutureOr<NotificationState> build() async {
    // Load persisted notifications.
    final notifications = await _repo.getNotifications();
    final unreadCount = notifications.where((n) => !n.isRead).length;

    // Register FCM token (fire-and-forget; do not block init).
    unawaited(_registerFcmToken());

    // Set up real-time listeners.
    _listenToIncomingFcm();
    _listenToWebSocket();

    // Clean up subscriptions when provider is disposed.
    ref.onDispose(_dispose);

    return NotificationState(
      notifications: notifications,
      unreadCount: unreadCount,
    );
  }

  // ---- Public API ----------------------------------------------------------

  /// Adds a new notification to the top of the list and persists it.
  ///
  /// If the notification is unread, the unread count is incremented.
  Future<void> addNotification(AppNotification notification) async {
    final current = state.value;
    if (current == null) return;

    // Avoid duplicates.
    if (current.notifications.any((n) => n.id == notification.id)) return;

    final updated = [notification, ...current.notifications];
    final unread = current.unreadCount + (notification.isRead ? 0 : 1);

    state = AsyncValue.data(
      current.copyWith(notifications: updated, unreadCount: unread),
    );
  }

  /// Marks a single notification as read by [id].
  ///
  /// Decrements the unread count when the notification was previously unread.
  Future<void> markAsRead(String id) async {
    final current = state.value;
    if (current == null) return;

    await _repo.markAsRead(id);

    final updated = current.notifications.map((n) {
      if (n.id == id && !n.isRead) {
        return n.copyWith(isRead: true);
      }
      return n;
    }).toList();

    final wasUnread = current.notifications.any((n) => n.id == id && !n.isRead);
    final unread = wasUnread ? current.unreadCount - 1 : current.unreadCount;

    state = AsyncValue.data(
      current.copyWith(
        notifications: updated,
        unreadCount: unread < 0 ? 0 : unread,
      ),
    );
  }

  /// Marks all notifications as read and resets the unread count.
  Future<void> markAllAsRead() async {
    final current = state.value;
    if (current == null) return;

    await _repo.markAllAsRead();

    final updated = current.notifications
        .map((n) => n.copyWith(isRead: true))
        .toList();

    state = AsyncValue.data(
      current.copyWith(notifications: updated, unreadCount: 0),
    );
  }

  /// Deletes a notification by [id].
  ///
  /// Decrements the unread count when the deleted notification was unread.
  Future<void> delete(String id) async {
    final current = state.value;
    if (current == null) return;

    await _repo.deleteNotification(id);

    final wasUnread = current.notifications.any((n) => n.id == id && !n.isRead);
    final updated = current.notifications.where((n) => n.id != id).toList();
    final unread = wasUnread ? current.unreadCount - 1 : current.unreadCount;

    state = AsyncValue.data(
      current.copyWith(
        notifications: updated,
        unreadCount: unread < 0 ? 0 : unread,
      ),
    );
  }

  // ---- Private helpers -----------------------------------------------------

  /// Registers the FCM device token with the backend.
  Future<void> _registerFcmToken() async {
    if (kDebugMode && EnvironmentConfig.isDev) {
      return;
    }

    try {
      final fcm = ref.read(fcmDatasourceProvider);
      final token = await fcm.getToken();
      if (token != null && token.isNotEmpty) {
        await _repo.registerFcmToken(token);
        AppLogger.info('FCM token registered with backend');
      }

      // Also listen for token refreshes.
      fcm.onTokenRefresh.listen((newToken) async {
        try {
          await _repo.registerFcmToken(newToken);
          AppLogger.info('Refreshed FCM token registered with backend');
        } catch (e) {
          AppLogger.error('Failed to register refreshed FCM token', error: e);
        }
      });
    } catch (e) {
      AppLogger.error('Failed to register FCM token', error: e);
    }
  }

  /// Subscribes to FCM foreground messages via the repository's
  /// [NotificationRepositoryImpl.incoming] stream.
  void _listenToIncomingFcm() {
    try {
      final repoImpl = ref.read(notificationRepositoryImplProvider);
      _incomingSub = repoImpl.incoming.listen(
        addNotification,
        onError: (Object e) {
          AppLogger.error('FCM incoming stream error', error: e);
        },
      );
    } catch (e) {
      AppLogger.error('Failed to listen to FCM incoming stream', error: e);
    }
  }

  /// Subscribes to WebSocket [NotificationReceived] events and converts
  /// them to [AppNotification] instances.
  void _listenToWebSocket() {
    try {
      final client = ref.read(webSocketClientProvider);
      _webSocketSub = client.notificationEvents.listen(
        (event) {
          final notification = AppNotification(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            type: _parseNotificationType(event.data['type'] as String?),
            title: event.title,
            body: event.body,
            receivedAt: DateTime.now(),
            actionRoute: event.data['action_route'] as String?,
            data: event.data.isNotEmpty ? event.data : null,
          );
          unawaited(addNotification(notification));
        },
        onError: (Object e) {
          AppLogger.error('WebSocket notification stream error', error: e);
        },
      );
    } catch (e) {
      AppLogger.error(
        'Failed to listen to WebSocket notification stream',
        error: e,
      );
    }
  }

  /// Parses a type string from WebSocket data into a [NotificationType].
  static NotificationType _parseNotificationType(String? value) {
    if (value == null) return NotificationType.promotional;
    for (final t in NotificationType.values) {
      if (t.name == value) return t;
    }
    return NotificationType.promotional;
  }

  void _dispose() {
    unawaited(_incomingSub?.cancel());
    unawaited(_webSocketSub?.cancel());
  }
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

/// Primary notification state provider backed by [NotificationNotifier].
final notificationProvider =
    AsyncNotifierProvider<NotificationNotifier, NotificationState>(
      NotificationNotifier.new,
    );

/// The current unread notification count (0 when state is not yet loaded).
final unreadCountProvider = Provider<int>((ref) {
  final notifState = ref.watch(notificationProvider).value;
  return notifState?.unreadCount ?? 0;
});

/// The current list of notifications (empty when state is not yet loaded).
final notificationsListProvider = Provider<List<AppNotification>>((ref) {
  final notifState = ref.watch(notificationProvider).value;
  return notifState?.notifications ?? [];
});

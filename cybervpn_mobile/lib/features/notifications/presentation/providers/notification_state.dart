import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';

// ---------------------------------------------------------------------------
// Notification state
// ---------------------------------------------------------------------------

/// Immutable snapshot of the notification state.
///
/// Held inside an [AsyncValue] by the [NotificationNotifier] so the
/// outer async wrapper covers the initial load while the inner fields
/// can be updated synchronously after mutations.
class NotificationState {
  const NotificationState({
    this.notifications = const [],
    this.unreadCount = 0,
  });

  /// All notifications, ordered newest first.
  final List<AppNotification> notifications;

  /// Number of unread notifications.
  final int unreadCount;

  // ---- Copy-with ----------------------------------------------------------

  NotificationState copyWith({
    List<AppNotification>? notifications,
    int? unreadCount,
  }) {
    return NotificationState(
      notifications: notifications ?? this.notifications,
      unreadCount: unreadCount ?? this.unreadCount,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is NotificationState &&
          runtimeType == other.runtimeType &&
          notifications == other.notifications &&
          unreadCount == other.unreadCount;

  @override
  int get hashCode => Object.hash(notifications, unreadCount);

  @override
  String toString() =>
      'NotificationState(count: ${notifications.length}, unread: $unreadCount)';
}

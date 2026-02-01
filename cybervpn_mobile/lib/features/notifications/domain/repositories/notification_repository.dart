import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';

/// Abstract repository for managing in-app notifications.
///
/// Implementations handle local persistence, remote synchronization,
/// and FCM token registration with the backend.
abstract class NotificationRepository {
  /// Retrieves all stored notifications, ordered by [AppNotification.receivedAt]
  /// descending (newest first).
  Future<List<AppNotification>> getNotifications();

  /// Marks a single notification as read by its [id].
  Future<void> markAsRead(String id);

  /// Marks every stored notification as read.
  Future<void> markAllAsRead();

  /// Permanently deletes the notification identified by [id].
  Future<void> deleteNotification(String id);

  /// Registers the device FCM [token] with the backend so push
  /// notifications can be delivered.
  Future<void> registerFcmToken(String token);

  /// Returns the count of notifications where [AppNotification.isRead] is false.
  Future<int> getUnreadCount();
}

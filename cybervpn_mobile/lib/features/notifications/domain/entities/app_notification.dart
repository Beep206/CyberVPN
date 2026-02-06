import 'package:freezed_annotation/freezed_annotation.dart';

part 'app_notification.freezed.dart';

/// Type of notification received by the application.
enum NotificationType {
  subscriptionExpiring,
  expired,
  paymentConfirmed,
  referralJoined,
  securityAlert,
  promotional,
  serverMaintenance,
  appUpdate,
}

/// An in-app notification displayed to the user.
///
/// Contains the notification content, type, read status, and optional
/// deep-link route and arbitrary metadata payload.
@freezed
sealed class AppNotification with _$AppNotification {
  const factory AppNotification({
    required String id,
    required NotificationType type,
    required String title,
    required String body,
    required DateTime receivedAt,
    @Default(false) bool isRead,
    String? actionRoute,
    Map<String, dynamic>? data,
  }) = _AppNotification;
}

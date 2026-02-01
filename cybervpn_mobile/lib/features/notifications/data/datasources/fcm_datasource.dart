import 'dart:async';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';

/// Datasource that handles Firebase Cloud Messaging events across all
/// application lifecycle states: foreground, background tap, and
/// terminated tap.
abstract class FcmDatasource {
  /// Stream of [AppNotification]s received while the app is in the foreground.
  Stream<AppNotification> get onForegroundMessage;

  /// Configures FCM message handlers. Must be called once during app
  /// initialisation.
  Future<void> configure();

  /// Returns the notification that launched the app from a terminated state,
  /// if any.
  Future<AppNotification?> getInitialNotification();

  /// Returns a stream of notifications opened from the background.
  Stream<AppNotification> get onBackgroundTap;

  /// Requests the current FCM device token.
  Future<String?> getToken();

  /// Stream that emits whenever the FCM token is refreshed.
  Stream<String> get onTokenRefresh;

  /// Releases resources.
  void dispose();
}

/// Default implementation backed by [FirebaseMessaging].
class FcmDatasourceImpl implements FcmDatasource {
  final FirebaseMessaging _messaging;

  final StreamController<AppNotification> _foregroundController =
      StreamController<AppNotification>.broadcast();

  final StreamController<AppNotification> _backgroundTapController =
      StreamController<AppNotification>.broadcast();

  FcmDatasourceImpl({FirebaseMessaging? messaging})
      : _messaging = messaging ?? FirebaseMessaging.instance;

  @override
  Stream<AppNotification> get onForegroundMessage =>
      _foregroundController.stream;

  @override
  Stream<AppNotification> get onBackgroundTap =>
      _backgroundTapController.stream;

  @override
  Future<void> configure() async {
    // Foreground messages.
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      final notification = parseMessage(message);
      if (notification != null) {
        _foregroundController.add(notification);
      }
    });

    // Background tap (user taps notification while app is in background).
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      final notification = parseMessage(message);
      if (notification != null) {
        _backgroundTapController.add(notification);
      }
    });
  }

  @override
  Future<AppNotification?> getInitialNotification() async {
    final message = await _messaging.getInitialMessage();
    if (message == null) return null;
    return parseMessage(message);
  }

  @override
  Future<String?> getToken() => _messaging.getToken();

  @override
  Stream<String> get onTokenRefresh => _messaging.onTokenRefresh;

  @override
  void dispose() {
    _foregroundController.close();
    _backgroundTapController.close();
  }

  // ---------------------------------------------------------------------------
  // Parsing
  // ---------------------------------------------------------------------------

  /// Converts an FCM [RemoteMessage] into an [AppNotification].
  ///
  /// Returns `null` when the message does not contain enough data to build a
  /// valid notification.
  static AppNotification? parseMessage(RemoteMessage message) {
    try {
      final data = message.data;
      final notification = message.notification;

      // Prefer explicit data payload; fall back to notification payload.
      final title =
          data['title'] as String? ?? notification?.title;
      final body =
          data['body'] as String? ?? notification?.body;

      if (title == null || body == null) return null;

      final id =
          data['id'] as String? ?? message.messageId ?? DateTime.now().millisecondsSinceEpoch.toString();

      final typeStr = data['type'] as String?;
      final type = _parseNotificationType(typeStr);

      final actionRoute = data['action_route'] as String?;

      return AppNotification(
        id: id,
        type: type,
        title: title,
        body: body,
        receivedAt: message.sentTime ?? DateTime.now(),
        actionRoute: actionRoute,
        data: data.isNotEmpty ? Map<String, dynamic>.from(data) : null,
      );
    } catch (_) {
      return null;
    }
  }

  static NotificationType _parseNotificationType(String? value) {
    if (value == null) return NotificationType.promotional;
    switch (value) {
      case 'subscription_expiring':
        return NotificationType.subscriptionExpiring;
      case 'expired':
        return NotificationType.expired;
      case 'payment_confirmed':
        return NotificationType.paymentConfirmed;
      case 'referral_joined':
        return NotificationType.referralJoined;
      case 'security_alert':
        return NotificationType.securityAlert;
      case 'promotional':
        return NotificationType.promotional;
      case 'server_maintenance':
        return NotificationType.serverMaintenance;
      case 'app_update':
        return NotificationType.appUpdate;
      default:
        return NotificationType.promotional;
    }
  }
}

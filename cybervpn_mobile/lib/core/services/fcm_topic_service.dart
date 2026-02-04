import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';

// ---------------------------------------------------------------------------
// FCM Topic Constants
// ---------------------------------------------------------------------------

/// FCM topic names for notification categories.
///
/// These must match the topic names used by the backend when sending
/// push notifications. Keep in sync with backend configuration.
class FcmTopics {
  FcmTopics._();

  /// Notifications for VPN connection status changes.
  static const String connectionStatus = 'connection_status';

  /// Reminders for subscription expiry.
  static const String subscriptionExpiry = 'subscription_expiry';

  /// Promotional offers and discounts.
  static const String promotional = 'promotional';

  /// Referral activity updates.
  static const String referralActivity = 'referral_activity';

  /// Security alerts (always subscribed).
  static const String securityAlerts = 'security_alerts';
}

// ---------------------------------------------------------------------------
// Notification Type to FCM Topic Mapping
// ---------------------------------------------------------------------------

/// Maps [NotificationType] to FCM topic names.
///
/// Used to subscribe/unsubscribe from topics when notification preferences
/// change in the settings.
String? notificationTypeToTopic(NotificationType type) {
  return switch (type) {
    NotificationType.connection => FcmTopics.connectionStatus,
    NotificationType.expiry => FcmTopics.subscriptionExpiry,
    NotificationType.promotional => FcmTopics.promotional,
    NotificationType.referral => FcmTopics.referralActivity,
    // VPN speed notifications are local only, no FCM topic
    NotificationType.vpnSpeed => null,
  };
}

// ---------------------------------------------------------------------------
// FCM Topic Service
// ---------------------------------------------------------------------------

/// Service for managing FCM topic subscriptions based on notification preferences.
///
/// Handles:
/// - Subscribing/unsubscribing from FCM topics when preferences change
/// - Syncing all topic subscriptions on app start
/// - Always keeping security alerts enabled
///
/// Topic subscriptions allow the backend to send targeted push notifications
/// only to users who have opted in to specific notification categories.
///
/// Usage:
/// ```dart
/// final service = ref.read(fcmTopicServiceProvider);
///
/// // Subscribe to a topic when user enables a notification type
/// await service.setTopicSubscription(NotificationType.promotional, true);
///
/// // Sync all topics based on current settings
/// await service.syncAllTopicSubscriptions(ref);
/// ```
class FcmTopicService {
  FcmTopicService();

  final FirebaseMessaging _messaging = FirebaseMessaging.instance;

  /// Subscribe to an FCM topic.
  Future<void> subscribe(String topic) async {
    try {
      await _messaging.subscribeToTopic(topic);
      AppLogger.info(
        'Subscribed to FCM topic: $topic',
        category: 'fcm.topics',
      );
    } catch (e, st) {
      AppLogger.error(
        'Failed to subscribe to FCM topic: $topic',
        error: e,
        stackTrace: st,
        category: 'fcm.topics',
      );
      rethrow;
    }
  }

  /// Unsubscribe from an FCM topic.
  Future<void> unsubscribe(String topic) async {
    try {
      await _messaging.unsubscribeFromTopic(topic);
      AppLogger.info(
        'Unsubscribed from FCM topic: $topic',
        category: 'fcm.topics',
      );
    } catch (e, st) {
      AppLogger.error(
        'Failed to unsubscribe from FCM topic: $topic',
        error: e,
        stackTrace: st,
        category: 'fcm.topics',
      );
      rethrow;
    }
  }

  /// Set subscription state for a notification type.
  ///
  /// If [enabled] is true, subscribes to the topic.
  /// If [enabled] is false, unsubscribes from the topic.
  /// Returns silently if the notification type has no associated FCM topic.
  Future<void> setTopicSubscription(
    NotificationType type,
    bool enabled,
  ) async {
    final topic = notificationTypeToTopic(type);
    if (topic == null) {
      // No FCM topic for this notification type (e.g., local-only notifications)
      return;
    }

    if (enabled) {
      await subscribe(topic);
    } else {
      await unsubscribe(topic);
    }
  }

  /// Sync all FCM topic subscriptions based on current app settings.
  ///
  /// Call this on app start to ensure topic subscriptions match user preferences.
  /// This handles cases where the user changed settings while offline.
  ///
  /// Security alerts are always subscribed - cannot be disabled.
  Future<void> syncAllTopicSubscriptions(AppSettings settings) async {
    AppLogger.info(
      'Syncing FCM topic subscriptions',
      category: 'fcm.topics',
    );

    try {
      // Connection status
      await setTopicSubscription(
        NotificationType.connection,
        settings.notificationConnection,
      );

      // Subscription expiry
      await setTopicSubscription(
        NotificationType.expiry,
        settings.notificationExpiry,
      );

      // Promotional
      await setTopicSubscription(
        NotificationType.promotional,
        settings.notificationPromotional,
      );

      // Referral
      await setTopicSubscription(
        NotificationType.referral,
        settings.notificationReferral,
      );

      // Security alerts - always subscribe, cannot be disabled
      await subscribe(FcmTopics.securityAlerts);

      AppLogger.info(
        'FCM topic subscriptions synced successfully',
        category: 'fcm.topics',
      );
    } catch (e, st) {
      AppLogger.error(
        'Failed to sync FCM topic subscriptions',
        error: e,
        stackTrace: st,
        category: 'fcm.topics',
      );
    }
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

/// Provides the [FcmTopicService] singleton.
final fcmTopicServiceProvider = Provider<FcmTopicService>((ref) {
  return FcmTopicService();
});

// ---------------------------------------------------------------------------
// Topic Sync Provider
// ---------------------------------------------------------------------------

/// Provider that syncs FCM topic subscriptions when settings change.
///
/// Watch this provider in the app to keep topics in sync with preferences.
/// It listens to settings changes and updates subscriptions accordingly.
final fcmTopicSyncProvider = Provider<void>((ref) {
  final settings = ref.watch(settingsProvider).value;
  if (settings == null) return;

  final service = ref.read(fcmTopicServiceProvider);

  // Sync all subscriptions when settings change
  // Using addPostFrameCallback to avoid calling async during build
  Future.microtask(() async {
    await service.syncAllTopicSubscriptions(settings);
  });
});

// ---------------------------------------------------------------------------
// Notification Preference Change Handler
// ---------------------------------------------------------------------------

/// Handles FCM topic subscription when a notification preference is toggled.
///
/// Call this after toggling a notification preference to update the
/// FCM subscription state.
///
/// Example:
/// ```dart
/// await notifier.toggleNotification(NotificationType.promotional);
/// await handleNotificationPreferenceChange(
///   ref,
///   NotificationType.promotional,
///   settings.notificationPromotional,
/// );
/// ```
Future<void> handleNotificationPreferenceChange(
  Ref ref,
  NotificationType type,
  bool enabled,
) async {
  final service = ref.read(fcmTopicServiceProvider);
  await service.setTopicSubscription(type, enabled);
}

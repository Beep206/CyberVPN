import 'dart:async';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/core/services/fcm_token_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/quick_actions/domain/services/quick_actions_handler.dart'
    show rootNavigatorKey;

/// Top-level handler for background FCM messages.
///
/// Must be a top-level function (not a class method) so the Flutter engine
/// can invoke it in the background isolate. See:
/// https://firebase.google.com/docs/cloud-messaging/flutter/receive
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Firebase must be initialized in the background isolate as well.
  // If it was already initialized this call is effectively a no-op.
  try {
    await Firebase.initializeApp();
  } catch (_) {
    // Initialization may fail if platform config is missing.
  }

  AppLogger.info(
    'Background FCM message received: ${message.messageId}',
    category: 'fcm',
  );
}

/// Manages Firebase Cloud Messaging (FCM) setup.
///
/// Handles:
/// * Requesting notification permissions from the user.
/// * Retrieving the FCM device token (logged truncated for security).
/// * Registering foreground and background message handlers.
/// * Listening for token refresh events and re-registering with backend.
///
/// Usage: call [initialize] once during app startup **after**
/// `Firebase.initializeApp()` has completed.
class PushNotificationService {
  PushNotificationService._();

  /// Singleton instance.
  static final PushNotificationService instance = PushNotificationService._();

  /// FCM token service for registering tokens with the backend.
  /// Must be set before calling [initialize].
  FcmTokenService? _fcmTokenService;

  /// Local notifications plugin for displaying foreground notifications.
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  /// Android notification channel for VPN-related notifications.
  static const _vpnChannel = AndroidNotificationChannel(
    'cybervpn_notifications',
    'CyberVPN Notifications',
    description: 'VPN status and account notifications',
    importance: Importance.high,
  );

  /// Callback invoked when a local notification is tapped.
  ///
  /// Set this to handle deep linking from notification taps.
  void Function(String? payload)? onNotificationTap;

  /// The underlying [FirebaseMessaging] instance.
  FirebaseMessaging get _messaging => FirebaseMessaging.instance;

  /// The most recently retrieved FCM token (may be `null` if Firebase is
  /// not configured or permissions were denied).
  String? _token;

  /// Returns the current FCM device token, or `null` if unavailable.
  String? get token => _token;

  /// Subscription for the token-refresh stream.
  StreamSubscription<String>? _tokenRefreshSub;

  /// Sets the FCM token service for backend registration.
  ///
  /// Should be called before [initialize] to enable automatic token
  /// registration on refresh.
  void setFcmTokenService(FcmTokenService service) {
    _fcmTokenService = service;
  }

  /// Initializes FCM: requests permissions, retrieves the device token,
  /// and registers message handlers.
  ///
  /// Errors are caught so the app continues to function even when Firebase
  /// is not configured (e.g. missing `google-services.json`).
  Future<void> initialize() async {
    try {
      // Check whether Firebase has been initialized before attempting
      // to use Firebase Messaging.
      if (Firebase.apps.isEmpty) {
        AppLogger.info(
          'Firebase not initialized -- skipping FCM setup',
          category: 'fcm',
        );
        return;
      }

      // Initialize local notifications for foreground display.
      // Wire notification tap handler for deep linking.
      onNotificationTap = (payload) {
        if (payload != null && payload.isNotEmpty) {
          _navigateToRoute(payload);
        }
      };
      await _initLocalNotifications();

      // Register the background handler before any other messaging calls.
      FirebaseMessaging.onBackgroundMessage(
        _firebaseMessagingBackgroundHandler,
      );

      // Request notification permissions (iOS / macOS / Web).
      final settings = await _messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
        provisional: false,
      );

      AppLogger.info(
        'FCM permission status: ${settings.authorizationStatus}',
        category: 'fcm',
      );

      if (settings.authorizationStatus == AuthorizationStatus.denied) {
        AppLogger.info(
          'Notification permission denied -- FCM token not retrieved',
          category: 'fcm',
        );
        return;
      }

      // Retrieve the device token.
      _token = await _messaging.getToken();
      AppLogger.debug(
        'FCM token retrieved (${_token?.length ?? 0} chars)',
        category: 'fcm',
      );

      // Store initial token locally so it survives app restarts.
      if (_token != null && _token!.isNotEmpty) {
        unawaited(_fcmTokenService?.storePendingToken(_token!));
      }

      // Listen for token refresh events and re-register with backend.
      _tokenRefreshSub = _messaging.onTokenRefresh.listen((newToken) {
        _token = newToken;
        AppLogger.debug(
          'FCM token refreshed (${newToken.length} chars)',
          category: 'fcm',
        );

        // Store refreshed token locally before attempting registration.
        unawaited(_fcmTokenService?.storePendingToken(newToken));

        // Re-register the new token with the backend
        _handleTokenRefresh(newToken);
      });

      // Handle foreground messages.
      FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

      // Handle taps on notifications that opened the app from background.
      FirebaseMessaging.onMessageOpenedApp.listen(_handleMessageOpenedApp);

      // Check if the app was launched from a terminated state via a
      // notification tap.
      final initialMessage = await _messaging.getInitialMessage();
      if (initialMessage != null) {
        _handleMessageOpenedApp(initialMessage);
      }
    } catch (e, st) {
      AppLogger.warning(
        'FCM initialization failed -- push notifications will be unavailable',
        error: e,
        stackTrace: st,
        category: 'fcm',
      );
    }
  }

  /// Handles a message received while the app is in the foreground.
  void _handleForegroundMessage(RemoteMessage message) {
    AppLogger.info(
      'Foreground FCM message: ${message.messageId} '
      'title=${message.notification?.title}',
      category: 'fcm',
    );

    final notification = message.notification;
    if (notification == null) return;

    unawaited(_localNotifications.show(
      id: notification.hashCode,
      title: notification.title,
      body: notification.body,
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          _vpnChannel.id,
          _vpnChannel.name,
          channelDescription: _vpnChannel.description,
          importance: _vpnChannel.importance,
          priority: Priority.high,
          icon: '@mipmap/ic_launcher',
        ),
        iOS: const DarwinNotificationDetails(
          presentAlert: true,
          presentBadge: true,
          presentSound: true,
        ),
      ),
      payload: message.data['route'] as String?,
    ));
  }

  /// Handles a notification tap that opened the app from the background or
  /// terminated state.
  void _handleMessageOpenedApp(RemoteMessage message) {
    AppLogger.info(
      'FCM message opened app: ${message.messageId} '
      'data=${message.data}',
      category: 'fcm',
    );

    final route = message.data['route'] as String?;
    if (route != null && route.isNotEmpty) {
      _navigateToRoute(route);
    }
  }

  /// Initializes the local notifications plugin and creates the Android
  /// notification channel.
  Future<void> _initLocalNotifications() async {
    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );
    const initSettings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _localNotifications.initialize(
      settings: initSettings,
      onDidReceiveNotificationResponse: (NotificationResponse response) {
        AppLogger.info(
          'Local notification tapped: payload=${response.payload}',
          category: 'fcm',
        );
        onNotificationTap?.call(response.payload);
      },
    );

    // Create the Android notification channel.
    if (Platform.isAndroid) {
      await _localNotifications
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(_vpnChannel);
    }
  }

  /// Navigates to the given [route] using the root navigator.
  ///
  /// Only navigates if the route starts with `/` and a navigator context is
  /// available. The delay ensures the app frame has fully rendered after
  /// launch from a terminated state.
  void _navigateToRoute(String route) {
    if (!route.startsWith('/')) {
      AppLogger.warning(
        'Invalid notification route (must start with /): $route',
        category: 'fcm',
      );
      return;
    }

    // Delay navigation slightly to ensure the app is fully initialized
    // (important when launching from terminated state via notification tap).
    unawaited(Future<void>.delayed(const Duration(milliseconds: 300), () {
      final context = rootNavigatorKey.currentContext;
      if (context == null) {
        AppLogger.warning(
          'Cannot navigate to $route: no navigator context',
          category: 'fcm',
        );
        return;
      }

      AppLogger.info('Navigating from notification tap: $route', category: 'fcm');
      // The context here is from rootNavigatorKey.currentContext which is
      // always valid if non-null — the `mounted` lint is a false positive
      // for GlobalKey contexts.
      // ignore: use_build_context_synchronously
      unawaited(GoRouter.of(context).push(route));
    }));
  }

  /// Handles FCM token refresh by re-registering with the backend.
  ///
  /// Runs asynchronously without blocking. Errors are logged but not thrown.
  void _handleTokenRefresh(String newToken) {
    // Run in fire-and-forget manner
    unawaited(Future(() async {
      if (_fcmTokenService == null) {
        AppLogger.warning(
          'FCM token service not set - skipping token refresh registration',
          category: 'fcm',
        );
        return;
      }

      try {
        AppLogger.info(
          'Re-registering FCM token with backend after refresh',
          category: 'fcm',
        );

        final success = await _fcmTokenService!.registerToken();

        if (success) {
          AppLogger.info(
            'FCM token re-registered successfully after refresh',
            category: 'fcm',
          );
        } else {
          AppLogger.warning(
            'FCM token re-registration failed after refresh',
            category: 'fcm',
          );
        }
      } catch (e, st) {
        AppLogger.error(
          'Error re-registering FCM token after refresh',
          error: e,
          stackTrace: st,
          category: 'fcm',
        );
      }
    }));
  }

  /// Releases resources held by this service.
  ///
  /// Call during app teardown if needed.
  void dispose() {
    unawaited(_tokenRefreshSub?.cancel());
    _tokenRefreshSub = null;
  }
}

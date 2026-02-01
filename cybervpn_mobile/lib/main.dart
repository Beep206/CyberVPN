import 'dart:async';
import 'dart:ui';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/app/app.dart';
import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/services/fcm_token_service.dart';
import 'package:cybervpn_mobile/core/services/push_notification_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/quick_actions/domain/services/quick_actions_service.dart';
import 'package:cybervpn_mobile/shared/widgets/global_error_screen.dart';

// Global provider container reference for accessing services
// before the widget tree is built.
late final ProviderContainer _globalContainer;

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Load .env file for local development fallback values.
  await EnvironmentConfig.init();

  // Initialize SharedPreferences before runApp so providers can access
  // it synchronously via the overridden sharedPreferencesProvider.
  final prefs = await SharedPreferences.getInstance();

  // Create the provider container with all overrides
  _globalContainer = ProviderContainer(
    // buildProviderOverrides returns List (raw) because Riverpod 3.0.3
    // does not publicly export the Override type.
    // ignore: argument_type_not_assignable
    overrides: buildProviderOverrides(prefs),
  );

  // Defer non-critical initialization to post-launch for faster cold start.
  WidgetsBinding.instance.addPostFrameCallback((_) {
    _initializeDeferredServices();
  });

  final dsn = EnvironmentConfig.sentryDsn;

  if (dsn.isNotEmpty) {
    await SentryFlutter.init(
      (options) {
        options.dsn = dsn;
        options.environment = EnvironmentConfig.environment;
        options.tracesSampleRate = 1.0;
        options.sendDefaultPii = false;
      },
      appRunner: () => _runApp(prefs),
    );
  } else {
    // Sentry disabled (local/dev) -- run the app directly.
    _runApp(prefs);
  }
}

/// Initializes non-critical services after the first frame is rendered.
///
/// Deferred services include:
/// - Firebase Core (for analytics, messaging, etc.)
/// - Push notification handlers (FCM)
/// - Quick actions (long-press app shortcuts)
///
/// This reduces cold start time by avoiding blocking the main thread during launch.
Future<void> _initializeDeferredServices() async {
  // Initialize Firebase Core. This must happen before any other Firebase
  // service (Messaging, Analytics, etc.) is used.
  await _initializeFirebase();

  // Set up Firebase Cloud Messaging (FCM) handlers.
  // Inject the FCM token service so it can register tokens on refresh.
  final fcmTokenService = _globalContainer.read(fcmTokenServiceProvider);
  PushNotificationService.instance.setFcmTokenService(fcmTokenService);
  await PushNotificationService.instance.initialize();

  // Initialize quick actions (long-press app shortcuts).
  await QuickActionsService.instance.initialize();
}

/// Initializes Firebase Core.
///
/// Wrapped in try-catch so the app can still start when Firebase platform
/// config files (`google-services.json` / `GoogleService-Info.plist`) are
/// missing -- e.g. during local development without a Firebase project.
Future<void> _initializeFirebase() async {
  try {
    await Firebase.initializeApp();
    AppLogger.info('Firebase Core initialized', category: 'firebase');
  } catch (e, st) {
    AppLogger.warning(
      'Firebase Core initialization failed -- Firebase services will be unavailable',
      error: e,
      stackTrace: st,
      category: 'firebase',
    );
  }
}

/// Launches the application inside a [ProviderScope].
///
/// Configures [FlutterError.onError] and [PlatformDispatcher.instance.onError]
/// to forward uncaught exceptions to Sentry when it is initialised.
void _runApp(SharedPreferences prefs) {
  // Capture Flutter framework errors (e.g. build/layout/painting failures).
  FlutterError.onError = (FlutterErrorDetails details) {
    FlutterError.presentError(details);
    if (EnvironmentConfig.sentryDsn.isNotEmpty) {
      Sentry.captureException(
        details.exception,
        stackTrace: details.stack,
      );
    }
  };

  // Capture platform-level errors that escape the Flutter framework.
  PlatformDispatcher.instance.onError = (Object error, StackTrace stack) {
    if (EnvironmentConfig.sentryDsn.isNotEmpty) {
      Sentry.captureException(error, stackTrace: stack);
    }
    return true;
  };

  // Replace the default red error screen with a user-friendly error widget.
  ErrorWidget.builder = (FlutterErrorDetails details) {
    return GlobalErrorScreen(error: details);
  };

  runApp(
    // Use UncontrolledProviderScope to reuse the existing container
    UncontrolledProviderScope(
      container: _globalContainer,
      child: const CyberVpnApp(),
    ),
  );
}

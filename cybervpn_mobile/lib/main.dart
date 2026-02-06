import 'dart:async';
import 'dart:ui';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:cybervpn_mobile/app/app.dart';
import 'package:cybervpn_mobile/core/analytics/analytics_providers.dart'
    show markFirebaseReady;
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
  final totalSw = Stopwatch()..start();
  final stepSw = Stopwatch();

  WidgetsFlutterBinding.ensureInitialized();

  // Load .env file for local development fallback values.
  stepSw.start();
  await EnvironmentConfig.init();
  _logStep('EnvironmentConfig.init', stepSw);

  // Initialize SharedPreferences before runApp so providers can access
  // it synchronously via the overridden sharedPreferencesProvider.
  stepSw
    ..reset()
    ..start();
  final prefs = await SharedPreferences.getInstance();
  _logStep('SharedPreferences.getInstance', stepSw);

  // Create the provider container with all overrides.
  // buildProviderOverrides is async because it awaits SecureStorage
  // prewarmCache to prevent race conditions during auth resolution.
  stepSw
    ..reset()
    ..start();
  final overrides = await buildProviderOverrides(prefs);
  _globalContainer = ProviderContainer(
    overrides: overrides,
  );
  _logStep('buildProviderOverrides + ProviderContainer', stepSw);

  // Defer non-critical initialization to post-launch for faster cold start.
  WidgetsBinding.instance.addPostFrameCallback((_) {
    unawaited(_initializeDeferredServices());
  });

  final dsn = EnvironmentConfig.sentryDsn;

  if (dsn.isNotEmpty) {
    stepSw
      ..reset()
      ..start();
    await SentryFlutter.init((options) {
      options.dsn = dsn;
      options.environment = EnvironmentConfig.environment;
      // Sample all traces in dev/staging; 20% in production to control costs.
      options.tracesSampleRate = EnvironmentConfig.isProd ? 0.2 : 1.0;
      options.sendDefaultPii = false;
    }, appRunner: () => _runApp(prefs));
    _logStep('SentryFlutter.init', stepSw);
  } else {
    // Sentry disabled (local/dev) -- run the app directly.
    _runApp(prefs);
  }

  totalSw.stop();
  final isDebug = () { bool d = false; assert(d = true); return d; }();
  AppLogger.info(
    'Startup complete in ${totalSw.elapsedMilliseconds}ms '
    '(${isDebug ? "debug" : "release"})',
    category: 'startup',
  );
}

/// Logs a startup step's duration. Warns if it exceeded 100ms.
void _logStep(String name, Stopwatch sw) {
  sw.stop();
  final ms = sw.elapsedMilliseconds;
  if (ms > 100) {
    AppLogger.warning(
      'Startup step "$name" took ${ms}ms (>100ms)',
      category: 'startup',
    );
  } else {
    AppLogger.info('Startup step "$name" took ${ms}ms', category: 'startup');
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
    markFirebaseReady();
    AppLogger.info('Firebase Core initialized', category: 'firebase');
  } catch (e, st) {
    // Still mark as ready so gated calls don't hang indefinitely.
    markFirebaseReady();
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
      unawaited(Sentry.captureException(details.exception, stackTrace: details.stack));
    }
  };

  // Capture platform-level errors that escape the Flutter framework.
  PlatformDispatcher.instance.onError = (Object error, StackTrace stack) {
    if (EnvironmentConfig.sentryDsn.isNotEmpty) {
      unawaited(Sentry.captureException(error, stackTrace: stack));
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

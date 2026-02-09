import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/services/fcm_token_service.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';

/// Registers the FCM device token with the backend when auth state changes.
///
/// Listens to [authProvider] and triggers FCM token registration when the
/// user becomes authenticated. Errors are logged and reported to Sentry
/// but never block the user flow.
final fcmAuthSyncProvider = Provider<void>((ref) {
  if (kDebugMode && EnvironmentConfig.isDev) {
    return;
  }

  ref.listen<AsyncValue<AuthState>>(authProvider, (previous, next) {
    final state = next.value;
    if (state == null) return;

    if (state is AuthAuthenticated) {
      unawaited(
        Future(() async {
          try {
            final fcmService = ref.read(fcmTokenServiceProvider);
            await fcmService.registerToken();
          } catch (e, st) {
            AppLogger.error(
              'Failed to register FCM token after auth',
              error: e,
              stackTrace: st,
              category: 'auth.fcm',
            );

            if (EnvironmentConfig.sentryDsn.isNotEmpty) {
              unawaited(Sentry.captureException(e, stackTrace: st));
            }
          }
        }),
      );
    }
  });
});

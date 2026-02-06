import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sentry_flutter/sentry_flutter.dart';

import 'package:cybervpn_mobile/core/config/environment_config.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';

/// Keeps Sentry's user context in sync with the authentication state.
///
/// When the user authenticates, the Sentry scope is updated with the user's
/// UUID. When the user logs out, the Sentry user is cleared.
///
/// **Privacy**: Only the user UUID is sent. Email and username are
/// intentionally omitted to comply with GDPR / `sendDefaultPii = false`
/// and to minimize the PII surface in third-party error monitoring.
final sentryUserSyncProvider = Provider<void>((ref) {
  if (EnvironmentConfig.sentryDsn.isEmpty) return;

  ref.listen<AsyncValue<AuthState>>(authProvider, (previous, next) {
    final state = next.value;
    if (state == null) return;

    switch (state) {
      case AuthAuthenticated(:final user):
        unawaited(Future(() => Sentry.configureScope((scope) async {
          await scope.setUser(SentryUser(id: user.id));
        })));
        AppLogger.debug('Sentry user set: ${user.id}', category: 'analytics.sentry');
      case AuthUnauthenticated():
        unawaited(Future(() => Sentry.configureScope((scope) async {
          await scope.setUser(null);
        })));
        AppLogger.debug('Sentry user cleared', category: 'analytics.sentry');
      default:
        break;
    }
  });
});

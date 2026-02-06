import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/security/app_attestation.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';

/// Triggers app attestation when the user authenticates.
///
/// Listens to [authProvider] and performs attestation in logging mode
/// when the user becomes authenticated. Results are logged to analytics
/// for monitoring. Never enforces (blocks) on failure in current
/// logging-only mode.
final attestationAuthProvider = Provider<void>((ref) {
  ref.listen<AsyncValue<AuthState>>(authProvider, (previous, next) {
    final prevState = previous?.value;
    final state = next.value;
    if (state == null) return;

    // Only trigger on transition TO authenticated (not on every rebuild).
    if (state is AuthAuthenticated && prevState is! AuthAuthenticated) {
      unawaited(Future(() async {
        try {
          final attestationService = ref.read(appAttestationServiceProvider);
          final result = await attestationService.generateToken(
            trigger: AttestationTrigger.login,
          );
          AppLogger.info(
            'Attestation completed: ${result.status.name}',
            category: 'auth.attestation',
          );
        } catch (e, st) {
          AppLogger.warning(
            'Attestation failed (non-blocking)',
            error: e,
            stackTrace: st,
            category: 'auth.attestation',
          );
        }
      }));
    }
  });
});

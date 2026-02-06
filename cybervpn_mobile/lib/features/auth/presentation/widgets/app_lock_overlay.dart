import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:local_auth/local_auth.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/auth/domain/services/app_lock_service.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/biometric_service.dart';

/// A fullscreen overlay that requires biometric authentication to dismiss.
///
/// This widget is shown when the app is locked after being in the background
/// for more than [AppLockService.lockTimeoutSeconds] seconds.
class AppLockOverlay extends ConsumerStatefulWidget {
  const AppLockOverlay({super.key});

  @override
  ConsumerState<AppLockOverlay> createState() => _AppLockOverlayState();
}

class _AppLockOverlayState extends ConsumerState<AppLockOverlay> {
  bool _isAuthenticating = false;

  @override
  void initState() {
    super.initState();
    // Auto-trigger biometric on first display
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_attemptUnlock());
    });
  }

  Future<void> _attemptUnlock() async {
    if (_isAuthenticating) return;

    setState(() => _isAuthenticating = true);

    try {
      final service = ref.read(appLockServiceProvider);
      await service.attemptBiometricUnlock();
    } finally {
      if (mounted) {
        setState(() => _isAuthenticating = false);
      }
    }
  }

  Future<void> _attemptPinUnlock() async {
    if (_isAuthenticating) return;

    setState(() => _isAuthenticating = true);

    try {
      // Use local_auth with biometricOnly: false to allow PIN/passcode
      final localAuth = LocalAuthentication();
      final authenticated = await localAuth.authenticate(
        localizedReason: 'Unlock CyberVPN with your device PIN',
        biometricOnly: false,
        persistAcrossBackgrounding: true,
      );

      if (authenticated) {
        final service = ref.read(appLockServiceProvider);
        service.unlock();
      }
    } finally {
      if (mounted) {
        setState(() => _isAuthenticating = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final service = ref.watch(appLockServiceProvider);
    final failedAttempts = service.failedAttempts;
    final showPinFallback = service.shouldShowPasswordFallback;
    final biometricTypes = ref.watch(availableBiometricsProvider);

    // Determine biometric type for display
    final biometricLabel = biometricTypes.when(
      data: (types) {
        if (types.contains(BiometricType.face)) {
          return 'Face ID';
        }
        return 'fingerprint';
      },
      loading: () => 'biometrics',
      error: (_, __) => 'biometrics',
    );

    final biometricIcon = biometricTypes.when(
      data: (types) {
        if (types.contains(BiometricType.face)) {
          return Icons.face;
        }
        return Icons.fingerprint;
      },
      loading: () => Icons.fingerprint,
      error: (_, __) => Icons.fingerprint,
    );

    return PopScope(
      canPop: false, // Prevent back button from dismissing
      child: Scaffold(
        body: Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                theme.colorScheme.surface,
                theme.colorScheme.surfaceContainerLowest,
              ],
            ),
          ),
          child: SafeArea(
            child: Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 32),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Lock icon
                    Icon(
                      Icons.lock_outline,
                      size: 80,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(height: 24),

                    // Title
                    Text(
                      'CyberVPN Locked',
                      style: theme.textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),

                    // Subtitle
                    Text(
                      'Authenticate to continue',
                      style: theme.textTheme.bodyLarge?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 48),

                    // Biometric unlock button
                    if (!showPinFallback) ...[
                      Semantics(
                        button: true,
                        enabled: !_isAuthenticating,
                        label: _isAuthenticating
                            ? 'Authenticating, please wait'
                            : 'Unlock with $biometricLabel',
                        hint: 'Authenticate to unlock the app',
                        child: FilledButton.icon(
                          onPressed: _isAuthenticating ? null : _attemptUnlock,
                          icon: _isAuthenticating
                              ? SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: theme.colorScheme.onPrimary,
                                  ),
                                )
                              : Icon(biometricIcon, size: 24, semanticLabel: ''),
                          label: ExcludeSemantics(
                              child: Text(l10n.appLockUnlockWithBiometric(biometricLabel))),
                          style: FilledButton.styleFrom(
                            minimumSize: const Size(double.infinity, 56),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                        ),
                      ),

                      // Failed attempts indicator
                      if (failedAttempts > 0) ...[
                        const SizedBox(height: 16),
                        Semantics(
                          label: 'Failed authentication attempts: $failedAttempts '
                              'out of ${AppLockService.maxBiometricAttempts}',
                          child: ExcludeSemantics(
                            child: Text(
                              'Failed attempts: $failedAttempts/${AppLockService.maxBiometricAttempts}',
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.error,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ],

                    // PIN/passcode fallback (shown after max attempts)
                    if (showPinFallback) ...[
                      Text(
                        l10n.appLockTooManyAttempts,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.error,
                        ),
                      ),
                      const SizedBox(height: 24),

                      Semantics(
                        button: true,
                        enabled: !_isAuthenticating,
                        label: _isAuthenticating
                            ? 'Authenticating, please wait'
                            : 'Use device PIN',
                        hint: 'Unlock using your device PIN or passcode',
                        child: FilledButton.icon(
                          onPressed:
                              _isAuthenticating ? null : _attemptPinUnlock,
                          icon: _isAuthenticating
                              ? SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: theme.colorScheme.onPrimary,
                                  ),
                                )
                              : const Icon(Icons.pin,
                                  size: 24, semanticLabel: ''),
                          label: ExcludeSemantics(
                              child: Text(l10n.appLockUsePin)),
                          style: FilledButton.styleFrom(
                            minimumSize: const Size(double.infinity, 56),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 16),

                      // Try biometric again button
                      Semantics(
                        button: true,
                        label: 'Try $biometricLabel again',
                        hint: 'Reset failed attempts and try biometric authentication',
                        child: TextButton(
                          onPressed: () {
                            ref.read(appLockServiceProvider).resetAttempts();
                            setState(() {}); // Trigger rebuild
                          },
                          child: ExcludeSemantics(
                              child: Text(l10n.appLockTryAgain(biometricLabel))),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:local_auth/local_auth.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/security/screen_protection.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/biometric_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/biometric_login_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/telegram_auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/widgets/login_form.dart';
import 'package:cybervpn_mobile/features/auth/presentation/widgets/social_login_button.dart';

/// Full-screen login page with email/password form, social login options,
/// and a link to the registration screen.
///
/// This screen is protected against screenshots to secure user credentials.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen>
    with ScreenProtection {
  bool _biometricChecked = false;

  @override
  void initState() {
    super.initState();
    unawaited(enableProtection());
    // Check and auto-trigger biometric login after first frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_checkAndTriggerBiometric());
    });
  }

  @override
  void dispose() {
    unawaited(disableProtection());
    super.dispose();
  }

  /// Checks if biometric login is available and auto-triggers it for returning users.
  Future<void> _checkAndTriggerBiometric() async {
    if (_biometricChecked) return;
    _biometricChecked = true;

    final notifier = ref.read(biometricLoginProvider.notifier);
    final isAvailable = await notifier.checkAvailability();

    if (isAvailable && mounted) {
      // Auto-trigger biometric prompt for returning users
      await notifier.authenticate(reason: 'Sign in to CyberVPN');
    }
  }

  void _handleBiometricLogin() {
    unawaited(ref.read(biometricLoginProvider.notifier).authenticate(
          reason: 'Sign in to CyberVPN',
        ));
  }

  void _handleTelegramLogin() {
    unawaited(ref.read(telegramAuthProvider.notifier).startLogin());
  }

  void _showTelegramNotInstalledDialog() {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final notifier = ref.read(telegramAuthProvider.notifier);

    unawaited(showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(l10n.telegramNotInstalledTitle),
        content: Text(l10n.telegramNotInstalledMessage),
        actions: [
          TextButton(
            onPressed: () {
              Navigator.of(dialogContext).pop();
              notifier.cancel();
            },
            child: Text(
              l10n.cancel,
              style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
            ),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(dialogContext).pop();
              unawaited(notifier.useWebFallback());
            },
            child: Text(l10n.telegramUseWeb),
          ),
          FilledButton(
            onPressed: () {
              Navigator.of(dialogContext).pop();
              unawaited(notifier.openAppStore());
              notifier.cancel();
            },
            child: Text(l10n.telegramInstall),
          ),
        ],
      ),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isTelegramAvailable = ref.watch(isTelegramLoginAvailableProvider);
    final isTelegramLoading = ref.watch(isTelegramAuthLoadingProvider);
    final biometricState = ref.watch(biometricLoginProvider);
    final isBiometricAvailable = biometricState is BiometricLoginAvailable ||
        biometricState is BiometricLoginCancelled;
    final isBiometricLoading = biometricState is BiometricLoginAuthenticating ||
        biometricState is BiometricLoginLoggingIn;

    // Listen for auth state changes to navigate on success.
    ref.listen<AsyncValue<AuthState>>(authProvider, (previous, next) {
      final state = next.value;
      if (state is AuthAuthenticated) {
        context.go('/connection');
      }
    });

    // Listen for biometric login state changes.
    ref.listen<BiometricLoginState>(biometricLoginProvider, (previous, next) {
      if (next is BiometricLoginSuccess) {
        // Navigate on successful biometric login
        context.go('/connection');
      } else if (next is BiometricLoginEnrollmentChanged) {
        // Biometric enrollment changed - show message
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text(
              'Your biometric settings have changed. Please sign in with your '
              'password and re-enable biometric login in settings.',
            ),
            backgroundColor: theme.colorScheme.error,
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 6),
          ),
        );
      } else if (next is BiometricLoginCredentialsInvalid) {
        // Stored credentials were invalid - show message to re-enter password
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text(
              'Your password has changed. Please sign in with your password.',
            ),
            backgroundColor: theme.colorScheme.error,
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 5),
          ),
        );
      } else if (next is BiometricLoginFailed) {
        // Show error snackbar
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(next.message),
            backgroundColor: theme.colorScheme.error,
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    });

    // Listen for Telegram auth state changes.
    ref.listen<AsyncValue<TelegramAuthState>>(telegramAuthProvider,
        (previous, next) {
      final state = next.value;
      if (state is TelegramAuthSuccess) {
        // Navigate to home screen on successful auth
        context.go('/connection');
      } else if (state is TelegramAuthNotInstalled) {
        // Show dialog with install options
        _showTelegramNotInstalledDialog();
      } else if (state is TelegramAuthError) {
        // Show error snackbar
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(state.message),
            backgroundColor: theme.colorScheme.error,
            behavior: SnackBarBehavior.floating,
          ),
        );
        // Reset error state
        ref.read(telegramAuthProvider.notifier).resetError();
      }
    });

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // ── Logo / Branding ──────────────────────────────
                  Icon(
                    Icons.shield_outlined,
                    size: 64,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'CyberVPN',
                    style: theme.textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Secure your connection',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 40),

                  // ── Biometric Login Button ────────────────────────
                  if (isBiometricAvailable) ...[
                    _BiometricLoginButton(
                      onPressed: isBiometricLoading ? null : _handleBiometricLogin,
                      isLoading: isBiometricLoading,
                    ),
                    const SizedBox(height: 24),
                    Row(
                      children: [
                        Expanded(
                            child: Divider(
                                color: theme.colorScheme.outlineVariant)),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: Text(
                            'OR USE PASSWORD',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ),
                        Expanded(
                            child: Divider(
                                color: theme.colorScheme.outlineVariant)),
                      ],
                    ),
                    const SizedBox(height: 24),
                  ],

                  // ── Login Form ───────────────────────────────────
                  LoginForm(
                    onSuccess: () => context.go('/connection'),
                    onForgotPassword: () {
                      // TODO: implement forgot-password flow
                    },
                  ),
                  const SizedBox(height: 28),

                  // ── Divider ──────────────────────────────────────
                  if (isTelegramAvailable) ...[
                    Row(
                      children: [
                        Expanded(
                            child: Divider(
                                color: theme.colorScheme.outlineVariant)),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 16),
                          child: Text(
                            'OR',
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ),
                        Expanded(
                            child: Divider(
                                color: theme.colorScheme.outlineVariant)),
                      ],
                    ),
                    const SizedBox(height: 28),

                    // ── Social Login ─────────────────────────────────
                    SocialLoginButton.telegram(
                      onPressed: isTelegramLoading ? null : _handleTelegramLogin,
                      isLoading: isTelegramLoading,
                    ),
                    const SizedBox(height: 32),
                  ] else
                    const SizedBox(height: 32),

                  // ── Register Link ────────────────────────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        "Don't have an account? ",
                        style: theme.textTheme.bodyMedium,
                      ),
                      Semantics(
                        button: true,
                        label: 'Register',
                        hint: 'Create a new account',
                        child: GestureDetector(
                          onTap: () => context.go('/register'),
                          child: ExcludeSemantics(
                            child: Text(
                              'Register',
                              style: theme.textTheme.bodyMedium?.copyWith(
                                color: theme.colorScheme.primary,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// A button for biometric login that shows fingerprint or face icon.
class _BiometricLoginButton extends ConsumerWidget {
  final VoidCallback? onPressed;
  final bool isLoading;

  const _BiometricLoginButton({
    required this.onPressed,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final biometricTypes = ref.watch(availableBiometricsProvider);

    // Determine the icon based on available biometrics
    final IconData icon = biometricTypes.when(
      data: (types) {
        if (types.contains(BiometricType.face)) {
          return Icons.face;
        }
        return Icons.fingerprint;
      },
      loading: () => Icons.fingerprint,
      error: (_, __) => Icons.fingerprint,
    );

    final String label = biometricTypes.when(
      data: (types) {
        if (types.contains(BiometricType.face)) {
          return 'Sign in with Face ID';
        }
        return 'Sign in with fingerprint';
      },
      loading: () => 'Sign in with biometrics',
      error: (_, __) => 'Sign in with biometrics',
    );

    return Semantics(
      button: true,
      enabled: onPressed != null,
      label: isLoading ? 'Authenticating with biometrics, please wait' : label,
      hint: 'Use biometrics to sign in quickly',
      child: FilledButton.icon(
        onPressed: onPressed,
        icon: isLoading
            ? SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: theme.colorScheme.onPrimary,
                ),
              )
            : Icon(icon, size: 24, semanticLabel: ''),
        label: ExcludeSemantics(child: Text(label)),
        style: FilledButton.styleFrom(
          minimumSize: const Size(double.infinity, 56),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
    );
  }
}

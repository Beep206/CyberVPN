import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:local_auth/local_auth.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/security/screen_protection.dart';
import 'package:cybervpn_mobile/features/auth/domain/usecases/biometric_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/biometric_login_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/telegram_auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/widgets/login_form.dart';
import 'package:cybervpn_mobile/features/auth/presentation/widgets/social_login_button.dart';
import 'package:cybervpn_mobile/shared/widgets/responsive_layout.dart';

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
      final l10n = AppLocalizations.of(context);
      await notifier.authenticate(reason: l10n.biometricSignInReason);
    }
  }

  void _handleBiometricLogin() {
    final l10n = AppLocalizations.of(context);
    unawaited(ref.read(biometricLoginProvider.notifier).authenticate(
          reason: l10n.biometricSignInReason,
        ));
  }

  void _handleTelegramLogin() {
    unawaited(ref.read(telegramAuthProvider.notifier).startLogin());
  }

  void _showComingSoon() {
    final l10n = AppLocalizations.of(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(l10n.socialLoginComingSoon),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
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
    final l10n = AppLocalizations.of(context);
    final isTelegramAvailable = ref.watch(isTelegramLoginAvailableProvider);
    final isTelegramLoading = ref.watch(isTelegramAuthLoadingProvider);
    final biometricState = ref.watch(biometricLoginProvider);
    final isBiometricAvailable = biometricState is BiometricLoginAvailable ||
        biometricState is BiometricLoginCancelled;
    final isBiometricLoading = biometricState is BiometricLoginAuthenticating ||
        biometricState is BiometricLoginLoggingIn;
    final authState = ref.watch(authProvider);
    final isAuthLoading = authState.value is AuthLoading;
    final isLoading = isTelegramLoading || isBiometricLoading || isAuthLoading;

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
            content: Text(l10n.biometricSettingsChanged),
            backgroundColor: theme.colorScheme.error,
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 6),
          ),
        );
      } else if (next is BiometricLoginCredentialsInvalid) {
        // Stored credentials were invalid - show message to re-enter password
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(l10n.biometricPasswordChanged),
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
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: Spacing.lg, vertical: Spacing.xl),
            child: LayoutBuilder(
              builder: (context, constraints) {
                // Use 90% of available width on phones, cap at 480 on tablets
                final maxWidth = constraints.maxWidth > 600 ? 480.0 : constraints.maxWidth;
                return ConstrainedBox(
                  constraints: BoxConstraints(maxWidth: maxWidth),
                  child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // ── Logo / Branding ──────────────────────────────
                  Icon(
                    Icons.shield_outlined,
                    size: 64,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(height: Spacing.md),
                  Text(
                    l10n.loginTitle,
                    style: theme.textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const SizedBox(height: Spacing.sm),
                  Text(
                    l10n.loginSubtitle,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: Spacing.xl + Spacing.sm),

                  // ── Biometric Login Button ────────────────────────
                  if (isBiometricAvailable) ...[
                    _BiometricLoginButton(
                      onPressed: isBiometricLoading ? null : _handleBiometricLogin,
                      isLoading: isBiometricLoading,
                    ),
                    const SizedBox(height: Spacing.lg),
                    Row(
                      children: [
                        Expanded(
                            child: Divider(
                                color: theme.colorScheme.outlineVariant)),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
                          child: Text(
                            l10n.loginOrUsePassword,
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
                    const SizedBox(height: Spacing.lg),
                  ],

                  // ── Login Form ───────────────────────────────────
                  LoginForm(
                    onSuccess: () => context.go('/connection'),
                    onForgotPassword: () {
                      context.push('/forgot-password');
                    },
                  ),
                  const SizedBox(height: Spacing.lg + Spacing.xs),

                  // ── Divider ──────────────────────────────────────
                  Row(
                    children: [
                      Expanded(
                          child: Divider(
                              color: theme.colorScheme.outlineVariant)),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
                        child: Text(
                          l10n.loginOrSeparator,
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
                  const SizedBox(height: Spacing.lg + Spacing.xs),

                  // ── Social Login — Google (full-width) ─────────
                  _SocialOutlinedButton(
                    icon: Icons.g_mobiledata,
                    label: l10n.continueWithGoogle,
                    onPressed: isLoading ? null : _showComingSoon,
                  ),
                  const SizedBox(height: Spacing.sm),

                  // ── Social Login — Apple (full-width, iOS only) ─
                  if (Platform.isIOS) ...[
                    _SocialOutlinedButton(
                      icon: Icons.apple,
                      label: l10n.continueWithApple,
                      onPressed: isLoading ? null : _showComingSoon,
                    ),
                    const SizedBox(height: Spacing.sm),
                  ],

                  // ── Social Login — Compact icon row ────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _CompactSocialIcon(
                        icon: Icons.code,
                        tooltip: 'GitHub',
                        onPressed: isLoading ? null : _showComingSoon,
                      ),
                      const SizedBox(width: Spacing.md),
                      _CompactSocialIcon(
                        icon: Icons.discord,
                        tooltip: 'Discord',
                        onPressed: isLoading ? null : _showComingSoon,
                      ),
                      const SizedBox(width: Spacing.md),
                      _CompactSocialIcon(
                        icon: Icons.window,
                        tooltip: 'Microsoft',
                        onPressed: isLoading ? null : _showComingSoon,
                      ),
                      const SizedBox(width: Spacing.md),
                      _CompactSocialIcon(
                        iconWidget: const Text(
                          'X',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        tooltip: 'X',
                        onPressed: isLoading ? null : _showComingSoon,
                      ),
                    ],
                  ),
                  const SizedBox(height: Spacing.sm),

                  // ── Social Login — Telegram (full-width) ───────
                  if (isTelegramAvailable) ...[
                    SocialLoginButton.telegram(
                      onPressed: isLoading ? null : _handleTelegramLogin,
                      isLoading: isTelegramLoading,
                    ),
                    const SizedBox(height: Spacing.sm),
                  ],

                  // ── Magic Link ─────────────────────────────────
                  TextButton(
                    onPressed: isLoading ? null : () => context.push('/magic-link'),
                    child: Text(
                      l10n.loginMagicLinkOption,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.primary,
                      ),
                    ),
                  ),
                  const SizedBox(height: Spacing.lg),

                  // ── Register Link ────────────────────────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        l10n.loginNoAccount,
                        style: theme.textTheme.bodyMedium,
                      ),
                      Semantics(
                        button: true,
                        label: l10n.loginRegisterLink,
                        hint: l10n.register,
                        child: GestureDetector(
                          onTap: () => context.go('/register'),
                          child: ExcludeSemantics(
                            child: Text(
                              l10n.loginRegisterLink,
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
                );
              },
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
      error: (_, _) => Icons.fingerprint,
    );

    final l10n = AppLocalizations.of(context);
    final String label = biometricTypes.when(
      data: (types) {
        if (types.contains(BiometricType.face)) {
          return l10n.loginBiometricFaceId;
        }
        return l10n.loginBiometricFingerprint;
      },
      loading: () => l10n.loginBiometricGeneric,
      error: (_, _) => l10n.loginBiometricGeneric,
    );

    return Semantics(
      button: true,
      enabled: onPressed != null,
      label: isLoading ? l10n.loginBiometricAuthenticating : label,
      hint: AppLocalizations.of(context).biometricSignInHint,
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
            borderRadius: BorderRadius.circular(Radii.md),
          ),
        ),
      ),
    );
  }
}

/// A full-width outlined button for social login providers (Google, Apple, etc.).
class _SocialOutlinedButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback? onPressed;

  const _SocialOutlinedButton({
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SizedBox(
      width: double.infinity,
      height: 48,
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, size: 24),
        label: Text(
          label,
          style: theme.textTheme.labelLarge?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        style: OutlinedButton.styleFrom(
          side: BorderSide(color: theme.colorScheme.outline),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(Radii.md),
          ),
        ),
      ),
    );
  }
}

/// A compact circular icon button for secondary social login providers.
class _CompactSocialIcon extends StatelessWidget {
  final IconData? icon;
  final Widget? iconWidget;
  final String tooltip;
  final VoidCallback? onPressed;

  const _CompactSocialIcon({
    this.icon,
    this.iconWidget,
    required this.tooltip,
    required this.onPressed,
  }) : assert(icon != null || iconWidget != null);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Colors.transparent,
        shape: const CircleBorder(),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onPressed,
          customBorder: const CircleBorder(),
          child: Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: onPressed != null
                    ? theme.colorScheme.outline
                    : theme.colorScheme.outline.withValues(alpha: 0.38),
              ),
            ),
            child: Center(
              child: iconWidget ??
                  Icon(
                    icon,
                    size: 22,
                    color: onPressed != null
                        ? theme.colorScheme.onSurface
                        : theme.colorScheme.onSurface.withValues(alpha: 0.38),
                  ),
            ),
          ),
        ),
      ),
    );
  }
}

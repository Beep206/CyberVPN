import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/core/security/screen_protection.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
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
  @override
  void initState() {
    super.initState();
    enableProtection();
  }

  @override
  void dispose() {
    disableProtection();
    super.dispose();
  }

  void _handleTelegramLogin() {
    ref.read(telegramAuthProvider.notifier).startLogin();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isTelegramAvailable = ref.watch(isTelegramLoginAvailableProvider);
    final isTelegramLoading = ref.watch(isTelegramAuthLoadingProvider);

    // Listen for auth state changes to navigate on success.
    ref.listen<AsyncValue<AuthState>>(authProvider, (previous, next) {
      final state = next.value;
      if (state is AuthAuthenticated) {
        context.go('/connection');
      }
    });

    // Listen for Telegram auth state changes.
    ref.listen<AsyncValue<TelegramAuthState>>(telegramAuthProvider,
        (previous, next) {
      final state = next.value;
      if (state is TelegramAuthSuccess) {
        // Navigate to home screen on successful auth
        context.go('/connection');
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
                      GestureDetector(
                        onTap: () => context.go('/register'),
                        child: Text(
                          'Register',
                          style: theme.textTheme.bodyMedium?.copyWith(
                            color: theme.colorScheme.primary,
                            fontWeight: FontWeight.w600,
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

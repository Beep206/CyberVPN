import 'package:flutter/gestures.dart';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/routing/deep_link_handler.dart';
import 'package:cybervpn_mobile/core/routing/deep_link_parser.dart';
import 'package:cybervpn_mobile/core/security/screen_protection.dart';
import 'package:cybervpn_mobile/core/utils/input_validators.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_state.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/telegram_auth_provider.dart';
import 'package:cybervpn_mobile/features/auth/presentation/widgets/social_login_button.dart';
import 'package:cybervpn_mobile/features/referral/presentation/providers/referral_provider.dart';
import 'package:cybervpn_mobile/shared/widgets/animated_form_field.dart';

/// Registration screen with email, password (with strength indicator),
/// confirm-password, optional referral code, and T&C acceptance.
///
/// This screen is protected against screenshots to secure user credentials.
class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen>
    with ScreenProtection {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _referralCodeController = TextEditingController();
  final _usernameController = TextEditingController();

  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;
  bool _acceptedTerms = false;
  bool _isReferralCodeValid = false;
  bool _isUsernameOnlyMode = false;

  @override
  void initState() {
    super.initState();
    unawaited(enableProtection());

    // Check for pending referral deep link after first frame
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkForReferralDeepLink();
    });
  }

  /// Checks for pending referral deep link and auto-fills the referral code field.
  void _checkForReferralDeepLink() {
    // Check if there's a pending deep link that's a ReferralRoute
    final pendingRoute = ref.read(pendingDeepLinkProvider);

    if (pendingRoute is ReferralRoute) {
      final code = pendingRoute.code;

      // Auto-fill the referral code field
      _referralCodeController.text = code.toUpperCase();

      // Validate immediately
      setState(() {
        _isReferralCodeValid =
            InputValidators.validateReferralCode(code) == null;
      });

      // Clear the pending deep link since we consumed it
      ref.read(pendingDeepLinkProvider.notifier).clear();

      // Show a brief confirmation
      if (mounted && _isReferralCodeValid) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              AppLocalizations.of(context).registerReferralFromLink,
            ),
            duration: Duration(seconds: 2),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  @override
  void dispose() {
    unawaited(disableProtection());
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _referralCodeController.dispose();
    _usernameController.dispose();
    super.dispose();
  }

  // ── Password strength ─────────────────────────────────────────────

  /// Returns a strength level: 0 = empty, 1 = weak, 2 = medium, 3 = strong.
  int _passwordStrength(String password) {
    if (password.isEmpty) return 0;
    int score = 0;
    if (password.length >= 8) score++;
    if (RegExp(r'[A-Z]').hasMatch(password) &&
        RegExp(r'[a-z]').hasMatch(password)) {
      score++;
    }
    if (RegExp(r'[0-9]').hasMatch(password) &&
        RegExp(r'[!@#\$%^&*(),.?":{}|<>]').hasMatch(password)) {
      score++;
    }
    return score;
  }

  // WCAG AA compliant colors for text on light/dark backgrounds
  static const _weakColor = Color(0xFFC62828); // Red 800: 7.1:1 on white
  static const _mediumColor = Color(0xFFEF6C00); // Orange 800: 4.5:1 on white
  static const _strongColor = Color(0xFF2E7D32); // Green 800: 5.1:1 on white

  Color _strengthColor(int strength) => switch (strength) {
    1 => _weakColor,
    2 => _mediumColor,
    3 => _strongColor,
    _ => Colors.transparent,
  };

  String _strengthLabel(int strength, AppLocalizations l10n) =>
      switch (strength) {
        1 => l10n.registerPasswordStrengthWeak,
        2 => l10n.registerPasswordStrengthMedium,
        3 => l10n.registerPasswordStrengthStrong,
        _ => '',
      };

  // ── Telegram not installed dialog ───────────────────────────────

  void _showTelegramNotInstalledDialog() {
    final theme = Theme.of(context);
    final notifier = ref.read(telegramAuthProvider.notifier);

    unawaited(
      showDialog<void>(
        context: context,
        builder: (dialogContext) {
          final l10n = AppLocalizations.of(dialogContext);
          return AlertDialog(
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
          );
        },
      ),
    );
  }

  // ── Submit ────────────────────────────────────────────────────────

  Future<void> _onSubmit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    if (!_acceptedTerms) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).registerAcceptTermsError),
          backgroundColor: Theme.of(context).colorScheme.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    final referral = _referralCodeController.text.trim();

    // In username-only mode, pass the username as the first argument.
    // The backend register endpoint accepts both email and username
    // in the same field (login_or_email concept).
    final identifier = _isUsernameOnlyMode
        ? _usernameController.text.trim()
        : _emailController.text.trim();

    await ref
        .read(authProvider.notifier)
        .register(
          identifier,
          _passwordController.text,
          referralCode: referral.isEmpty ? null : referral,
        );

    if (!mounted) return;

    final authState = ref.read(authProvider).value;

    switch (authState) {
      case AuthError(:final message):
        _passwordController.clear();
        _confirmPasswordController.clear();
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: Theme.of(context).colorScheme.error,
            behavior: SnackBarBehavior.floating,
          ),
        );
      case AuthAuthenticated():
        if (!mounted) return;
        context.go('/connection');
      default:
        break;
    }
  }

  // ── Build ─────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final authAsync = ref.watch(authProvider);
    final authState = authAsync.value;
    final isLoading = authState is AuthLoading;

    // Listen for external auth state changes (e.g. from social login).
    ref.listen<AsyncValue<AuthState>>(authProvider, (_, next) {
      if (next.value is AuthAuthenticated) {
        context.go('/connection');
      }
    });

    // Listen for Telegram auth state changes.
    ref.listen<AsyncValue<TelegramAuthState>>(telegramAuthProvider, (
      previous,
      next,
    ) {
      final state = next.value;
      if (state is TelegramAuthSuccess) {
        context.go('/connection');
      } else if (state is TelegramAuthNotInstalled) {
        _showTelegramNotInstalledDialog();
      } else if (state is TelegramAuthError) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(state.message),
            backgroundColor: theme.colorScheme.error,
            behavior: SnackBarBehavior.floating,
          ),
        );
        ref.read(telegramAuthProvider.notifier).resetError();
      }
    });

    final strength = _passwordStrength(_passwordController.text);

    return Scaffold(
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: FocusTraversalGroup(
                policy: OrderedTraversalPolicy(),
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // ── Logo ───────────────────────────────────────
                      Icon(
                        Icons.shield_outlined,
                        size: 56,
                        color: theme.colorScheme.primary,
                      ),
                      const SizedBox(height: 12),
                      Text(
                        l10n.registerTitle,
                        style: theme.textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        l10n.registerSubtitle,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 24),

                      // ── Registration mode toggle ─────────────────
                      SegmentedButton<bool>(
                        segments: [
                          ButtonSegment<bool>(
                            value: false,
                            label: Text(l10n.registerModeEmail),
                            icon: const Icon(Icons.email_outlined),
                          ),
                          ButtonSegment<bool>(
                            value: true,
                            label: Text(l10n.registerModeUsernameOnly),
                            icon: const Icon(Icons.person_outlined),
                          ),
                        ],
                        selected: {_isUsernameOnlyMode},
                        onSelectionChanged: isLoading
                            ? null
                            : (Set<bool> selection) {
                                setState(() {
                                  _isUsernameOnlyMode = selection.first;
                                });
                              },
                      ),
                      const SizedBox(height: 16),

                      // ── Username-only warning banner ─────────────
                      if (_isUsernameOnlyMode) ...[
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.errorContainer,
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: theme.colorScheme.error.withValues(
                                alpha: 0.3,
                              ),
                            ),
                          ),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(
                                Icons.warning_amber_rounded,
                                color: theme.colorScheme.onErrorContainer,
                                size: 20,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  l10n.registerUsernameOnlyWarning,
                                  style: theme.textTheme.bodySmall?.copyWith(
                                    color: theme.colorScheme.onErrorContainer,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],

                      // ── Username field (username-only mode) ──────
                      if (_isUsernameOnlyMode) ...[
                        AnimatedFormField(
                          child: FocusTraversalOrder(
                            order: const NumericFocusOrder(1),
                            child: TextFormField(
                              controller: _usernameController,
                              enabled: !isLoading,
                              keyboardType: TextInputType.text,
                              textInputAction: TextInputAction.next,
                              autofillHints: const [AutofillHints.username],
                              decoration: InputDecoration(
                                labelText: l10n.registerUsernameLabel,
                                hintText: l10n.registerUsernameHint,
                                prefixIcon: const Icon(
                                  Icons.person_outlined,
                                  semanticLabel: '',
                                ),
                              ),
                              validator: (value) {
                                final error =
                                    InputValidators.validateUsername(value);
                                if (error != null) {
                                  return l10n.registerUsernameValidationError;
                                }
                                return null;
                              },
                              autovalidateMode:
                                  AutovalidateMode.onUserInteraction,
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],

                      // ── Email (email mode only) ──────────────────
                      if (!_isUsernameOnlyMode) ...[
                        AnimatedFormField(
                          child: FocusTraversalOrder(
                            order: const NumericFocusOrder(1),
                            child: TextFormField(
                              controller: _emailController,
                              enabled: !isLoading,
                              keyboardType: TextInputType.emailAddress,
                              textInputAction: TextInputAction.next,
                              autofillHints: const [AutofillHints.email],
                              decoration: InputDecoration(
                                labelText: l10n.formEmailLabel,
                                hintText: l10n.formEmailHint,
                                prefixIcon: Icon(
                                  Icons.email_outlined,
                                  semanticLabel: '', // Hide from screen reader
                                ),
                              ),
                              validator: InputValidators.validateEmail,
                              autovalidateMode:
                                  AutovalidateMode.onUserInteraction,
                            ),
                          ),
                        ),
                        const SizedBox(height: 16),
                      ],

                      // ── Password ───────────────────────────────────
                      AnimatedFormField(
                        child: FocusTraversalOrder(
                          order: const NumericFocusOrder(2),
                          child: TextFormField(
                            controller: _passwordController,
                            enabled: !isLoading,
                            obscureText: _obscurePassword,
                            textInputAction: TextInputAction.next,
                            autofillHints: const [AutofillHints.newPassword],
                            decoration: InputDecoration(
                              labelText: l10n.formPasswordLabel,
                              hintText: l10n.registerPasswordHint,
                              prefixIcon: const Icon(
                                Icons.lock_outlined,
                                semanticLabel: '', // Hide from screen reader
                              ),
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _obscurePassword
                                      ? Icons.visibility_outlined
                                      : Icons.visibility_off_outlined,
                                  semanticLabel: '', // Handled by tooltip
                                ),
                                tooltip: _obscurePassword
                                    ? l10n.formShowPassword
                                    : l10n.formHidePassword,
                                onPressed: isLoading
                                    ? null
                                    : () => setState(
                                        () =>
                                            _obscurePassword = !_obscurePassword,
                                      ),
                              ),
                            ),
                            validator: InputValidators.validatePassword,
                            autovalidateMode: AutovalidateMode.onUserInteraction,
                            onChanged: (_) => setState(() {}),
                          ),
                        ),
                      ),

                      // ── Password strength indicator ────────────────
                      if (_passwordController.text.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Semantics(
                          label:
                              'Password strength: ${_strengthLabel(strength, l10n)}',
                          value: '${(strength * 100 / 3).round()} percent',
                          child: Row(
                            children: [
                              Expanded(
                                child: ExcludeSemantics(
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(4),
                                    child: LinearProgressIndicator(
                                      value: strength / 3,
                                      minHeight: 4,
                                      backgroundColor: theme
                                          .colorScheme
                                          .surfaceContainerHighest,
                                      color: _strengthColor(strength),
                                    ),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 12),
                              ExcludeSemantics(
                                child: Text(
                                  _strengthLabel(strength, l10n),
                                  style: theme.textTheme.bodySmall?.copyWith(
                                    color: _strengthColor(strength),
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                      const SizedBox(height: 16),

                      // ── Confirm password ───────────────────────────
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(3),
                        child: TextFormField(
                          controller: _confirmPasswordController,
                          enabled: !isLoading,
                          obscureText: _obscureConfirmPassword,
                          textInputAction: TextInputAction.next,
                          decoration: InputDecoration(
                            labelText: l10n.registerConfirmPasswordLabel,
                            hintText: l10n.registerConfirmPasswordHint,
                            prefixIcon: const Icon(
                              Icons.lock_outlined,
                              semanticLabel: '', // Hide from screen reader
                            ),
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscureConfirmPassword
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                                semanticLabel: '', // Handled by tooltip
                              ),
                              tooltip: _obscureConfirmPassword
                                  ? l10n.formShowPassword
                                  : l10n.formHidePassword,
                              onPressed: isLoading
                                  ? null
                                  : () => setState(
                                      () => _obscureConfirmPassword =
                                          !_obscureConfirmPassword,
                                    ),
                            ),
                          ),
                          validator: (value) {
                            if (value == null || value.isEmpty) {
                              return l10n.registerConfirmPasswordError;
                            }
                            if (value != _passwordController.text) {
                              return l10n.registerPasswordMismatch;
                            }
                            return null;
                          },
                          autovalidateMode: AutovalidateMode.onUserInteraction,
                        ),
                      ),
                      const SizedBox(height: 16),

                      // ── Referral code (optional) ───────────────────
                      // Only show if referral system is available
                      if (ref.watch(isReferralAvailableProvider)) ...[
                        FocusTraversalOrder(
                          order: const NumericFocusOrder(4),
                          child: TextFormField(
                            controller: _referralCodeController,
                            enabled: !isLoading,
                            textInputAction: TextInputAction.done,
                            textCapitalization: TextCapitalization.characters,
                            decoration: InputDecoration(
                              labelText: l10n.registerReferralCodeLabel,
                              hintText: l10n.registerReferralCodeHint,
                              prefixIcon: const Icon(
                                Icons.card_giftcard_outlined,
                                semanticLabel: '', // Hide from screen reader
                              ),
                              suffixIcon: _isReferralCodeValid
                                  ? Icon(
                                      Icons.check_circle,
                                      color: _strongColor, // WCAG AA compliant
                                      semanticLabel:
                                          l10n.registerReferralValidA11y,
                                    )
                                  : null,
                            ),
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) {
                                return null;
                              }
                              final error =
                                  InputValidators.validateReferralCode(value);
                              return error;
                            },
                            autovalidateMode:
                                AutovalidateMode.onUserInteraction,
                            onChanged: (value) {
                              // Update validation state for "Applied!" chip
                              setState(() {
                                _isReferralCodeValid =
                                    value.isNotEmpty &&
                                    InputValidators.validateReferralCode(
                                          value,
                                        ) ==
                                        null;
                              });
                            },
                          ),
                        ),
                        // "Applied!" confirmation chip when valid code entered
                        if (_isReferralCodeValid) ...[
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Semantics(
                                label: l10n.registerReferralAppliedA11y,
                                child: Chip(
                                  avatar: const Icon(
                                    Icons.check_circle,
                                    size: 16,
                                    color: _strongColor, // WCAG AA compliant
                                    semanticLabel: '', // Handled by parent
                                  ),
                                  label: ExcludeSemantics(
                                    child: Text(
                                      l10n.registerReferralApplied,
                                      style: const TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ),
                                  backgroundColor: Color(
                                    0xFFE8F5E9,
                                  ), // Green 50: soft bg
                                  side: const BorderSide(
                                    color: Color(
                                      0xFFA5D6A7,
                                    ), // Green 200: border
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ],
                        const SizedBox(height: 16),
                      ],

                      // ── Terms & Conditions ─────────────────────────
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          FocusTraversalOrder(
                            order: const NumericFocusOrder(5),
                            child: Semantics(
                              label: l10n.registerAcceptTermsA11y,
                              hint: l10n.registerAcceptTermsA11yHint,
                              child: SizedBox(
                                height: 24,
                                width: 24,
                                child: Checkbox(
                                  value: _acceptedTerms,
                                  onChanged: isLoading
                                      ? null
                                      : (v) => setState(
                                          () => _acceptedTerms = v ?? false,
                                        ),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: ExcludeSemantics(
                              child: RichText(
                                text: TextSpan(
                                  style: theme.textTheme.bodySmall?.copyWith(
                                    color: theme.colorScheme.onSurfaceVariant,
                                  ),
                                  children: [
                                    TextSpan(text: l10n.registerAgreePrefix),
                                    TextSpan(
                                      text: l10n.registerTermsAndConditions,
                                      style: TextStyle(
                                        color: theme.colorScheme.primary,
                                        fontWeight: FontWeight.w600,
                                      ),
                                      recognizer: TapGestureRecognizer()
                                        ..onTap = () {
                                          // TODO: open T&C page / URL
                                        },
                                    ),
                                    TextSpan(text: l10n.registerAndSeparator),
                                    TextSpan(
                                      text: l10n.privacyPolicy,
                                      style: TextStyle(
                                        color: theme.colorScheme.primary,
                                        fontWeight: FontWeight.w600,
                                      ),
                                      recognizer: TapGestureRecognizer()
                                        ..onTap = () {
                                          // TODO: open Privacy Policy page / URL
                                        },
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 24),

                      // ── Register button ────────────────────────────
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(6),
                        child: Semantics(
                          button: true,
                          enabled: !isLoading,
                          label: isLoading
                              ? l10n.registerCreatingAccount
                              : l10n.registerButton,
                          hint: l10n.registerHint,
                          child: SizedBox(
                            width: double.infinity,
                            height: 52,
                            child: ElevatedButton(
                              onPressed: isLoading ? null : _onSubmit,
                              child: isLoading
                                  ? const SizedBox(
                                      width: 24,
                                      height: 24,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2.5,
                                      ),
                                    )
                                  : ExcludeSemantics(
                                      child: Text(
                                        AppLocalizations.of(
                                          context,
                                        ).registerButton,
                                      ),
                                    ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 28),

                      // ── Divider ────────────────────────────────────
                      Row(
                        children: [
                          Expanded(
                            child: Divider(
                              color: theme.colorScheme.outlineVariant,
                            ),
                          ),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            child: Text(
                              l10n.registerOrSeparator,
                              style: theme.textTheme.bodySmall?.copyWith(
                                color: theme.colorScheme.onSurfaceVariant,
                              ),
                            ),
                          ),
                          Expanded(
                            child: Divider(
                              color: theme.colorScheme.outlineVariant,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 28),

                      // ── Social ─────────────────────────────────────
                      if (ref.watch(isTelegramLoginAvailableProvider))
                        SocialLoginButton.telegram(
                          onPressed: ref.watch(isTelegramAuthLoadingProvider)
                              ? null
                              : () {
                                  unawaited(
                                    ref
                                        .read(telegramAuthProvider.notifier)
                                        .startLogin(),
                                  );
                                },
                          isLoading: ref.watch(isTelegramAuthLoadingProvider),
                        ),
                      const SizedBox(height: 32),

                      // ── Login link ─────────────────────────────────
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            l10n.registerAlreadyHaveAccount,
                            style: theme.textTheme.bodyMedium,
                          ),
                          Semantics(
                            button: true,
                            label: l10n.registerLoginLink,
                            hint: l10n.registerLoginA11y,
                            child: GestureDetector(
                              onTap: () => context.go('/login'),
                              child: ExcludeSemantics(
                                child: Text(
                                  l10n.registerLoginLink,
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
        ),
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/di/providers.dart' show apiClientProvider;
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Screen for completing password reset with an OTP code.
///
/// Accepts an optional pre-filled [email] from the forgot-password flow.
/// The user enters the 6-digit OTP code and a new password to complete
/// the password reset.
class ResetPasswordScreen extends ConsumerStatefulWidget {
  const ResetPasswordScreen({super.key, this.email});

  /// Pre-filled email from the forgot-password screen.
  final String? email;

  @override
  ConsumerState<ResetPasswordScreen> createState() =>
      _ResetPasswordScreenState();
}

enum _ScreenState { initial, submitting, success, error, rateLimited }

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _emailController = TextEditingController();
  final _codeController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  _ScreenState _state = _ScreenState.initial;
  String? _errorMessage;
  int _rateLimitSeconds = 0;
  Timer? _rateLimitTimer;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  static const int _minPasswordLength = 12;

  @override
  void initState() {
    super.initState();
    if (widget.email != null && widget.email!.isNotEmpty) {
      _emailController.text = widget.email!;
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _codeController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _rateLimitTimer?.cancel();
    super.dispose();
  }

  Future<void> _submitResetPassword() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _state = _ScreenState.submitting;
      _errorMessage = null;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.post<Map<String, dynamic>>(
        ApiConstants.resetPassword,
        data: {
          'email': _emailController.text.trim(),
          'code': _codeController.text.trim(),
          'new_password': _passwordController.text,
        },
      );

      if (!mounted) return;
      setState(() {
        _state = _ScreenState.success;
      });
    } on ServerException catch (e) {
      AppLogger.error('Reset password failed', error: e, category: 'auth');
      if (!mounted) return;

      // Check for rate limiting (429)
      if (e.code == 429) {
        _startRateLimitCountdown(60);
        return;
      }

      setState(() {
        _state = _ScreenState.error;
        // Provide a more specific message for invalid/expired codes
        if (e.code == 400 || e.code == 422) {
          _errorMessage =
              AppLocalizations.of(context).resetPasswordInvalidCode;
        } else {
          _errorMessage = e.message;
        }
      });
    } on NetworkException catch (e) {
      AppLogger.error('Reset password failed (network)',
          error: e, category: 'auth');
      if (!mounted) return;
      setState(() {
        _state = _ScreenState.error;
        _errorMessage = e.message;
      });
    } catch (e) {
      AppLogger.error('Reset password failed (unknown)',
          error: e, category: 'auth');
      if (!mounted) return;
      setState(() {
        _state = _ScreenState.error;
        _errorMessage = e.toString();
      });
    }
  }

  void _startRateLimitCountdown(int seconds) {
    setState(() {
      _state = _ScreenState.rateLimited;
      _rateLimitSeconds = seconds;
    });
    _rateLimitTimer?.cancel();
    _rateLimitTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        _rateLimitSeconds--;
        if (_rateLimitSeconds <= 0) {
          timer.cancel();
          _state = _ScreenState.initial;
        }
      });
    });
  }

  void _resetState() {
    setState(() {
      _state = _ScreenState.initial;
      _errorMessage = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.resetPasswordTitle),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Spacing.lg),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 400),
            child: _buildBody(theme, l10n),
          ),
        ),
      ),
    );
  }

  Widget _buildBody(ThemeData theme, AppLocalizations l10n) {
    return switch (_state) {
      _ScreenState.success => _buildSuccessState(theme, l10n),
      _ScreenState.error => _buildErrorState(theme, l10n),
      _ScreenState.rateLimited => _buildRateLimitState(theme, l10n),
      _ => _buildFormState(theme, l10n),
    };
  }

  Widget _buildFormState(ThemeData theme, AppLocalizations l10n) {
    final isSubmitting = _state == _ScreenState.submitting;

    return Form(
      key: _formKey,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.lock_reset_outlined,
            size: 64,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(height: Spacing.lg),
          Text(
            l10n.resetPasswordTitle,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: Spacing.sm),
          Text(
            l10n.resetPasswordSubtitle,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.xl),

          // Email field
          TextFormField(
            controller: _emailController,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            enabled: !isSubmitting,
            decoration: InputDecoration(
              labelText: l10n.email,
              hintText: 'user@example.com',
              prefixIcon: const Icon(Icons.email_outlined),
            ),
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return l10n.errorFieldRequired;
              }
              if (!value.contains('@')) {
                return l10n.errorInvalidEmail;
              }
              return null;
            },
          ),
          const SizedBox(height: Spacing.md),

          // OTP code field
          TextFormField(
            controller: _codeController,
            keyboardType: TextInputType.number,
            enabled: !isSubmitting,
            maxLength: 6,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(6),
            ],
            decoration: InputDecoration(
              labelText: l10n.resetPasswordCodeLabel,
              hintText: l10n.resetPasswordCodeHint,
              prefixIcon: const Icon(Icons.pin_outlined),
              counterText: '',
            ),
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return l10n.errorFieldRequired;
              }
              if (value.trim().length != 6) {
                return l10n.resetPasswordInvalidCode;
              }
              return null;
            },
          ),
          const SizedBox(height: Spacing.md),

          // New password field
          TextFormField(
            controller: _passwordController,
            obscureText: _obscurePassword,
            enabled: !isSubmitting,
            autofillHints: const [AutofillHints.newPassword],
            decoration: InputDecoration(
              labelText: l10n.resetPasswordNewPassword,
              prefixIcon: const Icon(Icons.lock_outlined),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscurePassword
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
                onPressed: () {
                  setState(() {
                    _obscurePassword = !_obscurePassword;
                  });
                },
                tooltip: _obscurePassword
                    ? l10n.a11yShowPassword
                    : l10n.a11yHidePassword,
              ),
            ),
            validator: (value) {
              if (value == null || value.isEmpty) {
                return l10n.errorFieldRequired;
              }
              if (value.length < _minPasswordLength) {
                return l10n.resetPasswordPasswordTooShort;
              }
              return null;
            },
          ),
          const SizedBox(height: Spacing.md),

          // Confirm password field
          TextFormField(
            controller: _confirmPasswordController,
            obscureText: _obscureConfirmPassword,
            enabled: !isSubmitting,
            decoration: InputDecoration(
              labelText: l10n.resetPasswordConfirmPassword,
              prefixIcon: const Icon(Icons.lock_outlined),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscureConfirmPassword
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
                onPressed: () {
                  setState(() {
                    _obscureConfirmPassword = !_obscureConfirmPassword;
                  });
                },
                tooltip: _obscureConfirmPassword
                    ? l10n.a11yShowPassword
                    : l10n.a11yHidePassword,
              ),
            ),
            validator: (value) {
              if (value == null || value.isEmpty) {
                return l10n.errorFieldRequired;
              }
              if (value != _passwordController.text) {
                return l10n.resetPasswordPasswordMismatch;
              }
              return null;
            },
          ),
          const SizedBox(height: Spacing.lg),

          // Submit button
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: isSubmitting ? null : _submitResetPassword,
              child: isSubmitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        value: null,
                      ),
                    )
                  : Text(l10n.resetPasswordSubmit),
            ),
          ),
          const SizedBox(height: Spacing.md),
          TextButton(
            onPressed: () => context.go('/login'),
            child: Text(l10n.backToLogin),
          ),
        ],
      ),
    );
  }

  Widget _buildSuccessState(ThemeData theme, AppLocalizations l10n) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(
          Icons.check_circle_outline,
          size: 64,
          color: CyberColors.matrixGreen,
        ),
        const SizedBox(height: Spacing.lg),
        Text(
          l10n.resetPasswordSuccess,
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.resetPasswordSuccessMessage,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.xl),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: () => context.go('/login'),
            child: Text(l10n.resetPasswordGoToLogin),
          ),
        ),
      ],
    );
  }

  Widget _buildErrorState(ThemeData theme, AppLocalizations l10n) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          Icons.error_outline,
          size: 64,
          color: theme.colorScheme.error,
        ),
        const SizedBox(height: Spacing.lg),
        Text(
          l10n.errorOccurred,
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          _errorMessage ?? l10n.unknownError,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.xl),
        FilledButton(
          onPressed: _resetState,
          child: Text(l10n.retry),
        ),
        const SizedBox(height: Spacing.md),
        TextButton(
          onPressed: () => context.go('/login'),
          child: Text(l10n.backToLogin),
        ),
      ],
    );
  }

  Widget _buildRateLimitState(ThemeData theme, AppLocalizations l10n) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          Icons.hourglass_top,
          size: 64,
          color: theme.colorScheme.tertiary,
        ),
        const SizedBox(height: Spacing.lg),
        Text(
          l10n.rateLimitTitle,
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.rateLimitMessage(_rateLimitSeconds.toString()),
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.xl),
        TextButton(
          onPressed: () => context.go('/login'),
          child: Text(l10n.backToLogin),
        ),
      ],
    );
  }
}

import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/di/providers.dart' show apiClientProvider;
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Screen for changing user password.
///
/// Allows authenticated users to change their password by providing their
/// current password and a new password. Includes password strength validation
/// and rate limiting (3 requests per hour).
class ChangePasswordScreen extends ConsumerStatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  ConsumerState<ChangePasswordScreen> createState() =>
      _ChangePasswordScreenState();
}

enum _ScreenState { initial, submitting, success, error, rateLimited }

class _ChangePasswordScreenState extends ConsumerState<ChangePasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _currentPasswordController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  _ScreenState _state = _ScreenState.initial;
  String? _errorMessage;
  int _rateLimitSeconds = 0;
  Timer? _rateLimitTimer;

  bool _obscureCurrentPassword = true;
  bool _obscureNewPassword = true;
  bool _obscureConfirmPassword = true;

  static const int _minPasswordLength = 12;
  static const int _rateLimitDuration = 3600; // 1 hour in seconds

  @override
  void dispose() {
    _currentPasswordController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    _rateLimitTimer?.cancel();
    super.dispose();
  }

  Future<void> _submitPasswordChange() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _state = _ScreenState.submitting;
      _errorMessage = null;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.post<Map<String, dynamic>>(
        ApiConstants.changePassword,
        data: {
          'current_password': _currentPasswordController.text,
          'new_password': _newPasswordController.text,
        },
      );

      if (!mounted) return;
      setState(() {
        _state = _ScreenState.success;
      });
    } on ServerException catch (e) {
      AppLogger.error('Password change failed', error: e, category: 'profile');
      if (!mounted) return;

      // Check for rate limiting (429)
      if (e.code == 429) {
        _startRateLimitCountdown(_rateLimitDuration);
        return;
      }

      setState(() {
        _state = _ScreenState.error;
        // Provide specific error messages
        if (e.code == 400) {
          _errorMessage =
              AppLocalizations.of(context).changePasswordInvalidPassword;
        } else if (e.code == 401) {
          _errorMessage =
              AppLocalizations.of(context).changePasswordCurrentWrong;
        } else if (e.message.toLowerCase().contains('oauth')) {
          _errorMessage =
              AppLocalizations.of(context).changePasswordOAuthOnly;
        } else {
          _errorMessage = e.message;
        }
      });
    } on NetworkException catch (e) {
      AppLogger.error('Password change failed (network)',
          error: e, category: 'profile');
      if (!mounted) return;
      setState(() {
        _state = _ScreenState.error;
        _errorMessage = e.message;
      });
    } catch (e) {
      AppLogger.error('Password change failed (unknown)',
          error: e, category: 'profile');
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

  int _passwordStrength(String password) {
    if (password.isEmpty) return 0;
    int score = 0;
    if (password.length >= 12) score++;
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

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.changePassword),
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
    final strength = _passwordStrength(_newPasswordController.text);

    return Form(
      key: _formKey,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.lock_reset,
            size: 64,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(height: Spacing.lg),
          Text(
            l10n.changePassword,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: Spacing.sm),
          Text(
            l10n.changePasswordSubtitle,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: Spacing.xl),

          // Current password field
          TextFormField(
            controller: _currentPasswordController,
            obscureText: _obscureCurrentPassword,
            enabled: !isSubmitting,
            decoration: InputDecoration(
              labelText: l10n.changePasswordCurrent,
              prefixIcon: const Icon(Icons.lock_outline),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscureCurrentPassword
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
                onPressed: () {
                  setState(() {
                    _obscureCurrentPassword = !_obscureCurrentPassword;
                  });
                },
              ),
            ),
            validator: (value) {
              if (value == null || value.isEmpty) {
                return l10n.errorFieldRequired;
              }
              return null;
            },
          ),
          const SizedBox(height: Spacing.md),

          // New password field
          TextFormField(
            controller: _newPasswordController,
            obscureText: _obscureNewPassword,
            enabled: !isSubmitting,
            onChanged: (_) => setState(() {}), // Rebuild for strength indicator
            decoration: InputDecoration(
              labelText: l10n.changePasswordNew,
              prefixIcon: const Icon(Icons.lock),
              suffixIcon: IconButton(
                icon: Icon(
                  _obscureNewPassword
                      ? Icons.visibility_outlined
                      : Icons.visibility_off_outlined,
                ),
                onPressed: () {
                  setState(() {
                    _obscureNewPassword = !_obscureNewPassword;
                  });
                },
              ),
            ),
            validator: (value) {
              if (value == null || value.isEmpty) {
                return l10n.errorFieldRequired;
              }
              if (value.length < _minPasswordLength) {
                return l10n.changePasswordTooShort;
              }
              if (value == _currentPasswordController.text) {
                return l10n.changePasswordSameAsOld;
              }
              return null;
            },
          ),
          if (_newPasswordController.text.isNotEmpty) ...[
            const SizedBox(height: Spacing.sm),
            _buildPasswordStrengthIndicator(strength, theme, l10n),
          ],
          const SizedBox(height: Spacing.md),

          // Confirm password field
          TextFormField(
            controller: _confirmPasswordController,
            obscureText: _obscureConfirmPassword,
            enabled: !isSubmitting,
            decoration: InputDecoration(
              labelText: l10n.changePasswordConfirm,
              prefixIcon: const Icon(Icons.lock_outline),
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
              ),
            ),
            validator: (value) {
              if (value == null || value.isEmpty) {
                return l10n.errorFieldRequired;
              }
              if (value != _newPasswordController.text) {
                return l10n.changePasswordMismatch;
              }
              return null;
            },
          ),
          const SizedBox(height: Spacing.lg),

          // Submit button
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: isSubmitting ? null : _submitPasswordChange,
              child: isSubmitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        value: null,
                      ),
                    )
                  : Text(l10n.changePasswordSubmit),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPasswordStrengthIndicator(
    int strength,
    ThemeData theme,
    AppLocalizations l10n,
  ) {
    final colors = [
      theme.colorScheme.error,
      Colors.orange,
      CyberColors.matrixGreen,
    ];
    final labels = [
      l10n.changePasswordStrengthWeak,
      l10n.changePasswordStrengthMedium,
      l10n.changePasswordStrengthStrong,
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: List.generate(3, (index) {
            return Expanded(
              child: Container(
                height: 4,
                margin: EdgeInsets.only(right: index < 2 ? 4 : 0),
                decoration: BoxDecoration(
                  color: index < strength
                      ? colors[strength - 1]
                      : theme.colorScheme.surfaceContainerHighest,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            );
          }),
        ),
        if (strength > 0) ...[
          const SizedBox(height: Spacing.xs),
          Text(
            labels[strength - 1],
            style: theme.textTheme.bodySmall?.copyWith(
              color: colors[strength - 1],
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ],
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
          l10n.changePasswordSuccess,
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.changePasswordSuccessMessage,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.xl),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: () => context.pop(),
            child: Text(l10n.close),
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
          textAlign: TextAlign.center,
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
          onPressed: () => context.pop(),
          child: Text(l10n.cancel),
        ),
      ],
    );
  }

  Widget _buildRateLimitState(ThemeData theme, AppLocalizations l10n) {
    final minutes = (_rateLimitSeconds / 60).ceil();

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
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.changePasswordRateLimit(minutes.toString()),
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.xl),
        TextButton(
          onPressed: () => context.pop(),
          child: Text(l10n.close),
        ),
      ],
    );
  }
}

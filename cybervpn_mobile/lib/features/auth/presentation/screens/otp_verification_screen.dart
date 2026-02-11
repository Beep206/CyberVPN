import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/di/providers.dart' show apiClientProvider, secureStorageProvider;
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/auth_provider.dart';

/// Screen for verifying email address with a 6-digit OTP code after registration.
///
/// Accepts a required [email] from the registration flow. The user enters
/// the 6-digit OTP code to verify their email. On success, the user is
/// automatically logged in.
class OtpVerificationScreen extends ConsumerStatefulWidget {
  const OtpVerificationScreen({super.key, required this.email});

  /// Email address that needs to be verified.
  final String email;

  @override
  ConsumerState<OtpVerificationScreen> createState() =>
      _OtpVerificationScreenState();
}

enum _ScreenState { initial, submitting, resending, success, error, rateLimited }

class _OtpVerificationScreenState
    extends ConsumerState<OtpVerificationScreen> {
  final _codeController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  _ScreenState _state = _ScreenState.initial;
  String? _errorMessage;
  int _rateLimitSeconds = 0;
  Timer? _rateLimitTimer;
  int _resendCooldownSeconds = 0;
  Timer? _resendCooldownTimer;

  static const int _resendCooldownDuration = 60; // 60 seconds cooldown

  @override
  void dispose() {
    _codeController.dispose();
    _rateLimitTimer?.cancel();
    _resendCooldownTimer?.cancel();
    super.dispose();
  }

  Future<void> _submitVerification() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _state = _ScreenState.submitting;
      _errorMessage = null;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.post<Map<String, dynamic>>(
        ApiConstants.verifyEmail,
        data: {
          'email': widget.email,
          'code': _codeController.text.trim(),
        },
      );

      if (!mounted) return;

      // Extract tokens from response and store them
      final data = response.data;
      if (data != null &&
          data['access_token'] != null &&
          data['refresh_token'] != null) {
        final storage = ref.read(secureStorageProvider);
        await storage.setTokens(
          accessToken: data['access_token'] as String,
          refreshToken: data['refresh_token'] as String,
        );

        // Trigger auth state refresh to load the authenticated user
        await ref.read(authProvider.notifier).checkAuthStatus();

        if (!mounted) return;
        setState(() {
          _state = _ScreenState.success;
        });
      } else {
        throw const ServerException(
          message: 'Invalid response from server',
          code: 500,
        );
      }
    } on ServerException catch (e) {
      AppLogger.error('OTP verification failed', error: e, category: 'auth');
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
              AppLocalizations.of(context).otpVerificationInvalidCode;
        } else {
          _errorMessage = e.message;
        }
      });
    } on NetworkException catch (e) {
      AppLogger.error('OTP verification failed (network)',
          error: e, category: 'auth');
      if (!mounted) return;
      setState(() {
        _state = _ScreenState.error;
        _errorMessage = e.message;
      });
    } catch (e) {
      AppLogger.error('OTP verification failed (unknown)',
          error: e, category: 'auth');
      if (!mounted) return;
      setState(() {
        _state = _ScreenState.error;
        _errorMessage = e.toString();
      });
    }
  }

  Future<void> _resendOtp() async {
    if (_resendCooldownSeconds > 0) return;

    setState(() {
      _state = _ScreenState.resending;
      _errorMessage = null;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.post<Map<String, dynamic>>(
        ApiConstants.resendOtp,
        data: {
          'email': widget.email,
        },
      );

      if (!mounted) return;

      setState(() {
        _state = _ScreenState.initial;
      });

      // Start cooldown timer
      _startResendCooldown();

      // Show success message
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).otpVerificationResendSuccess),
          backgroundColor: CyberColors.matrixGreen,
        ),
      );
    } on ServerException catch (e) {
      AppLogger.error('OTP resend failed', error: e, category: 'auth');
      if (!mounted) return;

      // Check for rate limiting (429)
      if (e.code == 429) {
        _startRateLimitCountdown(60);
        return;
      }

      setState(() {
        _state = _ScreenState.error;
        _errorMessage = e.message;
      });
    } on NetworkException catch (e) {
      AppLogger.error('OTP resend failed (network)', error: e, category: 'auth');
      if (!mounted) return;
      setState(() {
        _state = _ScreenState.error;
        _errorMessage = e.message;
      });
    } catch (e) {
      AppLogger.error('OTP resend failed (unknown)', error: e, category: 'auth');
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

  void _startResendCooldown() {
    setState(() {
      _resendCooldownSeconds = _resendCooldownDuration;
    });
    _resendCooldownTimer?.cancel();
    _resendCooldownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) {
        timer.cancel();
        return;
      }
      setState(() {
        _resendCooldownSeconds--;
        if (_resendCooldownSeconds <= 0) {
          timer.cancel();
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
        title: Text(l10n.otpVerificationTitle),
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
    final isResending = _state == _ScreenState.resending;
    final isDisabled = isSubmitting || isResending;

    return Form(
      key: _formKey,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.mark_email_unread_outlined,
            size: 64,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(height: Spacing.lg),
          Text(
            l10n.otpVerificationTitle,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.sm),
          Text(
            l10n.otpVerificationSubtitle(widget.email),
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.xl),

          // OTP code field
          TextFormField(
            controller: _codeController,
            keyboardType: TextInputType.number,
            enabled: !isDisabled,
            maxLength: 6,
            autofocus: true,
            textAlign: TextAlign.center,
            style: theme.textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.bold,
              letterSpacing: 8,
            ),
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(6),
            ],
            decoration: InputDecoration(
              labelText: l10n.otpVerificationCodeLabel,
              hintText: l10n.otpVerificationCodeHint,
              prefixIcon: const Icon(Icons.pin_outlined),
              counterText: '',
            ),
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return l10n.errorFieldRequired;
              }
              if (value.trim().length != 6) {
                return l10n.otpVerificationInvalidCode;
              }
              return null;
            },
            onFieldSubmitted: (_) => _submitVerification(),
          ),
          const SizedBox(height: Spacing.lg),

          // Submit button
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: isDisabled ? null : _submitVerification,
              child: isSubmitting
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        value: null,
                      ),
                    )
                  : Text(l10n.otpVerificationSubmit),
            ),
          ),
          const SizedBox(height: Spacing.md),

          // Resend button with cooldown
          if (_resendCooldownSeconds > 0)
            TextButton(
              onPressed: null,
              child: Text(
                l10n.otpVerificationResendCooldown(_resendCooldownSeconds.toString()),
              ),
            )
          else
            TextButton(
              onPressed: isDisabled ? null : _resendOtp,
              child: isResending
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        value: null,
                      ),
                    )
                  : Text(l10n.otpVerificationResend),
            ),

          const SizedBox(height: Spacing.sm),
          TextButton(
            onPressed: isDisabled ? null : () => context.go('/login'),
            child: Text(l10n.backToLogin),
          ),
        ],
      ),
    );
  }

  Widget _buildSuccessState(ThemeData theme, AppLocalizations l10n) {
    // After a brief delay, navigate to the connection screen
    // The auth provider will handle the navigation through its redirect logic
    Future.delayed(const Duration(milliseconds: 1500), () {
      if (mounted) {
        context.go('/connection');
      }
    });

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
          l10n.otpVerificationSuccess,
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.otpVerificationSuccessMessage,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.xl),
        const CircularProgressIndicator(),
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
          textAlign: TextAlign.center,
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

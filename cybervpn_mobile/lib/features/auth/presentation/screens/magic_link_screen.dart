import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/di/providers.dart' show apiClientProvider;
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';

/// Screen for requesting a magic link for passwordless login.
///
/// Allows the user to enter their email and request a single-use login link.
/// The link is sent to their email and handled by the deep link system
/// when tapped.
class MagicLinkScreen extends ConsumerStatefulWidget {
  const MagicLinkScreen({super.key});

  @override
  ConsumerState<MagicLinkScreen> createState() => _MagicLinkScreenState();
}

enum _ScreenState { initial, sending, success, error, rateLimited }

class _MagicLinkScreenState extends ConsumerState<MagicLinkScreen> {
  final _emailController = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  _ScreenState _state = _ScreenState.initial;
  String? _errorMessage;
  int _rateLimitSeconds = 0;
  Timer? _rateLimitTimer;

  @override
  void dispose() {
    _emailController.dispose();
    _rateLimitTimer?.cancel();
    super.dispose();
  }

  Future<void> _requestMagicLink() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _state = _ScreenState.sending;
      _errorMessage = null;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      await apiClient.post<Map<String, dynamic>>(
        '/api/v1/auth/magic-link/request',
        data: {'email': _emailController.text.trim()},
      );

      if (!mounted) return;
      setState(() {
        _state = _ScreenState.success;
      });
    } on ServerException catch (e) {
      AppLogger.error('Magic link request failed', error: e, category: 'auth');
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
      AppLogger.error('Magic link request failed (network)', error: e, category: 'auth');
      if (!mounted) return;
      setState(() {
        _state = _ScreenState.error;
        _errorMessage = e.message;
      });
    } catch (e) {
      AppLogger.error('Magic link request failed (unknown)', error: e, category: 'auth');
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
        title: Text(l10n.magicLinkTitle),
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
    final isSending = _state == _ScreenState.sending;

    return Form(
      key: _formKey,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.mail_outline,
            size: 64,
            color: theme.colorScheme.primary,
          ),
          const SizedBox(height: Spacing.lg),
          Text(
            l10n.magicLinkTitle,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: Spacing.sm),
          Text(
            l10n.magicLinkSubtitle,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.xl),
          TextFormField(
            controller: _emailController,
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            autofocus: true,
            enabled: !isSending,
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
          const SizedBox(height: Spacing.lg),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: isSending ? null : _requestMagicLink,
              child: isSending
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        value: null,
                      ),
                    )
                  : Text(l10n.magicLinkSendButton),
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
          Icons.mark_email_read_outlined,
          size: 64,
          color: CyberColors.matrixGreen,
        ),
        const SizedBox(height: Spacing.lg),
        Text(
          l10n.magicLinkCheckInbox,
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.magicLinkSentTo(_emailController.text.trim()),
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.magicLinkExpiresIn,
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Spacing.xl),
        OutlinedButton(
          onPressed: _resetState,
          child: Text(l10n.magicLinkSendAgain),
        ),
        const SizedBox(height: Spacing.md),
        TextButton(
          onPressed: () => context.go('/login'),
          child: Text(l10n.backToLogin),
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

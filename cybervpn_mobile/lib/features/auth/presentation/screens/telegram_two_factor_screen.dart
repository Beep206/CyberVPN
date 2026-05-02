import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/services/telegram_auth_service.dart';
import 'package:cybervpn_mobile/features/auth/presentation/providers/telegram_auth_provider.dart';

/// Completes a Telegram login that is paused behind TOTP verification.
class TelegramTwoFactorScreen extends ConsumerStatefulWidget {
  const TelegramTwoFactorScreen({super.key});

  @override
  ConsumerState<TelegramTwoFactorScreen> createState() =>
      _TelegramTwoFactorScreenState();
}

class _TelegramTwoFactorScreenState
    extends ConsumerState<TelegramTwoFactorScreen> {
  final TextEditingController _codeController = TextEditingController();
  final FocusNode _codeFocusNode = FocusNode();

  @override
  void dispose() {
    _codeController.dispose();
    _codeFocusNode.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final code = _codeController.text.trim();
    if (code.length != 6) {
      return;
    }

    try {
      await ref.read(telegramAuthProvider.notifier).completeTwoFactor(code);
    } on TelegramAuthException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.message),
          backgroundColor: Theme.of(context).colorScheme.error,
          behavior: SnackBarBehavior.floating,
        ),
      );
      _codeFocusNode.requestFocus();
      _codeController.selection = TextSelection(
        baseOffset: 0,
        extentOffset: _codeController.text.length,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final telegramState = ref.watch(telegramAuthProvider).value;
    final isLoading = telegramState is TelegramAuthCompletingTwoFactor;
    final requiresTwoFactor =
        telegramState is TelegramAuthRequiresTwoFactor ||
        telegramState is TelegramAuthCompletingTwoFactor;

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.profileTwoFactorAuth),
        leading: IconButton(
          onPressed: isLoading
              ? null
              : () {
                  ref.read(telegramAuthProvider.notifier).cancel();
                  context.pop();
                },
          icon: const Icon(Icons.arrow_back),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(Spacing.lg),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Icon(
                    Icons.lock_outline,
                    size: 56,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(height: Spacing.md),
                  Text(
                    l10n.profileTwoFactorEnterCode,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: Spacing.sm),
                  Text(
                    requiresTwoFactor
                        ? l10n.profileTwoFactorEnterCodeShort
                        : l10n.errorTelegramAuthFailed,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: Spacing.xl),
                  TextField(
                    controller: _codeController,
                    focusNode: _codeFocusNode,
                    enabled: !isLoading && requiresTwoFactor,
                    keyboardType: TextInputType.number,
                    textInputAction: TextInputAction.done,
                    maxLength: 6,
                    autofocus: true,
                    inputFormatters: [
                      FilteringTextInputFormatter.digitsOnly,
                      LengthLimitingTextInputFormatter(6),
                    ],
                    onSubmitted: (_) => _submit(),
                    decoration: InputDecoration(
                      labelText: l10n.profileTwoFactorCodeLabel,
                      hintText: '123456',
                      counterText: '',
                    ),
                  ),
                  const SizedBox(height: Spacing.lg),
                  FilledButton(
                    onPressed: isLoading || !requiresTwoFactor ? null : _submit,
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                    ),
                    child: isLoading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text(l10n.commonContinue),
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

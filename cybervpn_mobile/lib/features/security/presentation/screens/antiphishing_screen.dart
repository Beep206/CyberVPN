import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/security/domain/entities/antiphishing_code.dart';
import 'package:cybervpn_mobile/features/security/presentation/providers/antiphishing_provider.dart';

/// Screen for managing the user's antiphishing code.
///
/// Displays the user's current code (masked) and provides options to:
/// - Set a new code (if not set)
/// - Edit the existing code
/// - Delete the code
///
/// The antiphishing code is shown in official CyberVPN emails to help users
/// verify that emails are legitimate and not phishing attempts.
class AntiphishingScreen extends ConsumerStatefulWidget {
  const AntiphishingScreen({super.key});

  @override
  ConsumerState<AntiphishingScreen> createState() =>
      _AntiphishingScreenState();
}

enum _ScreenMode { view, edit }

class _AntiphishingScreenState extends ConsumerState<AntiphishingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _codeController = TextEditingController();

  _ScreenMode _mode = _ScreenMode.view;
  bool _isLoading = false;
  String? _errorMessage;

  static const int _maxCodeLength = 50;

  @override
  void dispose() {
    _codeController.dispose();
    super.dispose();
  }

  Future<void> _saveCode() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final repository = ref.read(securityRepositoryProvider);
      final result = await repository.setAntiphishingCode(
        _codeController.text.trim(),
      );

      if (!mounted) return;

      result.when(
        success: (_) {
          ref.invalidate(antiphishingCodeProvider);
          setState(() {
            _mode = _ScreenMode.view;
            _isLoading = false;
          });
          _codeController.clear();
        },
        failure: (AppFailure failure) {
          AppLogger.error('Failed to save antiphishing code',
              error: failure, category: 'security');
          setState(() {
            _isLoading = false;
            _errorMessage = failure.message;
          });
        },
      );
    } catch (e) {
      AppLogger.error('Unexpected error saving antiphishing code',
          error: e, category: 'security');
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.toString();
      });
    }
  }

  Future<void> _deleteCode() async {
    final l10n = AppLocalizations.of(context);

    // Show confirmation dialog
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(l10n.antiphishingDeleteConfirmTitle),
        content: Text(l10n.antiphishingDeleteConfirmMessage),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(l10n.cancel),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            child: Text(l10n.delete),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final repository = ref.read(securityRepositoryProvider);
      final result = await repository.deleteAntiphishingCode();

      if (!mounted) return;

      result.when(
        success: (_) {
          ref.invalidate(antiphishingCodeProvider);
          setState(() {
            _isLoading = false;
          });
        },
        failure: (AppFailure failure) {
          AppLogger.error('Failed to delete antiphishing code',
              error: failure, category: 'security');
          setState(() {
            _isLoading = false;
            _errorMessage = failure.message;
          });
        },
      );
    } catch (e) {
      AppLogger.error('Unexpected error deleting antiphishing code',
          error: e, category: 'security');
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.toString();
      });
    }
  }

  void _enterEditMode(String? currentCode) {
    setState(() {
      _mode = _ScreenMode.edit;
      _errorMessage = null;
      if (currentCode != null) {
        _codeController.text = currentCode;
      }
    });
  }

  void _cancelEdit() {
    setState(() {
      _mode = _ScreenMode.view;
      _errorMessage = null;
      _codeController.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final codeAsync = ref.watch(antiphishingCodeProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.antiphishingTitle),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Spacing.lg),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 400),
            child: codeAsync.when(
              data: (code) => _buildContent(theme, l10n, code),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (error, _) => _buildErrorState(theme, l10n, error),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildContent(
    ThemeData theme,
    AppLocalizations l10n,
    AntiphishingCode code,
  ) {
    if (_mode == _ScreenMode.edit) {
      return _buildEditMode(theme, l10n, code);
    }

    if (!code.isSet) {
      return _buildNotSetState(theme, l10n);
    }

    return _buildViewMode(theme, l10n, code);
  }

  Widget _buildNotSetState(ThemeData theme, AppLocalizations l10n) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(
          Icons.security_outlined,
          size: 64,
        ),
        const SizedBox(height: Spacing.lg),
        Text(
          l10n.antiphishingNotSetTitle,
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.antiphishingNotSetMessage,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.xl),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: _isLoading ? null : () => _enterEditMode(null),
            icon: const Icon(Icons.add),
            label: Text(l10n.antiphishingSetCode),
          ),
        ),
      ],
    );
  }

  Widget _buildViewMode(
    ThemeData theme,
    AppLocalizations l10n,
    AntiphishingCode code,
  ) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Icon(
          Icons.verified_user,
          size: 64,
          color: CyberColors.matrixGreen,
        ),
        const SizedBox(height: Spacing.lg),
        Text(
          l10n.antiphishingTitle,
          style: theme.textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.antiphishingDescription,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Spacing.xl),

        // Masked code display
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(Spacing.lg),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: theme.colorScheme.outline.withValues(alpha: 0.2),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.antiphishingCurrentCode,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: Spacing.xs),
              Text(
                code.maskedCode,
                style: theme.textTheme.headlineMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                  letterSpacing: 4,
                  color: CyberColors.matrixGreen,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: Spacing.xl),

        // Action buttons
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: _isLoading ? null : () => _enterEditMode(code.code),
            icon: const Icon(Icons.edit),
            label: Text(l10n.antiphishingEditCode),
          ),
        ),
        const SizedBox(height: Spacing.md),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton.icon(
            onPressed: _isLoading ? null : _deleteCode,
            icon: Icon(
              Icons.delete_outline,
              color: theme.colorScheme.error,
            ),
            style: OutlinedButton.styleFrom(
              foregroundColor: theme.colorScheme.error,
              side: BorderSide(color: theme.colorScheme.error),
            ),
            label: Text(l10n.antiphishingDeleteCode),
          ),
        ),
      ],
    );
  }

  Widget _buildEditMode(
    ThemeData theme,
    AppLocalizations l10n,
    AntiphishingCode code,
  ) {
    return Form(
      key: _formKey,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.edit_outlined,
            size: 64,
          ),
          const SizedBox(height: Spacing.lg),
          Text(
            code.isSet ? l10n.antiphishingEditCode : l10n.antiphishingSetCode,
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: Spacing.sm),
          Text(
            l10n.antiphishingEditDescription,
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: Spacing.xl),

          // Code input field
          TextFormField(
            controller: _codeController,
            enabled: !_isLoading,
            maxLength: _maxCodeLength,
            decoration: InputDecoration(
              labelText: l10n.antiphishingCodeLabel,
              hintText: l10n.antiphishingCodeHint,
              prefixIcon: const Icon(Icons.shield_outlined),
              helperText: l10n.antiphishingCodeHelper,
            ),
            validator: (value) {
              if (value == null || value.trim().isEmpty) {
                return l10n.errorFieldRequired;
              }
              if (value.trim().length > _maxCodeLength) {
                return l10n.antiphishingCodeTooLong;
              }
              return null;
            },
          ),
          if (_errorMessage != null) ...[
            const SizedBox(height: Spacing.md),
            Container(
              padding: const EdgeInsets.all(Spacing.md),
              decoration: BoxDecoration(
                color: theme.colorScheme.errorContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  Icon(
                    Icons.error_outline,
                    color: theme.colorScheme.error,
                    size: 20,
                  ),
                  const SizedBox(width: Spacing.sm),
                  Expanded(
                    child: Text(
                      _errorMessage!,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onErrorContainer,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
          const SizedBox(height: Spacing.xl),

          // Action buttons
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              onPressed: _isLoading ? null : _saveCode,
              child: _isLoading
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                      ),
                    )
                  : Text(l10n.save),
            ),
          ),
          const SizedBox(height: Spacing.md),
          SizedBox(
            width: double.infinity,
            child: TextButton(
              onPressed: _isLoading ? null : _cancelEdit,
              child: Text(l10n.cancel),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState(
    ThemeData theme,
    AppLocalizations l10n,
    Object? error,
  ) {
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
          l10n.antiphishingLoadError,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: Spacing.xl),
        FilledButton.icon(
          onPressed: () {
            ref.invalidate(antiphishingCodeProvider);
          },
          icon: const Icon(Icons.refresh),
          label: Text(l10n.retry),
        ),
        const SizedBox(height: Spacing.md),
        TextButton(
          onPressed: () => context.pop(),
          child: Text(l10n.close),
        ),
      ],
    );
  }
}

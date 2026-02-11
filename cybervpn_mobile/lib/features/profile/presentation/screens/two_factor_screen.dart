import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:math';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/security/screen_protection.dart';
import 'package:cybervpn_mobile/features/profile/domain/entities/setup_2fa_result.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';

// ---------------------------------------------------------------------------
// TwoFactorScreen
// ---------------------------------------------------------------------------

/// Two-factor authentication management screen
///
/// Provides functionality to enable, verify, and disable 2FA on the account.
/// Uses screen protection to prevent screenshots of sensitive 2FA data.
///
/// States:
/// - Not enabled: Shows information and Enable button
/// - Setup: Displays QR code and verification code input
/// - Enabled: Shows current status and Disable button
class TwoFactorScreen extends ConsumerStatefulWidget {
  const TwoFactorScreen({super.key});

  @override
  ConsumerState<TwoFactorScreen> createState() => _TwoFactorScreenState();
}

class _TwoFactorScreenState extends ConsumerState<TwoFactorScreen>
    with ScreenProtection {
  /// Current state of the 2FA flow
  TwoFactorState _currentState = TwoFactorState.notEnabled;

  /// Result from 2FA setup containing QR code URI and secret
  Setup2FAResult? _setup2FAResult;

  /// Backup codes shown after successful verification (shown only once)
  List<String>? _backupCodes;

  /// Controller for the 6-digit verification code input
  final TextEditingController _codeController = TextEditingController();

  /// Loading state for async operations
  bool _isLoading = false;

  // ---- Lifecycle -----------------------------------------------------------

  @override
  void initState() {
    super.initState();
    unawaited(enableProtection());
    _initializeState();
  }

  @override
  void dispose() {
    unawaited(disableProtection());
    _codeController.dispose();
    super.dispose();
  }

  /// Initialize the screen state based on current 2FA status
  void _initializeState() {
    final is2FAEnabled = ref.read(is2FAEnabledProvider);
    setState(() {
      _currentState =
          is2FAEnabled ? TwoFactorState.enabled : TwoFactorState.notEnabled;
    });
  }

  // ---- Build ---------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        title: Text(l10n.profileTwoFactorAuth),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Spacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Status header
              _buildStatusHeader(theme, l10n),
              const SizedBox(height: Spacing.lg),

              // Conditional content based on state
              if (_currentState == TwoFactorState.notEnabled)
                _buildNotEnabledView(theme, l10n),
              if (_currentState == TwoFactorState.setup) _buildSetupView(theme, l10n),
              if (_currentState == TwoFactorState.enabled)
                _buildEnabledView(theme, l10n),

              // Loading indicator
              if (_isLoading) ...[
                const SizedBox(height: Spacing.md),
                const Center(child: CircularProgressIndicator()),
              ],
            ],
          ),
        ),
      ),
    );
  }

  // ---- Status Header -------------------------------------------------------

  Widget _buildStatusHeader(ThemeData theme, AppLocalizations l10n) {
    final colorScheme = theme.colorScheme;
    final isEnabled = _currentState == TwoFactorState.enabled;

    return Container(
      padding: const EdgeInsets.all(Spacing.md),
      decoration: BoxDecoration(
        color: (isEnabled ? CyberColors.matrixGreen : colorScheme.error)
            .withAlpha(25),
        borderRadius: BorderRadius.circular(Radii.md),
        border: Border.all(
          color: isEnabled ? CyberColors.matrixGreen : colorScheme.error,
          width: 1.5,
        ),
      ),
      child: Row(
        children: [
          Icon(
            isEnabled ? Icons.verified_user : Icons.security,
            color: isEnabled ? CyberColors.matrixGreen : colorScheme.error,
            size: 32,
          ),
          const SizedBox(width: Spacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  isEnabled ? l10n.profileTwoFactorEnabled : l10n.profileTwoFactorDisabledStatus,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color:
                        isEnabled ? CyberColors.matrixGreen : colorScheme.error,
                  ),
                ),
                const SizedBox(height: Spacing.xs),
                Text(
                  isEnabled
                      ? l10n.profileTwoFactorProtected
                      : l10n.profileTwoFactorEnablePrompt,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ---- Not Enabled View ----------------------------------------------------

  Widget _buildNotEnabledView(ThemeData theme, AppLocalizations l10n) {
    final colorScheme = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.profileTwoFactorWhatIs,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.profileTwoFactorFullDescription,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Spacing.md),

        // Benefits list
        _buildBenefitItem(
          icon: Icons.shield_outlined,
          title: l10n.profileTwoFactorEnhancedSecurity,
          description: l10n.profileTwoFactorEnhancedSecurityDesc,
          theme: theme,
        ),
        const SizedBox(height: Spacing.sm),
        _buildBenefitItem(
          icon: Icons.phone_android_outlined,
          title: l10n.profileTwoFactorAuthenticatorApp,
          description: l10n.profileTwoFactorAuthenticatorAppDesc,
          theme: theme,
        ),
        const SizedBox(height: Spacing.sm),
        _buildBenefitItem(
          icon: Icons.backup_outlined,
          title: l10n.profileTwoFactorBackupCodes,
          description: l10n.profileTwoFactorBackupCodesDesc,
          theme: theme,
        ),
        const SizedBox(height: Spacing.lg),

        // Enable button
        FilledButton(
          onPressed: _isLoading ? null : _handleEnablePress,
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          child: Text(l10n.profileTwoFactorEnable),
        ),
      ],
    );
  }

  Widget _buildBenefitItem({
    required IconData icon,
    required String title,
    required String description,
    required ThemeData theme,
  }) {
    final colorScheme = theme.colorScheme;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          padding: const EdgeInsets.all(Spacing.sm),
          decoration: BoxDecoration(
            color: CyberColors.matrixGreen.withAlpha(25),
            borderRadius: BorderRadius.circular(Radii.sm),
          ),
          child: Icon(
            icon,
            size: 20,
            color: CyberColors.matrixGreen,
          ),
        ),
        const SizedBox(width: Spacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: theme.textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                description,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  // ---- Setup View ----------------------------------------------------------

  Widget _buildSetupView(ThemeData theme, AppLocalizations l10n) {
    final colorScheme = theme.colorScheme;
    final setup = _setup2FAResult;

    if (setup == null) {
      return Center(child: Text(l10n.profileTwoFactorFailedSetupData));
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.profileTwoFactorStep1,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.profileTwoFactorScanQrShort,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Spacing.md),

        // QR Code
        Center(
          child: Container(
            padding: const EdgeInsets.all(Spacing.md),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(Radii.md),
            ),
            child: QrImageView(
              data: setup.qrCodeUri,
              version: QrVersions.auto,
              size: 200,
              backgroundColor: Colors.white,
            ),
          ),
        ),
        const SizedBox(height: Spacing.md),

        // Manual entry option
        ExpansionTile(
          title: Text(l10n.profileTwoFactorEnterManually),
          children: [
            Padding(
              padding: const EdgeInsets.all(Spacing.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l10n.profileTwoFactorSecretKey,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: Spacing.xs),
                  Container(
                    padding: const EdgeInsets.all(Spacing.sm),
                    decoration: BoxDecoration(
                      color: colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(Radii.sm),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            setup.secret,
                            style: theme.textTheme.bodyMedium?.copyWith(
                              fontFamily: 'monospace',
                            ),
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.copy),
                          tooltip: l10n.commonCopy,
                          onPressed: () => _copyToClipboard(setup.secret),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: Spacing.lg),

        // Step 2: Verify code
        Text(
          l10n.profileTwoFactorStep2,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.profileTwoFactorEnterCodeShort,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Spacing.md),

        // Code input field
        TextField(
          controller: _codeController,
          keyboardType: TextInputType.number,
          maxLength: 6,
          decoration: InputDecoration(
            labelText: l10n.profileTwoFactorCodeLabel,
            hintText: '000000',
            prefixIcon: const Icon(Icons.lock_outline),
            counterText: '',
          ),
          inputFormatters: [
            FilteringTextInputFormatter.digitsOnly,
            LengthLimitingTextInputFormatter(6),
          ],
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: Spacing.md),

        // Verify button
        FilledButton(
          onPressed: _canVerify && !_isLoading ? _handleVerifyPress : null,
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          child: Text(l10n.profileTwoFactorVerifyAndEnable),
        ),
        const SizedBox(height: Spacing.sm),

        // Cancel button
        OutlinedButton(
          onPressed: _isLoading ? null : _handleCancelSetup,
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          child: Text(l10n.cancel),
        ),
      ],
    );
  }

  bool get _canVerify => _codeController.text.length == 6;

  // ---- Enabled View --------------------------------------------------------

  Widget _buildEnabledView(ThemeData theme, AppLocalizations l10n) {
    final colorScheme = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.profileTwoFactorActive,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.profileTwoFactorActiveDesc,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Spacing.lg),

        // Show backup codes button (if they exist from recent setup)
        if (_backupCodes != null) ...[
          OutlinedButton.icon(
            onPressed: () => _showBackupCodesDialog(theme),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size.fromHeight(48),
            ),
            icon: const Icon(Icons.content_copy),
            label: Text(l10n.profileTwoFactorViewBackupCodes),
          ),
          const SizedBox(height: Spacing.sm),
        ],

        // Disable button
        OutlinedButton(
          onPressed: _isLoading ? null : _handleDisablePress,
          style: OutlinedButton.styleFrom(
            foregroundColor: colorScheme.error,
            minimumSize: const Size.fromHeight(48),
          ),
          child: Text(l10n.profileTwoFactorDisable),
        ),
      ],
    );
  }

  // ---- Actions -------------------------------------------------------------

  /// Handle Enable 2FA button press
  Future<void> _handleEnablePress() async {
    setState(() => _isLoading = true);

    try {
      final result = await ref.read(profileProvider.notifier).setup2FA();
      setState(() {
        _setup2FAResult = result;
        _currentState = TwoFactorState.setup;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        _showErrorSnackbar('Failed to setup 2FA: $e');
      }
    }
  }

  /// Handle Verify button press
  Future<void> _handleVerifyPress() async {
    final code = _codeController.text.trim();
    if (code.length != 6) return;

    setState(() => _isLoading = true);

    try {
      final success = await ref.read(profileProvider.notifier).verify2FA(code);
      setState(() => _isLoading = false);

      if (success) {
        // Generate backup codes with cryptographically secure random
        _backupCodes = _generateBackupCodes();

        setState(() {
          _currentState = TwoFactorState.enabled;
          _codeController.clear();
        });

        if (mounted) {
          _showSuccessSnackbar('2FA enabled successfully!');
          _showBackupCodesDialog(Theme.of(context));
        }
      } else {
        if (mounted) {
          _showErrorSnackbar('Invalid verification code. Please try again.');
        }
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        _showErrorSnackbar('Failed to verify 2FA: $e');
      }
    }
  }

  /// Handle Cancel Setup button press
  void _handleCancelSetup() {
    setState(() {
      _currentState = TwoFactorState.notEnabled;
      _setup2FAResult = null;
      _codeController.clear();
    });
  }

  /// Handle Disable 2FA button press
  Future<void> _handleDisablePress() async {
    final confirmed = await _showDisableConfirmationDialog();
    if (!confirmed) return;

    final code = await _showCodeInputDialog();
    if (code == null || code.length != 6) return;

    setState(() => _isLoading = true);

    try {
      await ref.read(profileProvider.notifier).disable2FA(code);
      setState(() {
        _currentState = TwoFactorState.notEnabled;
        _backupCodes = null;
        _isLoading = false;
      });

      if (mounted) {
        _showSuccessSnackbar('2FA disabled successfully');
      }
    } catch (e) {
      setState(() => _isLoading = false);
      if (mounted) {
        _showErrorSnackbar('Failed to disable 2FA: $e');
      }
    }
  }

  // ---- Helpers -------------------------------------------------------------

  /// Copy text to clipboard and show feedback
  Future<void> _copyToClipboard(String text) async {
    await Clipboard.setData(ClipboardData(text: text));
    if (mounted) {
      final l10n = AppLocalizations.of(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(l10n.commonCopied),
          duration: const Duration(seconds: 2),
        ),
      );
    }
  }

  /// Show success snackbar
  void _showSuccessSnackbar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: CyberColors.matrixGreen,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  /// Show error snackbar
  void _showErrorSnackbar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Theme.of(context).colorScheme.error,
        duration: const Duration(seconds: 4),
      ),
    );
  }

  /// Show confirmation dialog for disabling 2FA
  Future<bool> _showDisableConfirmationDialog() async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) {
        final dialogL10n = AppLocalizations.of(context);
        return AlertDialog(
          title: Text(dialogL10n.profileTwoFactorDisableConfirmTitle),
          content: Text(dialogL10n.profileTwoFactorDisableWarning),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: Text(dialogL10n.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              style: FilledButton.styleFrom(
                backgroundColor: Theme.of(context).colorScheme.error,
              ),
              child: Text(dialogL10n.profileTwoFactorDisableButton),
            ),
          ],
        );
      },
    );
    return result ?? false;
  }

  /// Show dialog to input TOTP code for disabling 2FA
  Future<String?> _showCodeInputDialog() async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) {
        final dialogL10n = AppLocalizations.of(context);
        return AlertDialog(
          title: Text(dialogL10n.profileTwoFactorEnterVerificationCode),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(dialogL10n.profileTwoFactorEnterCodeShort),
              const SizedBox(height: Spacing.md),
              TextField(
                controller: controller,
                keyboardType: TextInputType.number,
                maxLength: 6,
                autofocus: true,
                decoration: InputDecoration(
                  labelText: dialogL10n.profileTwoFactorCodeLabel,
                  hintText: '000000',
                  counterText: '',
                ),
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(6),
                ],
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(dialogL10n.cancel),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, controller.text),
              child: Text(dialogL10n.confirm),
            ),
          ],
        );
      },
    );
    controller.dispose();
    return result;
  }

  /// Show backup codes dialog
  void _showBackupCodesDialog(ThemeData theme) {
    if (_backupCodes == null) return;

    unawaited(showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        final dialogL10n = AppLocalizations.of(context);
        return AlertDialog(
          title: Text(dialogL10n.profileTwoFactorBackupCodes),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  dialogL10n.profileTwoFactorBackupCodesInstructions,
                  style: theme.textTheme.bodyMedium,
                ),
                const SizedBox(height: Spacing.md),
                Container(
                  padding: const EdgeInsets.all(Spacing.md),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(Radii.sm),
                  ),
                  child: ListView.separated(
                    shrinkWrap: true,
                    itemCount: _backupCodes!.length,
                    separatorBuilder: (context, index) => const SizedBox(height: Spacing.xs),
                    itemBuilder: (context, index) {
                      final code = _backupCodes![index];
                      return Row(
                        children: [
                          Expanded(
                            child: Text(
                              code,
                              style: theme.textTheme.bodyMedium?.copyWith(
                                fontFamily: 'monospace',
                              ),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
          actions: [
            FilledButton.icon(
              onPressed: () {
                unawaited(_copyToClipboard(_backupCodes!.join('\n')));
              },
              icon: const Icon(Icons.copy),
              label: Text(dialogL10n.profileTwoFactorCopyAll),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text(dialogL10n.commonClose),
            ),
          ],
        );
      },
    ));
  }

  /// Generate backup codes using cryptographically secure random
  List<String> _generateBackupCodes() {
    final random = Random.secure();
    return List.generate(
      8,
      (index) {
        final part1 = random.nextInt(10000).toString().padLeft(4, '0');
        final part2 = random.nextInt(10000).toString().padLeft(4, '0');
        return '$part1-$part2';
      },
    );
  }
}

// ---------------------------------------------------------------------------
// TwoFactorState enum
// ---------------------------------------------------------------------------

/// States for the 2FA screen flow
enum TwoFactorState {
  /// 2FA is not enabled, showing enable option
  notEnabled,

  /// 2FA setup in progress, showing QR code and verification
  setup,

  /// 2FA is enabled, showing disable option
  enabled,
}

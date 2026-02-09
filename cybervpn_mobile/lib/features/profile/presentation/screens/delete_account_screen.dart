import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/profile/domain/usecases/delete_account.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/core/di/providers.dart'
    show profileRepositoryProvider;

// ---------------------------------------------------------------------------
// DeleteAccountScreen
// ---------------------------------------------------------------------------

/// GDPR-compliant account deletion screen with re-authentication and data warning.
///
/// **Flow**:
/// 1. Warning screen listing data to be deleted → 30-day grace period info
/// 2. Password re-entry (+ TOTP if 2FA enabled)
/// 3. Final confirmation
/// 4. API call → disconnect VPN → clear all local data → navigate to login
///
/// Complies with App Store/Play data deletion requirements.
class DeleteAccountScreen extends ConsumerStatefulWidget {
  const DeleteAccountScreen({super.key});

  @override
  ConsumerState<DeleteAccountScreen> createState() =>
      _DeleteAccountScreenState();
}

class _DeleteAccountScreenState extends ConsumerState<DeleteAccountScreen> {
  // Current step in the deletion flow
  _DeletionStep _currentStep = _DeletionStep.warning;

  // Controllers for password and TOTP input
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _totpController = TextEditingController();

  // Controller for final confirmation input
  final TextEditingController _confirmationController = TextEditingController();

  // Loading state for async operations
  bool _isLoading = false;

  // Password visibility toggle
  bool _obscurePassword = true;

  // Countdown timer for final delete button (5-second safety delay)
  Timer? _countdownTimer;
  int _countdownSeconds = 5;

  @override
  void dispose() {
    _countdownTimer?.cancel();
    _passwordController.dispose();
    _totpController.dispose();
    _confirmationController.dispose();
    super.dispose();
  }

  // ---- Build ---------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      resizeToAvoidBottomInset: true,
      appBar: AppBar(
        title: Text(l10n.profileDeleteAccount),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Spacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Danger header
              _buildDangerHeader(theme, l10n),
              const SizedBox(height: Spacing.lg),

              // Step-specific content
              if (_currentStep == _DeletionStep.warning)
                _buildWarningStep(theme, l10n),
              if (_currentStep == _DeletionStep.reAuthentication)
                _buildReAuthenticationStep(theme, l10n),
              if (_currentStep == _DeletionStep.finalConfirmation)
                _buildFinalConfirmationStep(theme, l10n),

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

  // ---- Danger Header -------------------------------------------------------

  Widget _buildDangerHeader(ThemeData theme, AppLocalizations l10n) {
    final colorScheme = theme.colorScheme;

    return Container(
      padding: const EdgeInsets.all(Spacing.md),
      decoration: BoxDecoration(
        color: colorScheme.error.withAlpha(25),
        borderRadius: BorderRadius.circular(Radii.md),
        border: Border.all(
          color: colorScheme.error,
          width: 1.5,
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.warning_amber_rounded,
            color: colorScheme.error,
            size: 32,
          ),
          const SizedBox(width: Spacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l10n.profileDangerZone,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: colorScheme.error,
                  ),
                ),
                const SizedBox(height: Spacing.xs),
                Text(
                  l10n.profileDeleteDangerZoneDesc,
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

  // ---- Step 1: Warning -----------------------------------------------------

  Widget _buildWarningStep(ThemeData theme, AppLocalizations l10n) {
    final colorScheme = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.profileDeleteWhatWillBeDeleted,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.profileDeletePermanentlyDeleted,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Spacing.md),

        // Data to be deleted list
        _buildDataItem(
          icon: Icons.person_outline,
          title: l10n.profileDeletePersonalInfo,
          description: l10n.profileDeletePersonalInfoDesc,
          theme: theme,
        ),
        const SizedBox(height: Spacing.sm),
        _buildDataItem(
          icon: Icons.workspace_premium_outlined,
          title: l10n.profileDeleteSubscriptionHistory,
          description: l10n.profileDeleteSubscriptionHistoryDesc,
          theme: theme,
        ),
        const SizedBox(height: Spacing.sm),
        _buildDataItem(
          icon: Icons.vpn_key_outlined,
          title: l10n.profileDeleteVpnConfigs,
          description: l10n.profileDeleteVpnConfigsDesc,
          theme: theme,
        ),
        const SizedBox(height: Spacing.sm),
        _buildDataItem(
          icon: Icons.settings_outlined,
          title: l10n.profileDeleteAppSettings,
          description: l10n.profileDeleteAppSettingsDesc,
          theme: theme,
        ),
        const SizedBox(height: Spacing.lg),

        // Grace period notice
        Container(
          padding: const EdgeInsets.all(Spacing.md),
          decoration: BoxDecoration(
            color: colorScheme.primaryContainer.withAlpha(40),
            borderRadius: BorderRadius.circular(Radii.md),
            border: Border.all(
              color: colorScheme.primary.withAlpha(40),
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                Icons.info_outline,
                color: colorScheme.primary,
                size: 24,
              ),
              const SizedBox(width: Spacing.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.profileDeleteGracePeriod,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: colorScheme.primary,
                      ),
                    ),
                    const SizedBox(height: Spacing.xs),
                    Text(
                      l10n.profileDeleteGracePeriodDesc,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: Spacing.lg),

        // App Store/Play policy notice
        Container(
          padding: const EdgeInsets.all(Spacing.sm),
          decoration: BoxDecoration(
            color: colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(Radii.sm),
          ),
          child: Text(
            l10n.profileDeleteStorePolicy,
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        const SizedBox(height: Spacing.lg),

        // Action buttons
        FilledButton(
          onPressed: _isLoading ? null : _handleContinueFromWarning,
          style: FilledButton.styleFrom(
            backgroundColor: colorScheme.error,
            minimumSize: const Size.fromHeight(48),
          ),
          child: Text(l10n.profileDeleteContinue),
        ),
        const SizedBox(height: Spacing.sm),
        OutlinedButton(
          onPressed: _isLoading ? null : () => context.pop(),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          child: Text(l10n.cancel),
        ),
      ],
    );
  }

  Widget _buildDataItem({
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
            color: colorScheme.error.withAlpha(25),
            borderRadius: BorderRadius.circular(Radii.sm),
          ),
          child: Icon(
            icon,
            size: 20,
            color: colorScheme.error,
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

  // ---- Step 2: Re-Authentication -------------------------------------------

  Widget _buildReAuthenticationStep(ThemeData theme, AppLocalizations l10n) {
    final colorScheme = theme.colorScheme;
    final profileState = ref.watch(profileProvider).value;
    final is2FAEnabled = profileState?.is2FAEnabled ?? false;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.profileDeleteVerifyIdentity,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.profileDeleteVerifyIdentityDesc,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Spacing.md),

        // Password field
        TextField(
          controller: _passwordController,
          obscureText: _obscurePassword,
          decoration: InputDecoration(
            labelText: l10n.profileDeletePasswordLabel,
            hintText: l10n.profileDeletePasswordHint,
            prefixIcon: const Icon(Icons.lock_outline),
            suffixIcon: IconButton(
              icon: Icon(
                _obscurePassword ? Icons.visibility : Icons.visibility_off,
              ),
              tooltip: _obscurePassword
                  ? l10n.formShowPassword
                  : l10n.formHidePassword,
              onPressed: () {
                setState(() => _obscurePassword = !_obscurePassword);
              },
            ),
          ),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: Spacing.md),

        // TOTP field (if 2FA is enabled)
        if (is2FAEnabled) ...[
          TextField(
            controller: _totpController,
            keyboardType: TextInputType.number,
            maxLength: 6,
            decoration: InputDecoration(
              labelText: l10n.profileTwoFactorCodeLabel,
              hintText: '000000',
              prefixIcon: const Icon(Icons.security),
              counterText: '',
            ),
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(6),
            ],
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: Spacing.xs),
          Text(
            l10n.profileTwoFactorEnterCodeShort,
            style: theme.textTheme.bodySmall?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: Spacing.md),
        ],

        const SizedBox(height: Spacing.lg),

        // Action buttons
        FilledButton(
          onPressed: _canProceedFromReAuth && !_isLoading
              ? _handleContinueFromReAuth
              : null,
          style: FilledButton.styleFrom(
            backgroundColor: colorScheme.error,
            minimumSize: const Size.fromHeight(48),
          ),
          child: Text(l10n.profileDeleteVerifyAndContinue),
        ),
        const SizedBox(height: Spacing.sm),
        OutlinedButton(
          onPressed: _isLoading ? null : _handleBackToWarning,
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          child: Text(l10n.commonBack),
        ),
      ],
    );
  }

  bool get _canProceedFromReAuth {
    final profileState = ref.watch(profileProvider).value;
    final is2FAEnabled = profileState?.is2FAEnabled ?? false;

    if (_passwordController.text.isEmpty) return false;
    if (is2FAEnabled && _totpController.text.length != 6) return false;
    return true;
  }

  // ---- Step 3: Final Confirmation ------------------------------------------

  Widget _buildFinalConfirmationStep(ThemeData theme, AppLocalizations l10n) {
    final colorScheme = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          l10n.profileDeleteFinalConfirmation,
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          l10n.profileDeleteFinalConfirmationDesc,
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Spacing.md),

        // Confirmation warning box
        Container(
          padding: const EdgeInsets.all(Spacing.md),
          decoration: BoxDecoration(
            color: colorScheme.error.withAlpha(25),
            borderRadius: BorderRadius.circular(Radii.md),
            border: Border.all(
              color: colorScheme.error,
              width: 1.5,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    Icons.error_outline,
                    color: colorScheme.error,
                    size: 24,
                  ),
                  const SizedBox(width: Spacing.sm),
                  Text(
                    l10n.profileDeleteIrreversible,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: colorScheme.error,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: Spacing.sm),
              Text(
                l10n.profileDeleteIrreversibleList,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: Spacing.lg),

        // Type DELETE confirmation
        Text(
          l10n.profileDeleteConfirmInput,
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        TextField(
          controller: _confirmationController,
          decoration: InputDecoration(
            hintText: l10n.deleteAccountConfirmHint,
            prefixIcon: const Icon(Icons.keyboard),
          ),
          textCapitalization: TextCapitalization.characters,
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: Spacing.lg),

        // Action buttons (with 5-second countdown safety delay)
        FilledButton(
          onPressed:
              _canConfirmDeletion && !_isLoading ? _handleDeleteAccount : null,
          style: FilledButton.styleFrom(
            backgroundColor: colorScheme.error,
            minimumSize: const Size.fromHeight(48),
          ),
          child: Text(
            _countdownSeconds > 0
                ? l10n.deleteAccountCountdown(_countdownSeconds)
                : l10n.deleteAccountFinalButton,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        OutlinedButton(
          onPressed: _isLoading ? null : _handleBackToReAuth,
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          child: Text(l10n.commonBack),
        ),
      ],
    );
  }

  bool get _canConfirmDeletion {
    return _confirmationController.text.toUpperCase() == 'DELETE' &&
        _countdownSeconds == 0;
  }

  // ---- Actions -------------------------------------------------------------

  /// Handle continue from warning step
  void _handleContinueFromWarning() {
    setState(() {
      _currentStep = _DeletionStep.reAuthentication;
    });
  }

  /// Handle back to warning step
  void _handleBackToWarning() {
    setState(() {
      _currentStep = _DeletionStep.warning;
      _passwordController.clear();
      _totpController.clear();
    });
  }

  /// Handle continue from re-authentication step
  Future<void> _handleContinueFromReAuth() async {
    // Validate credentials format client-side
    if (_passwordController.text.isEmpty) {
      _showErrorSnackbar('Password is required');
      return;
    }

    final profileState = ref.read(profileProvider).value;
    final is2FAEnabled = profileState?.is2FAEnabled ?? false;

    if (is2FAEnabled) {
      final totpCode = _totpController.text;
      if (totpCode.isEmpty || totpCode.length != 6) {
        _showErrorSnackbar('Please enter a valid 6-digit code');
        return;
      }
    }

    // Move to final confirmation (credentials will be validated on actual deletion)
    setState(() {
      _currentStep = _DeletionStep.finalConfirmation;
    });
    _startCountdown();
  }

  /// Starts a 5-second countdown before the delete button becomes active.
  void _startCountdown() {
    _countdownTimer?.cancel();
    setState(() => _countdownSeconds = 5);
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (_countdownSeconds <= 1) {
        timer.cancel();
        if (mounted) setState(() => _countdownSeconds = 0);
      } else {
        if (mounted) setState(() => _countdownSeconds--);
      }
    });
  }

  /// Handle back to re-authentication step
  void _handleBackToReAuth() {
    _countdownTimer?.cancel();
    setState(() {
      _currentStep = _DeletionStep.reAuthentication;
      _confirmationController.clear();
      _countdownSeconds = 5;
    });
  }

  /// Handle account deletion
  Future<void> _handleDeleteAccount() async {
    if (!_canConfirmDeletion) return;

    // Trigger error haptic pattern on account deletion confirmation.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.error());

    setState(() => _isLoading = true);

    try {
      final profileState = ref.read(profileProvider).value;
      final is2FAEnabled = profileState?.is2FAEnabled ?? false;

      // Create the delete account use case
      final deleteAccountUseCase = DeleteAccountUseCase(
        ref.read(profileRepositoryProvider),
      );

      // Call the delete account API
      await deleteAccountUseCase.call(
        password: _passwordController.text,
        is2FAEnabled: is2FAEnabled,
        totpCode: is2FAEnabled ? _totpController.text : null,
      );

      // Disconnect VPN if connected
      final vpnState = ref.read(vpnConnectionProvider).value;
      if (vpnState?.isConnected ?? false) {
        await ref.read(vpnConnectionProvider.notifier).disconnect();
      }

      // Clear all local data
      await _clearLocalData();

      if (!mounted) return;

      final l10n = AppLocalizations.of(context);

      // Show success message
      _showSuccessSnackbar(l10n.profileDeleteScheduledSuccess);

      // Navigate to login and clear navigation stack
      await Future<void>.delayed(const Duration(seconds: 1));
      if (!mounted) return;
      context.go('/login');
    } on ArgumentError catch (e) {
      setState(() => _isLoading = false);
      _showErrorSnackbar(e.toString());
    } catch (e) {
      setState(() => _isLoading = false);
      _showErrorSnackbar('Account deletion failed: ${e.toString()}');
    }
  }

  /// Clear all local data including secure storage and shared preferences
  Future<void> _clearLocalData() async {
    try {
      // Clear secure storage (tokens, credentials)
      final secureStorage = SecureStorageWrapper();
      await secureStorage.deleteAll();

      // Clear local storage (preferences, settings)
      final localStorage = LocalStorageWrapper();
      await localStorage.clear();
    } catch (e) {
      // Log error but don't fail the deletion flow
      debugPrint('Warning: Failed to clear some local data: $e');
    }
  }

  // ---- Helpers -------------------------------------------------------------

  /// Show success snackbar
  void _showSuccessSnackbar(String message) {
    if (!mounted) return;
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
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Theme.of(context).colorScheme.error,
        duration: const Duration(seconds: 4),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Deletion Step enum
// ---------------------------------------------------------------------------

/// States for the account deletion flow
enum _DeletionStep {
  /// Warning screen with data deletion preview
  warning,

  /// Re-authentication with password (and TOTP if 2FA enabled)
  reAuthentication,

  /// Final confirmation step
  finalConfirmation,
}

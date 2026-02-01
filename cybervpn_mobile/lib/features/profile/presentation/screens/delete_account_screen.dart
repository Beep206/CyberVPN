import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/storage/local_storage.dart';
import 'package:cybervpn_mobile/core/storage/secure_storage.dart';
import 'package:cybervpn_mobile/features/profile/domain/use_cases/delete_account.dart';
import 'package:cybervpn_mobile/features/profile/presentation/providers/profile_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';

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

  @override
  void dispose() {
    _passwordController.dispose();
    _totpController.dispose();
    _confirmationController.dispose();
    super.dispose();
  }

  // ---- Build ---------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Delete Account'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(Spacing.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Danger header
              _buildDangerHeader(theme),
              const SizedBox(height: Spacing.lg),

              // Step-specific content
              if (_currentStep == _DeletionStep.warning)
                _buildWarningStep(theme),
              if (_currentStep == _DeletionStep.reAuthentication)
                _buildReAuthenticationStep(theme),
              if (_currentStep == _DeletionStep.finalConfirmation)
                _buildFinalConfirmationStep(theme),

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

  Widget _buildDangerHeader(ThemeData theme) {
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
                  'Danger Zone',
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: colorScheme.error,
                  ),
                ),
                const SizedBox(height: Spacing.xs),
                Text(
                  'This action cannot be undone',
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

  Widget _buildWarningStep(ThemeData theme) {
    final colorScheme = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'What will be deleted?',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          'The following data will be permanently deleted:',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: Spacing.md),

        // Data to be deleted list
        _buildDataItem(
          icon: Icons.person_outline,
          title: 'Personal Information',
          description: 'Email, username, and profile data',
          theme: theme,
        ),
        const SizedBox(height: Spacing.sm),
        _buildDataItem(
          icon: Icons.workspace_premium_outlined,
          title: 'Subscription & Payment History',
          description: 'All active subscriptions and transaction records',
          theme: theme,
        ),
        const SizedBox(height: Spacing.sm),
        _buildDataItem(
          icon: Icons.vpn_key_outlined,
          title: 'VPN Configurations',
          description: 'Server settings and connection preferences',
          theme: theme,
        ),
        const SizedBox(height: Spacing.sm),
        _buildDataItem(
          icon: Icons.settings_outlined,
          title: 'App Settings',
          description: 'All preferences and customizations',
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
                      '30-Day Grace Period',
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: colorScheme.primary,
                      ),
                    ),
                    const SizedBox(height: Spacing.xs),
                    Text(
                      'Your account will be scheduled for deletion. You can cancel '
                      'this request within 30 days by logging back in. After this '
                      'period, all data will be permanently deleted.',
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
            'In compliance with App Store and Google Play data deletion policies, '
            'all personal data will be permanently removed from our servers.',
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
          child: const Text('Continue with Deletion'),
        ),
        const SizedBox(height: Spacing.sm),
        OutlinedButton(
          onPressed: _isLoading ? null : () => context.pop(),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          child: const Text('Cancel'),
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

  Widget _buildReAuthenticationStep(ThemeData theme) {
    final colorScheme = theme.colorScheme;
    final profileState = ref.watch(profileProvider).value;
    final is2FAEnabled = profileState?.is2FAEnabled ?? false;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Verify Your Identity',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          'For security reasons, please re-enter your credentials to confirm '
          'account deletion.',
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
            labelText: 'Password',
            hintText: 'Enter your password',
            prefixIcon: const Icon(Icons.lock_outline),
            suffixIcon: IconButton(
              icon: Icon(
                _obscurePassword ? Icons.visibility : Icons.visibility_off,
              ),
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
            decoration: const InputDecoration(
              labelText: '6-digit code',
              hintText: '000000',
              prefixIcon: Icon(Icons.security),
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
            'Enter the 6-digit code from your authenticator app',
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
          child: const Text('Verify and Continue'),
        ),
        const SizedBox(height: Spacing.sm),
        OutlinedButton(
          onPressed: _isLoading ? null : _handleBackToWarning,
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          child: const Text('Back'),
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

  Widget _buildFinalConfirmationStep(ThemeData theme) {
    final colorScheme = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Final Confirmation',
          style: theme.textTheme.titleMedium?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        Text(
          'This is your last chance to cancel. Once confirmed, your account '
          'will be scheduled for permanent deletion.',
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
                    'This action is irreversible',
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: colorScheme.error,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: Spacing.sm),
              Text(
                '• All data will be permanently deleted after 30 days\n'
                '• Active subscriptions will be cancelled\n'
                '• You will be immediately logged out\n'
                '• This cannot be undone',
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
          'Type DELETE to confirm',
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: Spacing.sm),
        TextField(
          controller: _confirmationController,
          decoration: const InputDecoration(
            hintText: 'DELETE',
            prefixIcon: Icon(Icons.keyboard),
          ),
          textCapitalization: TextCapitalization.characters,
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: Spacing.lg),

        // Action buttons
        FilledButton(
          onPressed:
              _canConfirmDeletion && !_isLoading ? _handleDeleteAccount : null,
          style: FilledButton.styleFrom(
            backgroundColor: colorScheme.error,
            minimumSize: const Size.fromHeight(48),
          ),
          child: const Text('Delete My Account'),
        ),
        const SizedBox(height: Spacing.sm),
        OutlinedButton(
          onPressed: _isLoading ? null : _handleBackToReAuth,
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          child: const Text('Back'),
        ),
      ],
    );
  }

  bool get _canConfirmDeletion {
    return _confirmationController.text.toUpperCase() == 'DELETE';
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
  }

  /// Handle back to re-authentication step
  void _handleBackToReAuth() {
    setState(() {
      _currentStep = _DeletionStep.reAuthentication;
      _confirmationController.clear();
    });
  }

  /// Handle account deletion
  Future<void> _handleDeleteAccount() async {
    if (!_canConfirmDeletion) return;

    // Trigger error haptic pattern on account deletion confirmation.
    final haptics = ref.read(hapticServiceProvider);
    haptics.error();

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

      // Show success message
      _showSuccessSnackbar('Account deletion scheduled successfully');

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

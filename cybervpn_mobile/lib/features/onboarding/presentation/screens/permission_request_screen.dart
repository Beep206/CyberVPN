import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/providers/permission_request_provider.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/widgets/permission_card.dart';

/// Permission request screen displayed after onboarding carousel.
///
/// Requests VPN and notification permissions with contextual explanations.
/// Shows explanation cards before triggering system permission dialogs.
/// Handles both granted and denied scenarios gracefully.
class PermissionRequestScreen extends ConsumerWidget {
  const PermissionRequestScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncState = ref.watch(permissionRequestProvider);

    return Scaffold(
      body: SafeArea(
        child: asyncState.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (error, _) => _buildError(context, error.toString()),
          data: (state) => _buildContent(context, ref, state),
        ),
      ),
    );
  }

  Widget _buildError(BuildContext context, String error) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.xl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: theme.colorScheme.error,
            ),
            const SizedBox(height: Spacing.lg),
            Text(
              l10n.errorGeneric,
              style: theme.textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: Spacing.md),
            Text(
              error,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: Spacing.xl),
            ElevatedButton(
              onPressed: () => context.go('/login'),
              child: Text(l10n.permissionContinueAnyway),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    WidgetRef ref,
    PermissionRequestState state,
  ) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    // If all permissions are processed, show completion view
    if (state.isComplete) {
      return _buildCompletionView(context, ref, state);
    }

    return Padding(
      padding: const EdgeInsets.all(Spacing.xl),
      child: Column(
        children: [
          // Header
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  Icons.security_rounded,
                  size: 80,
                  color: colorScheme.primary,
                ),
                const SizedBox(height: Spacing.lg),
                Text(
                  l10n.permissionSetupTitle,
                  style: theme.textTheme.headlineMedium?.copyWith(
                    color: colorScheme.primary,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: Spacing.md),
                Text(
                  l10n.permissionSetupSubtitle,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: Spacing.xl),

                // Permission cards
                PermissionCard(
                  icon: Icons.vpn_lock,
                  title: l10n.permissionVpnTitle,
                  description: l10n.permissionVpnDescription,
                  isGranted: state.vpnPermissionGranted,
                  isProcessing: state.isRequestingVpnPermission,
                ),
              ],
            ),
          ),

          // Action button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: state.canRequestPermissions
                  ? () => _handleRequestPermissions(context, ref)
                  : null,
              child: Text(
                state.hasRequestedAnyPermission
                    ? l10n.commonContinue
                    : l10n.permissionGrantButton,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCompletionView(
    BuildContext context,
    WidgetRef ref,
    PermissionRequestState state,
  ) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

    final allGranted = state.allPermissionsGranted;
    final someDenied = state.hasRequestedAnyPermission && !allGranted;

    return Padding(
      padding: const EdgeInsets.all(Spacing.xl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            allGranted ? Icons.check_circle : Icons.info_outline,
            size: 80,
            color: allGranted ? colorScheme.primary : colorScheme.secondary,
          ),
          const SizedBox(height: Spacing.lg),
          Text(
            allGranted ? l10n.permissionAllSet : l10n.permissionAlmostReady,
            style: theme.textTheme.headlineMedium?.copyWith(
              color: colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.md),
          Text(
            someDenied
                ? l10n.permissionEnableLater
                : l10n.permissionAppReady,
            style: theme.textTheme.bodyLarge?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.xl),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              onPressed: () => _handleContinue(context, ref),
              child: Text(l10n.onboardingGetStarted),
            ),
          ),
          if (someDenied) ...[
            const SizedBox(height: Spacing.md),
            TextButton(
              onPressed: () => _handleOpenSettings(context),
              child: Text(l10n.permissionOpenSettings),
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _handleRequestPermissions(
    BuildContext context,
    WidgetRef ref,
  ) async {
    await ref.read(permissionRequestProvider.notifier).requestAllPermissions();
  }

  Future<void> _handleContinue(BuildContext context, WidgetRef ref) async {
    await ref.read(permissionRequestProvider.notifier).complete();
    if (context.mounted) {
      context.go('/login');
    }
  }

  void _handleOpenSettings(BuildContext context) {
    // Note: Navigation to app settings pending implementation.
    // This would use a package like app_settings or url_launcher
    // to open the device's app settings page
    final l10n = AppLocalizations.of(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(l10n.permissionEnableInSettings),
      ),
    );
  }
}

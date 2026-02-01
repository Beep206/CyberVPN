import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
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
              'Something went wrong',
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
              child: const Text('Continue Anyway'),
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
                  'Set Up Permissions',
                  style: theme.textTheme.headlineMedium?.copyWith(
                    color: colorScheme.primary,
                    fontWeight: FontWeight.bold,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: Spacing.md),
                Text(
                  'CyberVPN needs a few permissions to keep you secure',
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: colorScheme.onSurfaceVariant,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: Spacing.xl),

                // Permission cards
                PermissionCard(
                  icon: Icons.vpn_lock,
                  title: 'VPN Connection',
                  description:
                      'CyberVPN creates a secure tunnel to protect your data',
                  isGranted: state.vpnPermissionGranted,
                  isProcessing: state.isRequestingVpnPermission,
                ),
                const SizedBox(height: Spacing.md),
                PermissionCard(
                  icon: Icons.notifications_active,
                  title: 'Notifications',
                  description:
                      'Stay informed about connection status and security alerts',
                  isGranted: state.notificationPermissionGranted,
                  isProcessing: state.isRequestingNotificationPermission,
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
                state.hasRequestedAnyPermission ? 'Continue' : 'Grant Permissions',
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
            allGranted ? 'All Set!' : 'Almost Ready',
            style: theme.textTheme.headlineMedium?.copyWith(
              color: colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: Spacing.md),
          Text(
            someDenied
                ? 'You can enable these permissions later in Settings if needed'
                : 'Your app is configured and ready to use',
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
              child: const Text('Get Started'),
            ),
          ),
          if (someDenied) ...[
            const SizedBox(height: Spacing.md),
            TextButton(
              onPressed: () => _handleOpenSettings(context),
              child: const Text('Open Settings'),
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
    // TODO: Implement navigation to app settings
    // This would use a package like app_settings or url_launcher
    // to open the device's app settings page
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Please enable permissions in your device Settings'),
      ),
    );
  }
}

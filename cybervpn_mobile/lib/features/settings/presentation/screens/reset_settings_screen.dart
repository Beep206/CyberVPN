import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/settings/data/services/app_reset_service.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/app_reset_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

class ResetSettingsScreen extends ConsumerWidget {
  const ResetSettingsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final resetState = ref.watch(appResetControllerProvider);
    final isBusy = resetState.isLoading;

    final content = ListView(
      children: [
        if (isBusy) const LinearProgressIndicator(),
        SettingsSection(
          title: 'Actions',
          children: [
            SettingsTile.navigation(
              key: const Key('reset_settings_action'),
              title: 'Reset Settings',
              subtitle:
                  'Restore VPN, ping, subscription, appearance, notification, and other app preferences to defaults.',
              leading: const Icon(Icons.restart_alt_outlined),
              onTap: () => _handleResetSettings(context, ref, isBusy),
            ),
            SettingsTile.navigation(
              key: const Key('full_app_reset_action'),
              title: 'Full App Reset',
              subtitle:
                  'Sign out and remove settings, local profiles, imported configs, caches, and logs.',
              leading: const Icon(Icons.delete_forever_outlined),
              onTap: () => _handleFullAppReset(context, ref, isBusy),
            ),
          ],
        ),
        const SettingsSection(
          title: 'Full Reset Scope',
          children: [
            SettingsTile.info(
              key: Key('reset_scope_local_data'),
              title: 'Local Data Removed',
              subtitle:
                  'Settings, imported configs, VPN profiles, subscription metadata, local caches, and persistent logs.',
              leading: Icon(Icons.layers_clear_outlined),
            ),
            SettingsTile.info(
              key: Key('reset_scope_auth'),
              title: 'Auth and Session Removed',
              subtitle:
                  'Access tokens, refresh tokens, cached user data, biometric/app-lock auth state, and RevenueCat user session.',
              leading: Icon(Icons.logout_outlined),
            ),
            SettingsTile.info(
              key: Key('reset_scope_preserved'),
              title: 'Preserved',
              subtitle:
                  'Device identity is intentionally preserved so backend/device registration remains stable after reset.',
              leading: Icon(Icons.smartphone_outlined),
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            Spacing.md,
            Spacing.sm,
            Spacing.md,
            Spacing.lg,
          ),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(Radii.lg),
            ),
            child: const Padding(
              padding: EdgeInsets.all(Spacing.md),
              child: Text(
                'Full App Reset follows an explicit product contract. It clears only the local areas listed above and requires an explicit confirmation dialog before execution.',
              ),
            ),
          ),
        ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );

    if (embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Reset')),
      body: content,
    );
  }

  Future<void> _handleResetSettings(
    BuildContext context,
    WidgetRef ref,
    bool isBusy,
  ) async {
    if (isBusy) {
      return;
    }

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Reset Settings'),
          content: const Text(
            'This restores all app settings to defaults. Local profiles, imports, logs, and auth/session data are not touched.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Reset Settings'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) {
      return;
    }

    try {
      await ref.read(appResetControllerProvider.notifier).resetSettings();
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Settings reset complete')),
      );
    } catch (error) {
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to reset settings: $error')),
      );
    }
  }

  Future<void> _handleFullAppReset(
    BuildContext context,
    WidgetRef ref,
    bool isBusy,
  ) async {
    if (isBusy) {
      return;
    }

    const scope = AppResetService.fullResetScope;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Full App Reset'),
          content: Text(
            'This signs you out and removes all local app data covered by the reset contract.\n\n'
            'Clears settings: ${scope.clearsSettings}\n'
            'Clears VPN profiles: ${scope.clearsVpnProfiles}\n'
            'Clears imported configs: ${scope.clearsImportedConfigs}\n'
            'Clears logs: ${scope.clearsLogs}\n'
            'Clears local caches: ${scope.clearsLocalCaches}\n'
            'Clears auth/session: ${scope.clearsAuthSessionData}\n'
            'Preserves device identity: ${scope.preservesDeviceIdentity}',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: Theme.of(dialogContext).colorScheme.error,
              ),
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Full App Reset'),
            ),
          ],
        );
      },
    );

    if (confirmed != true) {
      return;
    }

    try {
      await ref.read(appResetControllerProvider.notifier).performFullAppReset();
      if (context.mounted) {
        context.go('/onboarding');
      }
    } catch (error) {
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Failed to complete full app reset: $error')),
      );
    }
  }
}

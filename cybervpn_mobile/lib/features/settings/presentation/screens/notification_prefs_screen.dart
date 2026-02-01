import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

// ---------------------------------------------------------------------------
// NotificationPrefsScreen
// ---------------------------------------------------------------------------

/// Notification preferences sub-screen with toggle tiles for each category.
///
/// Categories:
/// - Connection status changes (default on)
/// - Subscription expiry (default on)
/// - Promotional (default off)
/// - Referral activity (default on)
/// - Security alerts (always on, disabled toggle with explanation)
/// - VPN notification speed (Android-only, default off)
///
/// All changes are persisted via [settingsProvider].
class NotificationPrefsScreen extends ConsumerWidget {
  const NotificationPrefsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncSettings = ref.watch(settingsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notification Preferences'),
      ),
      body: asyncSettings.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _buildError(context, ref, error),
        data: (settings) => _buildBody(context, ref, settings),
      ),
    );
  }

  // -- Error state -----------------------------------------------------------

  Widget _buildError(BuildContext context, WidgetRef ref, Object error) {
    final theme = Theme.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
          const SizedBox(height: 12),
          Text(
            'Failed to load notification settings',
            style: theme.textTheme.bodyLarge,
          ),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: () => ref.invalidate(settingsProvider),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  // -- Data state ------------------------------------------------------------

  Widget _buildBody(
    BuildContext context,
    WidgetRef ref,
    AppSettings settings,
  ) {
    final notifier = ref.read(settingsProvider.notifier);

    return ListView(
      children: [
        // --- General Notifications ---
        SettingsSection(
          title: 'General',
          children: [
            SettingsTile.toggle(
              key: const Key('toggle_notification_connection'),
              title: 'Connection status changes',
              subtitle: 'Get notified when VPN connects or disconnects',
              leading: const Icon(Icons.wifi_outlined),
              value: settings.notificationConnection,
              onChanged: (_) =>
                  notifier.toggleNotification(NotificationType.connection),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_notification_expiry'),
              title: 'Subscription expiry',
              subtitle: 'Reminders before your subscription expires',
              leading: const Icon(Icons.event_outlined),
              value: settings.notificationExpiry,
              onChanged: (_) =>
                  notifier.toggleNotification(NotificationType.expiry),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_notification_promotional'),
              title: 'Promotional',
              subtitle: 'Offers, discounts, and new features',
              leading: const Icon(Icons.campaign_outlined),
              value: settings.notificationPromotional,
              onChanged: (_) =>
                  notifier.toggleNotification(NotificationType.promotional),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_notification_referral'),
              title: 'Referral activity',
              subtitle: 'Updates on your referral rewards',
              leading: const Icon(Icons.group_outlined),
              value: settings.notificationReferral,
              onChanged: (_) =>
                  notifier.toggleNotification(NotificationType.referral),
            ),
          ],
        ),

        // --- Security Alerts (always on) ---
        const SettingsSection(
          title: 'Security',
          children: [
            _SecurityAlertsTile(key: Key('toggle_notification_security')),
          ],
        ),

        // --- Android-only: VPN speed in notification ---
        if (_isAndroid)
          SettingsSection(
            title: 'VPN Notification',
            children: [
              SettingsTile.toggle(
                key: const Key('toggle_notification_vpn_speed'),
                title: 'Show speed in VPN notification',
                subtitle: 'Display connection speed in persistent notification',
                leading: const Icon(Icons.speed_outlined),
                value: settings.notificationVpnSpeed,
                onChanged: (_) =>
                    notifier.toggleNotification(NotificationType.vpnSpeed),
              ),
            ],
          ),

        // Bottom padding so content is not obscured by navigation bar.
        const SizedBox(height: 80),
      ],
    );
  }

  // -- Helpers ---------------------------------------------------------------

  /// Whether the current platform is Android.
  ///
  /// Guarded with a try-catch for test environments that may not have
  /// platform support.
  bool get _isAndroid {
    try {
      return Platform.isAndroid;
    } catch (_) {
      return false;
    }
  }
}

// ---------------------------------------------------------------------------
// _SecurityAlertsTile
// ---------------------------------------------------------------------------

/// A permanently enabled toggle tile for security alerts.
///
/// The switch is always on and the tile is non-interactive, with an
/// explanation subtitle telling the user why it cannot be disabled.
class _SecurityAlertsTile extends StatelessWidget {
  const _SecurityAlertsTile({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    final titleStyle = theme.textTheme.bodyLarge?.copyWith(
      color: colorScheme.onSurface,
    );

    final subtitleStyle = theme.textTheme.bodySmall?.copyWith(
      color: colorScheme.onSurfaceVariant,
    );

    return ListTile(
      leading: const Icon(Icons.shield_outlined),
      title: Text('Security alerts', style: titleStyle),
      subtitle: Text(
        'Required for account security. Cannot be disabled.',
        style: subtitleStyle,
      ),
      trailing: const Switch(
        value: true,
        onChanged: null,
      ),
    );
  }
}

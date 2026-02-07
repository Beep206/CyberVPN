import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
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
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.settingsNotificationPrefsTitle),
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
    final l10n = AppLocalizations.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
          const SizedBox(height: 12),
          Text(
            l10n.settingsNotificationLoadError,
            style: theme.textTheme.bodyLarge,
          ),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: () => ref.invalidate(settingsProvider),
            child: Text(l10n.retry),
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
    final l10n = AppLocalizations.of(context);

    return ListView(
      children: [
        // --- General Notifications ---
        SettingsSection(
          title: l10n.settingsNotificationGeneralSection,
          children: [
            SettingsTile.toggle(
              key: const Key('toggle_notification_connection'),
              title: l10n.settingsNotificationConnectionLabel,
              subtitle: l10n.settingsNotificationConnectionDescription,
              leading: const Icon(Icons.wifi_outlined),
              value: settings.notificationConnection,
              onChanged: (_) =>
                  notifier.toggleNotification(NotificationType.connection),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_notification_expiry'),
              title: l10n.settingsNotificationExpiryLabel,
              subtitle: l10n.settingsNotificationExpiryDescription,
              leading: const Icon(Icons.event_outlined),
              value: settings.notificationExpiry,
              onChanged: (_) =>
                  notifier.toggleNotification(NotificationType.expiry),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_notification_promotional'),
              title: l10n.settingsNotificationPromotionLabel,
              subtitle: l10n.settingsNotificationPromotionalDescription,
              leading: const Icon(Icons.campaign_outlined),
              value: settings.notificationPromotional,
              onChanged: (_) =>
                  notifier.toggleNotification(NotificationType.promotional),
            ),
            SettingsTile.toggle(
              key: const Key('toggle_notification_referral'),
              title: l10n.settingsNotificationReferralLabel,
              subtitle: l10n.settingsNotificationReferralDescription,
              leading: const Icon(Icons.group_outlined),
              value: settings.notificationReferral,
              onChanged: (_) =>
                  notifier.toggleNotification(NotificationType.referral),
            ),
          ],
        ),

        // --- Security Alerts (always on) ---
        SettingsSection(
          title: l10n.settingsNotificationSecuritySection,
          children: const [
            _SecurityAlertsTile(key: Key('toggle_notification_security')),
          ],
        ),

        // --- Android-only: VPN speed in notification ---
        if (_isAndroid)
          SettingsSection(
            title: l10n.settingsNotificationVpnSection,
            children: [
              SettingsTile.toggle(
                key: const Key('toggle_notification_vpn_speed'),
                title: l10n.settingsNotificationVpnSpeedLabel,
                subtitle: l10n.settingsNotificationVpnSpeedDescription,
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
    } catch (e) {
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

    final l10n = AppLocalizations.of(context);

    return ListTile(
      leading: const Icon(Icons.shield_outlined),
      title: Text(l10n.settingsNotificationSecurityLabel, style: titleStyle),
      subtitle: Text(
        l10n.settingsNotificationSecurityRequired,
        style: subtitleStyle,
      ),
      trailing: const Switch(
        value: true,
        onChanged: null,
      ),
    );
  }
}

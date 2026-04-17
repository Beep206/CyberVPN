import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/per_app_proxy_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

class PerAppProxyScreen extends ConsumerWidget {
  const PerAppProxyScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncSettings = ref.watch(settingsProvider);
    final matrix = ref.watch(vpnSettingsSupportMatrixProvider);
    final support = matrix.perAppProxy;
    final isSupported =
        support.isAvailable &&
        ref.watch(perAppProxyPlatformServiceProvider).isSupported;

    final content = asyncSettings.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) =>
          const Center(child: Text('Failed to load Per-App Proxy settings')),
      data: (settings) => _PerAppProxyContent(
        settings: settings,
        isSupported: isSupported,
        support: support,
      ),
    );

    if (embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Per-App Proxy')),
      body: content,
    );
  }
}

class _PerAppProxyContent extends ConsumerWidget {
  const _PerAppProxyContent({
    required this.settings,
    required this.isSupported,
    required this.support,
  });

  final AppSettings settings;
  final bool isSupported;
  final VpnSettingsFeatureSupport support;

  String _modeTitle(PerAppProxyMode mode) {
    return switch (mode) {
      PerAppProxyMode.off => 'Off',
      PerAppProxyMode.proxySelected => 'Selected apps use proxy',
      PerAppProxyMode.bypassSelected => 'Selected apps bypass proxy',
    };
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(settingsProvider.notifier);
    final asyncApps = ref.watch(installedAppsProvider);

    if (!isSupported) {
      return ListView(
        children: [
          SettingsSection(
            title: 'Status',
            children: [
              SettingsTile.info(
                key: const Key('per_app_proxy_status_tile'),
                title: 'Per-App Proxy',
                subtitle:
                    'Current stored mode: ${_modeTitle(settings.perAppProxyMode)}.',
              ),
              SettingsTile.info(
                key: const Key('per_app_proxy_selection_tile'),
                title: 'Stored app selection',
                subtitle: settings.perAppProxyAppIds.isEmpty
                    ? 'No stored application selection.'
                    : '${settings.perAppProxyAppIds.length} app(s) remain stored for Android runtime.',
              ),
            ],
          ),
          _CapabilityNotice(
            key: const Key('per_app_proxy_unsupported_notice'),
            message:
                support.message ??
                'Per-App Proxy is currently available only on Android. '
                    'The setting remains stored for Android, but it is hidden from standard iOS VPN settings.',
          ),
          const _CapabilityNotice(
            message:
                'Changes still apply on the next Android VPN connection. This screen is read-only on unsupported platforms to avoid dead toggles.',
          ),
          SizedBox(height: Spacing.navBarClearance(context)),
        ],
      );
    }

    return ListView(
      children: [
        SettingsSection(
          title: 'Mode',
          children: [
            SettingsTile.radio(
              key: const Key('radio_per_app_mode_off'),
              title: 'Off',
              subtitle: 'Proxy applies to all applications without exceptions.',
              value: PerAppProxyMode.off,
              groupValue: settings.perAppProxyMode,
              onChanged: (_) =>
                  notifier.updatePerAppProxyMode(PerAppProxyMode.off),
            ),
            SettingsTile.radio(
              key: const Key('radio_per_app_mode_proxy_selected'),
              title: 'Selected apps use proxy',
              subtitle:
                  'Only the applications you select will use the VPN tunnel.',
              value: PerAppProxyMode.proxySelected,
              groupValue: settings.perAppProxyMode,
              onChanged: (_) =>
                  notifier.updatePerAppProxyMode(PerAppProxyMode.proxySelected),
            ),
            SettingsTile.radio(
              key: const Key('radio_per_app_mode_bypass_selected'),
              title: 'Selected apps bypass proxy',
              subtitle:
                  'The selected applications will be excluded from the VPN tunnel.',
              value: PerAppProxyMode.bypassSelected,
              groupValue: settings.perAppProxyMode,
              onChanged: (_) => notifier.updatePerAppProxyMode(
                PerAppProxyMode.bypassSelected,
              ),
            ),
          ],
        ),
        SettingsSection(
          title: 'Applications',
          children: [
            if (settings.perAppProxyMode == PerAppProxyMode.off)
              const ListTile(
                title: Text('Per-App Proxy is disabled'),
                subtitle: Text(
                  'Enable one of the app-selection modes above to choose applications.',
                ),
              )
            else
              asyncApps.when(
                loading: () => const Padding(
                  padding: EdgeInsets.all(Spacing.md),
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (error, _) => Padding(
                  padding: const EdgeInsets.all(Spacing.md),
                  child: Text('Failed to load installed apps: $error'),
                ),
                data: (apps) {
                  if (apps.isEmpty) {
                    return const Padding(
                      padding: EdgeInsets.all(Spacing.md),
                      child: Text(
                        'No launchable applications were returned by Android.',
                      ),
                    );
                  }

                  return Column(
                    children: [
                      for (final app in apps)
                        CheckboxListTile(
                          key: Key('checkbox_app_${app.packageName}'),
                          value: settings.perAppProxyAppIds.contains(
                            app.packageName,
                          ),
                          onChanged: (_) =>
                              notifier.togglePerAppProxyApp(app.packageName),
                          title: Text(app.displayName),
                          subtitle: Text(app.packageName),
                          secondary: app.isSystemApp
                              ? const Icon(Icons.android_outlined)
                              : const Icon(Icons.apps_outlined),
                          controlAffinity: ListTileControlAffinity.trailing,
                        ),
                    ],
                  );
                },
              ),
          ],
        ),
        const _CapabilityNotice(
          message:
              'Changes apply on the next VPN connection. Android runtime uses the current app selection to derive blockedApps for flutter_v2ray_plus.',
        ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );
  }
}

class _CapabilityNotice extends StatelessWidget {
  const _CapabilityNotice({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        Spacing.md,
        Spacing.sm,
        Spacing.md,
        Spacing.md,
      ),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(Radii.lg),
        ),
        child: Padding(
          padding: const EdgeInsets.all(Spacing.md),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                Icons.info_outline,
                color: theme.colorScheme.primary,
                size: 18,
              ),
              const SizedBox(width: Spacing.sm),
              Expanded(child: Text(message, style: theme.textTheme.bodySmall)),
            ],
          ),
        ),
      ),
    );
  }
}

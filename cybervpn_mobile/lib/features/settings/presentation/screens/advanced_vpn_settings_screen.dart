import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

/// Advanced transport tuning screen for fragmentation, mux, and IP family.
class AdvancedVpnSettingsScreen extends ConsumerWidget {
  const AdvancedVpnSettingsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncSettings = ref.watch(settingsProvider);

    final content = asyncSettings.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) =>
          const Center(child: Text('Failed to load advanced settings')),
      data: (settings) => _AdvancedVpnSettingsContent(settings: settings),
    );

    if (embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: const Text('Advanced')),
      body: content,
    );
  }
}

class _AdvancedVpnSettingsContent extends ConsumerWidget {
  const _AdvancedVpnSettingsContent({required this.settings});

  final AppSettings settings;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(settingsProvider.notifier);
    final supportMatrix = ref.watch(vpnSettingsSupportMatrixProvider);

    return ListView(
      children: [
        if (supportMatrix.advancedNoticeMessage case final message?)
          _CapabilityNotice(
            key: const Key('advanced_settings_notice'),
            message: message,
          ),
        if (supportMatrix.proxyOnlyMode.isVisible)
          SettingsSection(
            title: 'Mode',
            children: [
              SettingsTile.info(
                key: const Key('info_vpn_run_mode'),
                title: 'Current mode',
                subtitle: _withSupportHint(
                  _vpnRunModeLabel(settings.vpnRunMode),
                  supportMatrix.proxyOnlyMode,
                ),
              ),
              SettingsTile.radio(
                key: const Key('radio_vpn_run_mode_vpn'),
                title: 'VPN',
                subtitle:
                    'Run the VPN tunnel and route device traffic through it.',
                value: VpnRunMode.vpn,
                groupValue: settings.vpnRunMode,
                onChanged: supportMatrix.proxyOnlyMode.isAvailable
                    ? (_) => notifier.updateVpnRunMode(VpnRunMode.vpn)
                    : null,
              ),
              SettingsTile.radio(
                key: const Key('radio_vpn_run_mode_proxy_only'),
                title: 'Proxy only',
                subtitle:
                    'Start the Xray proxy without creating the full device VPN tunnel.',
                value: VpnRunMode.proxyOnly,
                groupValue: settings.vpnRunMode,
                onChanged: supportMatrix.proxyOnlyMode.isAvailable
                    ? (_) => notifier.updateVpnRunMode(VpnRunMode.proxyOnly)
                    : null,
              ),
            ],
          ),
        if (supportMatrix.sniffing.isVisible)
          SettingsSection(
            title: 'Traffic analysis',
            children: [
              SettingsTile.toggle(
                key: const Key('toggle_sniffing'),
                title: 'Packet analysis',
                subtitle: _withSupportHint(
                  'Enable Xray sniffing on supported inbounds before routing outbound traffic.',
                  supportMatrix.sniffing,
                ),
                value: settings.sniffingEnabled,
                onChanged: supportMatrix.sniffing.isAvailable
                    ? (_) => notifier.updateSniffing(!settings.sniffingEnabled)
                    : null,
              ),
            ],
          ),
        SettingsSection(
          title: 'Transport features',
          children: [
            if (supportMatrix.fragmentation.isVisible)
              SettingsTile.toggle(
                key: const Key('toggle_fragmentation'),
                title: 'Use Fragmentation',
                subtitle: _withSupportHint(
                  'Split packets on supported transports to reduce active probing.',
                  supportMatrix.fragmentation,
                ),
                value: settings.fragmentationEnabled,
                onChanged: (_) => notifier.updateFragmentation(
                  !settings.fragmentationEnabled,
                ),
              ),
            if (supportMatrix.mux.isVisible)
              SettingsTile.toggle(
                key: const Key('toggle_mux'),
                title: 'Use Mux',
                subtitle: _withSupportHint(
                  'Reuse tunnel connections when the active configuration supports multiplexing.',
                  supportMatrix.mux,
                ),
                value: settings.muxEnabled,
                onChanged: (_) => notifier.updateMux(!settings.muxEnabled),
              ),
          ],
        ),
        if (supportMatrix.preferredIpType.isVisible)
          SettingsSection(
            title: 'Preferred IP Type',
            children: [
              SettingsTile.info(
                key: const Key('info_preferred_ip_type'),
                title: 'Current selection',
                subtitle: _withSupportHint(
                  _preferredIpTypeLabel(settings.preferredIpType),
                  supportMatrix.preferredIpType,
                ),
              ),
              SettingsTile.radio(
                key: const Key('radio_ip_type_auto'),
                title: 'Auto',
                value: PreferredIpType.auto,
                groupValue: settings.preferredIpType,
                onChanged: (_) =>
                    notifier.updatePreferredIpType(PreferredIpType.auto),
              ),
              SettingsTile.radio(
                key: const Key('radio_ip_type_ipv4'),
                title: 'IPv4 only',
                value: PreferredIpType.ipv4,
                groupValue: settings.preferredIpType,
                onChanged: (_) =>
                    notifier.updatePreferredIpType(PreferredIpType.ipv4),
              ),
              SettingsTile.radio(
                key: const Key('radio_ip_type_ipv6'),
                title: 'IPv6 only',
                value: PreferredIpType.ipv6,
                groupValue: settings.preferredIpType,
                onChanged: (_) =>
                    notifier.updatePreferredIpType(PreferredIpType.ipv6),
              ),
            ],
          ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );
  }

  String _withSupportHint(String baseText, VpnSettingsFeatureSupport support) {
    if (support.message == null || support.message!.isEmpty) {
      return baseText;
    }
    return '$baseText ${support.message}';
  }

  String _preferredIpTypeLabel(PreferredIpType ipType) {
    return switch (ipType) {
      PreferredIpType.auto => 'Auto',
      PreferredIpType.ipv4 => 'IPv4',
      PreferredIpType.ipv6 => 'IPv6',
    };
  }

  String _vpnRunModeLabel(VpnRunMode mode) {
    return switch (mode) {
      VpnRunMode.vpn => 'VPN',
      VpnRunMode.proxyOnly => 'Proxy only',
    };
  }
}

class _CapabilityNotice extends StatelessWidget {
  const _CapabilityNotice({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        Spacing.md,
        Spacing.sm,
        Spacing.md,
        Spacing.sm,
      ),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(Radii.lg),
        ),
        child: Padding(
          padding: const EdgeInsets.all(Spacing.md),
          child: Text(message),
        ),
      ),
    );
  }
}

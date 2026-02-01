import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/constants/vpn_constants.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

// ---------------------------------------------------------------------------
// VpnSettingsScreen
// ---------------------------------------------------------------------------

/// VPN settings sub-screen with protocol picker, auto-connect toggles,
/// kill switch, split tunneling, DNS picker, and MTU configuration.
///
/// All changes are persisted via [settingsProvider] and take effect on the
/// next VPN connection.
class VpnSettingsScreen extends ConsumerStatefulWidget {
  const VpnSettingsScreen({super.key});

  @override
  ConsumerState<VpnSettingsScreen> createState() => _VpnSettingsScreenState();
}

class _VpnSettingsScreenState extends ConsumerState<VpnSettingsScreen> {
  late final TextEditingController _customDnsController;
  late final TextEditingController _mtuController;

  @override
  void initState() {
    super.initState();
    _customDnsController = TextEditingController();
    _mtuController = TextEditingController();
  }

  @override
  void dispose() {
    _customDnsController.dispose();
    _mtuController.dispose();
    super.dispose();
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  /// Returns a human-readable label for the [PreferredProtocol].
  String _protocolLabel(PreferredProtocol protocol) {
    return switch (protocol) {
      PreferredProtocol.auto => 'Auto',
      PreferredProtocol.vlessReality => 'VLESS Reality',
      PreferredProtocol.vlessXhttp => 'VLESS XHTTP',
      PreferredProtocol.vlessWsTls => 'VLESS WS+TLS',
    };
  }

  /// Returns a human-readable label for the [DnsProvider].
  String _dnsLabel(DnsProvider dns) {
    return switch (dns) {
      DnsProvider.system => 'System',
      DnsProvider.cloudflare => 'Cloudflare (1.1.1.1)',
      DnsProvider.google => 'Google (8.8.8.8)',
      DnsProvider.quad9 => 'Quad9 (9.9.9.9)',
      DnsProvider.custom => 'Custom',
    };
  }

  /// Shows a warning dialog before enabling the kill switch.
  Future<bool> _showKillSwitchWarning() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Enable Kill Switch?'),
        content: const Text(
          'When enabled, all internet traffic will be blocked if the VPN '
          'connection drops unexpectedly. This protects your privacy but '
          'may temporarily prevent internet access.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Enable'),
          ),
        ],
      ),
    );
    return confirmed ?? false;
  }

  // ── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final asyncSettings = ref.watch(settingsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('VPN Settings'),
      ),
      body: asyncSettings.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _buildError(error),
        data: _buildBody,
      ),
    );
  }

  // ── Error state ────────────────────────────────────────────────────────

  Widget _buildError(Object error) {
    final theme = Theme.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
          const SizedBox(height: 12),
          Text('Failed to load settings', style: theme.textTheme.bodyLarge),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: () => ref.invalidate(settingsProvider),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  // ── Data state ─────────────────────────────────────────────────────────

  Widget _buildBody(AppSettings settings) {
    // Sync text controllers with current settings values.
    if (_customDnsController.text != (settings.customDns ?? '')) {
      _customDnsController.text = settings.customDns ?? '';
    }
    if (_mtuController.text != settings.mtuValue.toString()) {
      _mtuController.text = settings.mtuValue.toString();
    }

    return ListView(
      children: [
        // --- Protocol Preference ---
        _buildProtocolSection(settings),

        // --- Auto-Connect ---
        _buildAutoConnectSection(settings),

        // --- Security ---
        _buildSecuritySection(settings),

        // --- DNS Configuration ---
        _buildDnsSection(settings),

        // --- Advanced ---
        _buildAdvancedSection(settings),

        // --- Info notice ---
        _buildConnectionNotice(),

        // Bottom padding
        const SizedBox(height: 80),
      ],
    );
  }

  // ── Protocol Preference ────────────────────────────────────────────────

  Widget _buildProtocolSection(AppSettings settings) {
    final notifier = ref.read(settingsProvider.notifier);

    return SettingsSection(
      title: 'Protocol Preference',
      children: [
        for (final protocol in PreferredProtocol.values)
          SettingsTile.radio(
            key: Key('radio_protocol_${protocol.name}'),
            title: _protocolLabel(protocol),
            value: protocol,
            groupValue: settings.preferredProtocol,
            onChanged: (_) => notifier.updateProtocol(protocol),
          ),
      ],
    );
  }

  // ── Auto-Connect ───────────────────────────────────────────────────────

  Widget _buildAutoConnectSection(AppSettings settings) {
    final notifier = ref.read(settingsProvider.notifier);

    return SettingsSection(
      title: 'Auto-Connect',
      children: [
        SettingsTile.toggle(
          key: const Key('toggle_auto_connect_launch'),
          title: 'Auto-connect on launch',
          subtitle: 'Connect to VPN when the app starts',
          value: settings.autoConnectOnLaunch,
          onChanged: (_) => notifier.toggleAutoConnect(),
        ),
        SettingsTile.toggle(
          key: const Key('toggle_auto_connect_wifi'),
          title: 'Auto-connect on untrusted WiFi',
          subtitle: 'Automatically connect when joining open networks',
          value: settings.autoConnectUntrustedWifi,
          onChanged: (_) => notifier.toggleAutoConnectUntrustedWifi(),
        ),
      ],
    );
  }

  // ── Security ───────────────────────────────────────────────────────────

  Widget _buildSecuritySection(AppSettings settings) {
    final notifier = ref.read(settingsProvider.notifier);

    return SettingsSection(
      title: 'Security',
      children: [
        SettingsTile.toggle(
          key: const Key('toggle_kill_switch'),
          title: 'Kill switch',
          subtitle: 'Block traffic if VPN disconnects unexpectedly',
          value: settings.killSwitch,
          onChanged: (dynamic newValue) async {
            final bool enabled = newValue as bool;
            if (enabled) {
              final confirmed = await _showKillSwitchWarning();
              if (!confirmed) return;
            }
            notifier.toggleKillSwitch();
          },
        ),
      ],
    );
  }

  // ── DNS Configuration ──────────────────────────────────────────────────

  Widget _buildDnsSection(AppSettings settings) {
    final notifier = ref.read(settingsProvider.notifier);

    return SettingsSection(
      title: 'DNS Provider',
      children: [
        for (final dns in DnsProvider.values)
          SettingsTile.radio(
            key: Key('radio_dns_${dns.name}'),
            title: _dnsLabel(dns),
            value: dns,
            groupValue: settings.dnsProvider,
            onChanged: (_) => notifier.updateDns(
              provider: dns,
              customDns: dns == DnsProvider.custom ? settings.customDns : null,
            ),
          ),

        // Custom DNS input (visible when Custom is selected)
        if (settings.dnsProvider == DnsProvider.custom)
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.md,
              vertical: Spacing.sm,
            ),
            child: TextField(
              key: const Key('input_custom_dns'),
              controller: _customDnsController,
              decoration: const InputDecoration(
                labelText: 'Custom DNS address',
                hintText: 'e.g. 1.0.0.1',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.url,
              onSubmitted: (value) => notifier.updateDns(
                provider: DnsProvider.custom,
                customDns: value,
              ),
            ),
          ),
      ],
    );
  }

  // ── Advanced ───────────────────────────────────────────────────────────

  Widget _buildAdvancedSection(AppSettings settings) {
    final notifier = ref.read(settingsProvider.notifier);

    return SettingsSection(
      title: 'Advanced',
      children: [
        // Split tunneling toggle
        SettingsTile.toggle(
          key: const Key('toggle_split_tunneling'),
          title: 'Split tunneling',
          subtitle: 'Choose which apps use the VPN',
          value: settings.splitTunneling,
          onChanged: (_) => notifier.toggleSplitTunneling(),
        ),

        // MTU selection
        SettingsTile.radio(
          key: const Key('radio_mtu_auto'),
          title: 'MTU: Auto',
          subtitle: 'Automatically determine optimal packet size',
          value: MtuMode.auto,
          groupValue: settings.mtuMode,
          onChanged: (_) => notifier.updateMtu(mode: MtuMode.auto),
        ),
        SettingsTile.radio(
          key: const Key('radio_mtu_manual'),
          title: 'MTU: Manual',
          subtitle: 'Set a custom MTU value',
          value: MtuMode.manual,
          groupValue: settings.mtuMode,
          onChanged: (_) => notifier.updateMtu(mode: MtuMode.manual),
        ),

        // Manual MTU input (visible when Manual is selected)
        if (settings.mtuMode == MtuMode.manual)
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.md,
              vertical: Spacing.sm,
            ),
            child: TextField(
              key: const Key('input_mtu_value'),
              controller: _mtuController,
              decoration: const InputDecoration(
                labelText: 'MTU value',
                hintText: '1280-1500',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
              onSubmitted: (value) {
                final parsed = int.tryParse(value);
                if (parsed != null &&
                    parsed >= VpnConstants.minMtu &&
                    parsed <= VpnConstants.maxMtu) {
                  notifier.updateMtu(
                    mode: MtuMode.manual,
                    mtuValue: parsed,
                  );
                }
              },
            ),
          ),
      ],
    );
  }

  // ── Connection notice ──────────────────────────────────────────────────

  Widget _buildConnectionNotice() {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.lg,
      ),
      child: Row(
        children: [
          Icon(
            Icons.info_outline,
            size: 16,
            color: theme.colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: Spacing.sm),
          Expanded(
            child: Text(
              'Changes apply on next connection',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

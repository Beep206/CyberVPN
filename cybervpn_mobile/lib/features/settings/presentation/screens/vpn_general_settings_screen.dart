import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/constants/vpn_constants.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/network/wifi_monitor_service.dart';
import 'package:cybervpn_mobile/features/settings/data/datasources/android_system_integration_service.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/domain/services/vpn_settings_support_matrix.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/android_system_integration_providers.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

/// General VPN settings screen for protocol, auto-connect, DNS, and MTU.
class VpnGeneralSettingsScreen extends ConsumerStatefulWidget {
  const VpnGeneralSettingsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  ConsumerState<VpnGeneralSettingsScreen> createState() =>
      _VpnGeneralSettingsScreenState();
}

class _VpnGeneralSettingsScreenState
    extends ConsumerState<VpnGeneralSettingsScreen> {
  late final TextEditingController _customDnsController;
  late final TextEditingController _localDnsPortController;
  late final TextEditingController _mtuController;
  late final TextEditingController _serverResolveDohController;
  late final TextEditingController _serverResolveDnsIpController;

  @override
  void initState() {
    super.initState();
    _customDnsController = TextEditingController();
    _localDnsPortController = TextEditingController();
    _mtuController = TextEditingController();
    _serverResolveDohController = TextEditingController();
    _serverResolveDnsIpController = TextEditingController();
  }

  @override
  void dispose() {
    _customDnsController.dispose();
    _localDnsPortController.dispose();
    _mtuController.dispose();
    _serverResolveDohController.dispose();
    _serverResolveDnsIpController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final asyncSettings = ref.watch(settingsProvider);
    final l10n = AppLocalizations.of(context);

    final content = asyncSettings.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => _buildError(),
      data: _buildBody,
    );

    if (widget.embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.settingsVpn)),
      body: content,
    );
  }

  Widget _buildError() {
    return Center(
      child: FilledButton.tonal(
        onPressed: () => ref.invalidate(settingsProvider),
        child: Text(AppLocalizations.of(context).retry),
      ),
    );
  }

  Widget _buildBody(AppSettings settings) {
    final supportMatrix = ref.watch(vpnSettingsSupportMatrixProvider);
    final lanStatus = ref.watch(lanProxyStatusProvider(settings.allowLanConnections));
    final appAutoStartStatus = ref.watch(
      appAutoStartStatusProvider(settings.appAutoStart),
    );

    if (_customDnsController.text != (settings.customDns ?? '')) {
      _customDnsController.text = settings.customDns ?? '';
    }
    if (_mtuController.text != settings.mtuValue.toString()) {
      _mtuController.text = settings.mtuValue.toString();
    }
    if (_localDnsPortController.text != settings.localDnsPort.toString()) {
      _localDnsPortController.text = settings.localDnsPort.toString();
    }
    if (_serverResolveDohController.text !=
        (settings.serverAddressResolveDohUrl ?? '')) {
      _serverResolveDohController.text =
          settings.serverAddressResolveDohUrl ?? '';
    }
    if (_serverResolveDnsIpController.text !=
        (settings.serverAddressResolveDnsIp ?? '')) {
      _serverResolveDnsIpController.text =
          settings.serverAddressResolveDnsIp ?? '';
    }

    return ListView(
      children: [
        _buildProtocolSection(settings),
        _buildAutoConnectSection(settings),
        _buildSecuritySection(settings),
        _buildDnsSection(settings, supportMatrix),
        _buildMtuSection(settings, supportMatrix.manualMtu.isVisible),
        if (!supportMatrix.manualMtu.isVisible)
          _buildNotice(
            key: const Key('vpn_general_mtu_notice'),
            message:
                supportMatrix.manualMtu.message ??
                'Manual MTU is unavailable on this platform.',
          ),
        _buildLanAccessSection(settings, lanStatus),
        _buildAppAutoStartSection(settings, appAutoStartStatus),
        _buildPlatformIntegrationSection(),
        _buildConnectionNotice(),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );
  }

  Widget _buildProtocolSection(AppSettings settings) {
    final notifier = ref.read(settingsProvider.notifier);
    final l10n = AppLocalizations.of(context);

    return SettingsSection(
      title: l10n.settingsVpnProtocolPreference,
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

  Widget _buildAutoConnectSection(AppSettings settings) {
    final notifier = ref.read(settingsProvider.notifier);
    final l10n = AppLocalizations.of(context);

    return SettingsSection(
      title: l10n.settingsAutoConnectLabel,
      children: [
        SettingsTile.toggle(
          key: const Key('toggle_auto_connect_launch'),
          title: l10n.settingsAutoConnectOnLaunchLabel,
          subtitle: l10n.settingsAutoConnectOnLaunchDescription,
          value: settings.autoConnectOnLaunch,
          onChanged: (_) => notifier.toggleAutoConnect(),
        ),
        SettingsTile.toggle(
          key: const Key('toggle_auto_connect_wifi'),
          title: l10n.settingsAutoConnectUntrustedWifiLabel,
          subtitle: l10n.settingsAutoConnectUntrustedWifiDescription,
          value: settings.autoConnectUntrustedWifi,
          onChanged: (_) => notifier.toggleAutoConnectUntrustedWifi(),
        ),
      ],
    );
  }

  Widget _buildSecuritySection(AppSettings settings) {
    final notifier = ref.read(settingsProvider.notifier);
    final l10n = AppLocalizations.of(context);

    return SettingsSection(
      title: l10n.settingsSecuritySection,
      children: [
        SettingsTile.toggle(
          key: const Key('toggle_kill_switch'),
          title: l10n.settingsKillSwitchLabel,
          subtitle: l10n.settingsKillSwitchSubtitle,
          value: settings.killSwitch,
          onChanged: (_) => notifier.toggleKillSwitch(),
        ),
      ],
    );
  }

  Widget _buildDnsSection(
    AppSettings settings,
    VpnSettingsSupportMatrix supportMatrix,
  ) {
    final notifier = ref.read(settingsProvider.notifier);
    final l10n = AppLocalizations.of(context);
    final canUseLocalDns = supportMatrix.localDns.isAvailable;
    final canResolveServerAddress = supportMatrix.serverResolve.isAvailable;

    return SettingsSection(
      title: 'DNS & Resolve',
      children: [
        const SettingsTile.info(
          key: Key('info_dns_precedence'),
          title: 'DNS precedence',
          subtitle:
              'DNS from JSON takes priority over app-level DNS. Otherwise the selected DNS provider is applied. Local DNS remains unavailable until the mobile bridge supports it.',
        ),
        for (final dnsProvider in DnsProvider.values)
          SettingsTile.radio(
            key: Key('radio_dns_${dnsProvider.name}'),
            title: _dnsLabel(dnsProvider),
            value: dnsProvider,
            groupValue: settings.dnsProvider,
            onChanged: (_) => notifier.updateDns(provider: dnsProvider),
          ),
        if (settings.dnsProvider == DnsProvider.custom)
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.md,
              vertical: Spacing.sm,
            ),
            child: TextField(
              key: const Key('input_custom_dns'),
              controller: _customDnsController,
              decoration: InputDecoration(
                labelText: l10n.settingsDnsCustomAddressLabel,
                hintText: l10n.settingsDnsCustomAddressHint,
                border: const OutlineInputBorder(),
              ),
              keyboardType: TextInputType.url,
              onSubmitted: (value) => notifier.updateDns(
                provider: DnsProvider.custom,
                customDns: value,
              ),
            ),
          ),
        SettingsTile.toggle(
          key: const Key('toggle_use_dns_from_json'),
          title: 'Use DNS from JSON',
          subtitle:
              'Preserve DNS servers from the imported JSON config when available.',
          value: settings.useDnsFromJson,
          onChanged: (_) =>
              notifier.updateUseDnsFromJson(!settings.useDnsFromJson),
        ),
        if (supportMatrix.localDns.isVisible)
          if (canUseLocalDns)
            SettingsTile.toggle(
              key: const Key('toggle_use_local_dns'),
              title: 'Use local DNS',
              subtitle: _withSupportHint(
                'Route tunnel DNS to a local resolver endpoint once the runtime bridge supports it.',
                supportMatrix.localDns,
              ),
              value: settings.useLocalDns,
              onChanged: (_) => notifier.updateLocalDnsSettings(
                enabled: !settings.useLocalDns,
              ),
            )
          else
            SettingsTile.info(
              key: const Key('info_local_dns_unavailable'),
              title: 'Use local DNS',
              subtitle:
                  supportMatrix.localDns.message ??
                  'Local DNS is unavailable on this platform.',
            ),
        if (canUseLocalDns && settings.useLocalDns)
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.md,
              vertical: Spacing.sm,
            ),
            child: TextField(
              key: const Key('input_local_dns_port'),
              controller: _localDnsPortController,
              decoration: const InputDecoration(
                labelText: 'Local DNS port',
                hintText: '1053',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
              onSubmitted: (value) {
                final parsed = int.tryParse(value);
                if (parsed != null && parsed > 0 && parsed <= 65535) {
                  unawaited(
                    notifier.updateLocalDnsSettings(
                      enabled: true,
                      port: parsed,
                    ),
                  );
                }
              },
            ),
          ),
        if (supportMatrix.serverResolve.isVisible)
          SettingsTile.toggle(
            key: const Key('toggle_server_address_resolve'),
            title: 'Resolve server before connect',
            subtitle: _withSupportHint(
              'Resolve the server hostname before connect and choose the fastest IP when multiple addresses are returned.',
              supportMatrix.serverResolve,
            ),
            value: settings.serverAddressResolveEnabled,
            onChanged: canResolveServerAddress
                ? (_) => notifier.updateServerAddressResolve(
                    enabled: !settings.serverAddressResolveEnabled,
                    dohUrl: _serverResolveDohController.text.trim().isEmpty
                        ? null
                        : _serverResolveDohController.text.trim(),
                    dnsIp: _serverResolveDnsIpController.text.trim().isEmpty
                        ? null
                        : _serverResolveDnsIpController.text.trim(),
                  )
                : null,
          ),
        if (canResolveServerAddress && settings.serverAddressResolveEnabled)
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.md,
              vertical: Spacing.sm,
            ),
            child: Column(
              children: [
                TextField(
                  key: const Key('input_server_resolve_doh_url'),
                  controller: _serverResolveDohController,
                  decoration: const InputDecoration(
                    labelText: 'DoH URL',
                    hintText: 'https://dns.google/resolve',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.url,
                  onSubmitted: (_) => notifier.updateServerAddressResolve(
                    enabled: true,
                    dohUrl: _serverResolveDohController.text.trim().isEmpty
                        ? null
                        : _serverResolveDohController.text.trim(),
                    dnsIp: _serverResolveDnsIpController.text.trim().isEmpty
                        ? null
                        : _serverResolveDnsIpController.text.trim(),
                  ),
                ),
                const SizedBox(height: Spacing.sm),
                TextField(
                  key: const Key('input_server_resolve_dns_ip'),
                  controller: _serverResolveDnsIpController,
                  decoration: const InputDecoration(
                    labelText: 'Resolver IP override',
                    hintText: '77.88.8.8',
                    border: OutlineInputBorder(),
                  ),
                  keyboardType: TextInputType.url,
                  onSubmitted: (_) => notifier.updateServerAddressResolve(
                    enabled: true,
                    dohUrl: _serverResolveDohController.text.trim().isEmpty
                        ? null
                        : _serverResolveDohController.text.trim(),
                    dnsIp: _serverResolveDnsIpController.text.trim().isEmpty
                        ? null
                        : _serverResolveDnsIpController.text.trim(),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  Widget _buildMtuSection(AppSettings settings, bool showManualMtu) {
    final notifier = ref.read(settingsProvider.notifier);
    final l10n = AppLocalizations.of(context);

    return SettingsSection(
      title: 'MTU',
      children: [
        SettingsTile.radio(
          key: const Key('radio_mtu_auto'),
          title: 'MTU: Auto',
          subtitle: 'Use the platform default MTU for the VPN tunnel.',
          value: MtuMode.auto,
          groupValue: settings.mtuMode,
          onChanged: (_) => notifier.updateMtu(mode: MtuMode.auto),
        ),
        if (showManualMtu)
          SettingsTile.radio(
            key: const Key('radio_mtu_manual'),
            title: 'MTU: Manual',
            subtitle:
                'Set a custom MTU for troubleshooting or performance tuning.',
            value: MtuMode.manual,
            groupValue: settings.mtuMode,
            onChanged: (_) => notifier.updateMtu(mode: MtuMode.manual),
          ),
        if (showManualMtu && settings.mtuMode == MtuMode.manual)
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: Spacing.md,
              vertical: Spacing.sm,
            ),
            child: TextField(
              key: const Key('input_mtu_value'),
              controller: _mtuController,
              decoration: InputDecoration(
                labelText: l10n.settingsMtuValueLabel,
                hintText: l10n.settingsMtuValueHint,
                border: const OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
              onSubmitted: (value) {
                final parsed = int.tryParse(value);
                if (parsed != null &&
                    parsed >= VpnConstants.minMtu &&
                    parsed <= VpnConstants.maxMtu) {
                  unawaited(
                    notifier.updateMtu(mode: MtuMode.manual, mtuValue: parsed),
                  );
                }
              },
            ),
          ),
      ],
    );
  }

  Widget _buildPlatformIntegrationSection() {
    return SettingsSection(
      title: 'Background settings',
      children: [
        SettingsTile.navigation(
          key: const Key('nav_background_settings'),
          title: 'Open app settings',
          subtitle:
              'Open the OS settings page for background permissions, battery rules, and autostart controls.',
          leading: const Icon(Icons.open_in_new_outlined),
          onTap: () =>
              unawaited(ref.read(wifiMonitorServiceProvider).openAppSettings()),
        ),
      ],
    );
  }

  Widget _buildLanAccessSection(
    AppSettings settings,
    AsyncValue<LanProxyStatus> statusAsync,
  ) {
    final notifier = ref.read(settingsProvider.notifier);
    final service = ref.read(androidSystemIntegrationServiceProvider);
    final status = switch (statusAsync) {
      AsyncData(:final value) => value,
      _ => null,
    };

    if (!service.isSupported) {
      return const SettingsSection(
        title: 'Allow Connections from LAN',
        children: [
          SettingsTile.info(
            key: Key('info_allow_lan_unsupported'),
            title: 'Android only',
            subtitle:
                'LAN proxy access is available on Android where the local SOCKS5 and HTTP inbounds can bind to the Wi-Fi interface.',
          ),
        ],
      );
    }

    final addressLabel = status?.wifiIpv4 ?? status?.wifiIpv6;
    final addressSubtitle = addressLabel == null || addressLabel.isEmpty
        ? 'Join Wi-Fi to surface the current LAN address. Proxy ports become reachable while VPN is running.'
        : 'Devices on the same LAN can use $addressLabel while VPN is running.';

    return SettingsSection(
      title: 'Allow Connections from LAN',
      children: [
        SettingsTile.toggle(
          key: const Key('toggle_allow_lan_connections'),
          title: 'Allow connections from LAN',
          subtitle:
              'Expose the local SOCKS5 and HTTP proxy ports to devices on the same Wi-Fi network.',
          value: settings.allowLanConnections,
          onChanged: (_) =>
              notifier.updateAllowLanConnections(!settings.allowLanConnections),
        ),
        SettingsTile.info(
          key: const Key('info_allow_lan_address'),
          title: 'LAN address',
          subtitle: addressSubtitle,
        ),
        SettingsTile.info(
          key: const Key('info_allow_lan_socks_port'),
          title: 'SOCKS5 port',
          subtitle: '${status?.socksPort ?? 10807}',
        ),
        SettingsTile.info(
          key: const Key('info_allow_lan_http_port'),
          title: 'HTTP port',
          subtitle: '${status?.httpPort ?? 10808}',
        ),
        const SettingsTile.info(
          key: Key('info_allow_lan_notice'),
          title: 'Runtime behavior',
          subtitle:
              'LAN exposure is applied on the next VPN connect and keeps the Xray API inbound bound to localhost only.',
        ),
      ],
    );
  }

  Widget _buildAppAutoStartSection(
    AppSettings settings,
    AsyncValue<AppAutoStartStatus> statusAsync,
  ) {
    final notifier = ref.read(settingsProvider.notifier);
    final service = ref.read(androidSystemIntegrationServiceProvider);
    final status = switch (statusAsync) {
      AsyncData(:final value) => value,
      _ => null,
    };

    if (!service.isSupported) {
      return const SettingsSection(
        title: 'App Auto Start',
        children: [
          SettingsTile.info(
            key: Key('info_app_auto_start_unsupported'),
            title: 'Android only',
            subtitle:
                'App auto-start is OEM- and Android-specific, so this release only exposes the operational controls on Android.',
          ),
        ],
      );
    }

    final lastBootHandledAt = status?.lastBootHandledAt;
    final lastBootHandledLabel = lastBootHandledAt == null
        ? 'No boot event handled yet'
        : lastBootHandledAt.toLocal().toString();

    return SettingsSection(
      title: 'App Auto Start',
      children: [
        SettingsTile.toggle(
          key: const Key('toggle_app_auto_start'),
          title: 'Auto-start app',
          subtitle:
              'Arms the Android boot receiver and surfaces the OEM autostart settings needed to keep CyberVPN eligible after reboot.',
          value: settings.appAutoStart,
          onChanged: (_) {
            final nextValue = !settings.appAutoStart;
            unawaited(notifier.updateAppAutoStart(nextValue));
            unawaited(
              ref
                  .read(androidSystemIntegrationServiceProvider)
                  .syncAppAutoStartPreference(nextValue),
            );
          },
        ),
        SettingsTile.info(
          key: const Key('info_app_auto_start_status'),
          title: 'Receiver status',
          subtitle: status?.bootReceiverReady == true
              ? 'Boot receiver armed for ${status?.manufacturer ?? 'android'}.'
              : 'Boot receiver is not armed yet.',
        ),
        SettingsTile.info(
          key: const Key('info_app_auto_start_last_boot'),
          title: 'Last boot event',
          subtitle: lastBootHandledLabel,
        ),
        SettingsTile.info(
          key: const Key('info_app_auto_start_battery'),
          title: 'Battery optimization',
          subtitle: status?.batteryOptimizationIgnored == true
              ? 'Battery optimization is already ignored for CyberVPN.'
              : 'Disable battery optimization to improve post-reboot reliability.',
        ),
        SettingsTile.navigation(
          key: const Key('nav_app_auto_start_settings'),
          title: 'Open autostart settings',
          subtitle:
              'Jump to the OEM-specific autostart management screen when available.',
          leading: const Icon(Icons.directions_run_outlined),
          onTap: () => unawaited(
            ref.read(androidSystemIntegrationServiceProvider).openAppAutoStartSettings(),
          ),
        ),
        SettingsTile.navigation(
          key: const Key('nav_battery_optimization_settings'),
          title: 'Open battery optimization settings',
          subtitle:
              'Open the Android battery optimization controls for CyberVPN.',
          leading: const Icon(Icons.battery_saver_outlined),
          onTap: () => unawaited(
            ref
                .read(androidSystemIntegrationServiceProvider)
                .openBatteryOptimizationSettings(),
          ),
        ),
      ],
    );
  }

  Widget _buildNotice({required Key key, required String message}) {
    final theme = Theme.of(context);

    return Padding(
      key: key,
      padding: const EdgeInsets.fromLTRB(
        Spacing.md,
        Spacing.sm,
        Spacing.md,
        Spacing.sm,
      ),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(Radii.lg),
        ),
        child: Padding(
          padding: const EdgeInsets.all(Spacing.md),
          child: Text(message, style: theme.textTheme.bodySmall),
        ),
      ),
    );
  }

  String _withSupportHint(String baseText, VpnSettingsFeatureSupport support) {
    final message = support.message;
    if (message == null || message.isEmpty) {
      return baseText;
    }
    return '$baseText $message';
  }

  Widget _buildConnectionNotice() {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

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
              l10n.settingsChangesApplyOnNextConnection,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _protocolLabel(PreferredProtocol protocol) {
    return switch (protocol) {
      PreferredProtocol.auto => 'Auto',
      PreferredProtocol.vlessReality => 'VLESS Reality',
      PreferredProtocol.vlessXhttp => 'VLESS XHTTP',
      PreferredProtocol.vlessWsTls => 'VLESS WS+TLS',
    };
  }

  String _dnsLabel(DnsProvider dns) {
    return switch (dns) {
      DnsProvider.system => 'System',
      DnsProvider.cloudflare => 'Cloudflare (1.1.1.1)',
      DnsProvider.google => 'Google (8.8.8.8)',
      DnsProvider.quad9 => 'Quad9 (9.9.9.9)',
      DnsProvider.custom => 'Custom',
    };
  }
}

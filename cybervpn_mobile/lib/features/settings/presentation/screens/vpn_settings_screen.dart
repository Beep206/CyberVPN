import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/config_import/presentation/providers/config_import_provider.dart';
import 'package:cybervpn_mobile/features/settings/domain/entities/app_settings.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/settings_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/providers/vpn_settings_support_provider.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_section.dart';
import 'package:cybervpn_mobile/features/settings/presentation/widgets/settings_tile.dart';

/// VPN settings hub that exposes the modular Phase 5 information architecture.
class VpnSettingsScreen extends ConsumerWidget {
  const VpnSettingsScreen({super.key, this.embedded = false});

  final bool embedded;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncSettings = ref.watch(settingsProvider);
    final l10n = AppLocalizations.of(context);

    final content = asyncSettings.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (error, _) => _buildError(context, ref),
      data: (settings) => _buildBody(context, ref, settings),
    );

    if (embedded) {
      return content;
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.settingsVpn)),
      body: content,
    );
  }

  Widget _buildError(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
          const SizedBox(height: 12),
          Text(
            AppLocalizations.of(context).settingsLoadError,
            style: theme.textTheme.bodyLarge,
          ),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: () => ref.invalidate(settingsProvider),
            child: Text(AppLocalizations.of(context).retry),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(BuildContext context, WidgetRef ref, AppSettings settings) {
    final supportMatrix = ref.watch(vpnSettingsSupportMatrixProvider);
    final importedConfigs = ref.watch(importedConfigsProvider);
    final subscriptionMetadata = ref.watch(subscriptionUrlMetadataProvider);

    return ListView(
      children: [
        SettingsSection(
          title: 'Connection',
          children: [
            SettingsTile.navigation(
              key: const Key('nav_vpn_general_settings'),
              title: 'VPN Settings',
              subtitle: _generalSummary(settings),
              leading: const Icon(Icons.vpn_key_outlined),
              onTap: () => context.push('/settings/vpn/general'),
            ),
            SettingsTile.navigation(
              key: const Key('nav_vpn_routing_settings'),
              title: 'Routing',
              subtitle: _routingSummary(settings),
              leading: const Icon(Icons.route_outlined),
              onTap: () => context.push('/settings/vpn/routing'),
            ),
            if (supportMatrix.perAppProxy.isVisible)
              SettingsTile.navigation(
                key: const Key('nav_vpn_per_app_proxy_settings'),
                title: 'Per-App Proxy',
                subtitle: _perAppProxySummary(settings),
                leading: const Icon(Icons.apps_outlined),
                onTap: () => context.push('/settings/vpn/per-app-proxy'),
              ),
            SettingsTile.navigation(
              key: const Key('nav_vpn_advanced_settings'),
              title: 'Advanced',
              subtitle: _advancedSummary(settings),
              leading: const Icon(Icons.tune_outlined),
              onTap: () => context.push('/settings/vpn/advanced'),
            ),
          ],
        ),
        SettingsSection(
          title: 'Operations',
          children: [
            SettingsTile.navigation(
              key: const Key('nav_vpn_subscription_settings'),
              title: 'Subscriptions',
              subtitle: _subscriptionSummary(
                importedConfigCount: importedConfigs.length,
                subscriptionCount: subscriptionMetadata.length,
              ),
              leading: const Icon(Icons.cloud_sync_outlined),
              onTap: () => context.push('/settings/vpn/subscriptions'),
            ),
            SettingsTile.navigation(
              key: const Key('nav_vpn_ping_settings'),
              title: 'Ping',
              subtitle: _pingSummary(settings),
              leading: const Icon(Icons.network_ping_outlined),
              onTap: () => context.push('/settings/vpn/ping'),
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
                'Phase 5 reorganizes VPN controls into operational areas. '
                'Use General, Routing, Advanced, Subscriptions, and Ping to avoid one overloaded settings page.',
              ),
            ),
          ),
        ),
        SizedBox(height: Spacing.navBarClearance(context)),
      ],
    );
  }

  String _generalSummary(AppSettings settings) {
    final dnsSummary = settings.useDnsFromJson
        ? 'DNS from JSON'
        : '${_dnsLabel(settings.dnsProvider)} DNS';
    final resolveSummary = settings.serverAddressResolveEnabled
        ? 'Resolve on connect'
        : 'No pre-resolve';
    return '${_protocolLabel(settings.preferredProtocol)} • '
        '$dnsSummary • '
        '$resolveSummary • '
        '${settings.mtuMode == MtuMode.auto ? 'MTU Auto' : 'MTU ${settings.mtuValue}'}';
  }

  String _routingSummary(AppSettings settings) {
    if (!settings.routingEnabled) {
      return 'Routing disabled';
    }

    final activeProfile = settings.routingProfiles.where(
      (profile) => profile.id == settings.activeRoutingProfileId,
    );
    final activeProfileName = activeProfile.isNotEmpty
        ? activeProfile.first.name
        : 'No active profile';

    final excludedRoutesSummary = settings.bypassSubnets.isEmpty
        ? 'no excluded routes'
        : '${settings.bypassSubnets.length} excluded route(s)';

    return '$activeProfileName • $excludedRoutesSummary';
  }

  String _perAppProxySummary(AppSettings settings) {
    final count = settings.perAppProxyAppIds.length;
    return switch (settings.perAppProxyMode) {
      PerAppProxyMode.off => 'Proxy applies to all apps',
      PerAppProxyMode.proxySelected =>
        count == 0
            ? 'Only selected apps will use proxy'
            : '$count selected app(s) use proxy',
      PerAppProxyMode.bypassSelected =>
        count == 0
            ? 'Selected apps will bypass proxy'
            : '$count selected app(s) bypass proxy',
    };
  }

  String _advancedSummary(AppSettings settings) {
    final enabledFlags = [
      if (settings.vpnRunMode == VpnRunMode.proxyOnly) 'proxy-only',
      if (settings.sniffingEnabled) 'packet analysis',
      if (settings.fragmentationEnabled) 'fragmentation',
      if (settings.muxEnabled) 'mux',
    ];
    final base = enabledFlags.isEmpty
        ? 'No transport modifiers enabled'
        : enabledFlags.join(', ');
    return '$base • ${_preferredIpTypeLabel(settings.preferredIpType)}';
  }

  String _subscriptionSummary({
    required int importedConfigCount,
    required int subscriptionCount,
  }) {
    if (importedConfigCount == 0 && subscriptionCount == 0) {
      return 'No imported configs yet';
    }

    return '$subscriptionCount subscription source(s) • '
        '$importedConfigCount imported config(s)';
  }

  String _pingSummary(AppSettings settings) {
    final label = switch (settings.pingMode) {
      PingMode.tcp => 'TCP connect',
      PingMode.realDelay => 'Real delay',
      PingMode.proxyGet => 'Via proxy GET',
      PingMode.proxyHead => 'Via proxy HEAD',
      PingMode.icmp => 'ICMP',
    };
    final host = Uri.tryParse(settings.pingTestUrl)?.host;
    if (host == null || host.isEmpty) {
      return label;
    }
    return '$label • $host';
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
      DnsProvider.cloudflare => 'Cloudflare',
      DnsProvider.google => 'Google',
      DnsProvider.quad9 => 'Quad9',
      DnsProvider.custom => 'Custom',
    };
  }

  String _preferredIpTypeLabel(PreferredIpType ipType) {
    return switch (ipType) {
      PreferredIpType.auto => 'IP Auto',
      PreferredIpType.ipv4 => 'IPv4 only',
      PreferredIpType.ipv6 => 'IPv6 only',
    };
  }
}

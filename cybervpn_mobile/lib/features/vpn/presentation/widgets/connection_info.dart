import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/servers/domain/entities/server_entity.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';
import 'package:cybervpn_mobile/shared/widgets/flag_widget.dart';

/// Displays connection details below the connect button:
/// server name, country flag emoji, city, active protocol chip,
/// connection duration timer, and IP address (when available).
class ConnectionInfo extends ConsumerWidget {
  const ConnectionInfo({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncState = ref.watch(vpnConnectionProvider);
    final vpnState = asyncState.value ?? const VpnDisconnected();
    final server = ref.watch(currentServerProvider);
    final protocol = ref.watch(activeProtocolProvider);
    final duration = ref.watch(sessionDurationProvider);
    final stats = ref.watch(vpnStatsProvider);

    if (server == null && vpnState is VpnDisconnected) {
      return const _NoServerSelected();
    }

    return AnimatedSwitcher(
      duration: AnimDurations.normal,
      child: Column(
        key: ValueKey(server?.id ?? 'none'),
        mainAxisSize: MainAxisSize.min,
        children: [
          // Server name + flag
          if (server != null) _ServerRow(server: server),

          const SizedBox(height: 8),

          // Protocol chip
          if (protocol != null) _ProtocolChip(protocol: protocol),

          const SizedBox(height: 12),

          // Duration timer (only when connected / reconnecting)
          if (vpnState.isConnected ||
              vpnState.isReconnecting ||
              vpnState.isConnecting)
            _DurationDisplay(duration: duration),

          const SizedBox(height: 6),

          // IP address
          if (stats?.ipAddress != null && stats!.ipAddress!.isNotEmpty)
            _IpAddressDisplay(ip: stats.ipAddress!),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Sub-widgets
// ---------------------------------------------------------------------------

class _NoServerSelected extends StatelessWidget {
  const _NoServerSelected();

  @override
  Widget build(BuildContext context) {
    return Text(
      AppLocalizations.of(context).connectionSelectServer,
      style: TextStyle(
        color: Colors.grey.shade500,
        fontSize: 14,
      ),
    );
  }
}

class _ServerRow extends StatelessWidget {
  final ServerEntity server;

  const _ServerRow({required this.server});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final semanticLabel = l10n.a11yConnectedToServer(server.name, server.city, server.countryName);

    return Semantics(
      label: semanticLabel,
      hint: 'Shows the currently selected server',
      readOnly: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          ExcludeSemantics(
            child: FlagWidget(
              countryCode: server.countryCode,
              size: FlagSize.medium,
              heroTag: 'server_flag_${server.id}',
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  server.name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                if (server.city.isNotEmpty)
                  Text(
                    '${server.city}, ${server.countryName}',
                    style: TextStyle(
                      color: Colors.grey.shade400,
                      fontSize: 12,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

}

class _ProtocolChip extends StatelessWidget {
  final VpnProtocol protocol;

  const _ProtocolChip({required this.protocol});

  @override
  Widget build(BuildContext context) {
    final label = _protocolDisplayName(protocol);
    final color = _protocolColor(protocol);

    return Semantics(
      label: AppLocalizations.of(context).a11yUsingProtocol(label),
      hint: 'Shows the active VPN protocol',
      readOnly: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: color.withValues(alpha: 0.4)),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: color,
            fontSize: 12,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.8,
          ),
        ),
      ),
    );
  }

  static String _protocolDisplayName(VpnProtocol protocol) {
    return switch (protocol) {
      VpnProtocol.vless => 'Reality',
      VpnProtocol.vmess => 'XHTTP',
      VpnProtocol.trojan => 'WS-TLS',
      VpnProtocol.shadowsocks => 'Shadowsocks',
    };
  }

  static Color _protocolColor(VpnProtocol protocol) {
    return switch (protocol) {
      VpnProtocol.vless => const Color(0xFF00E5FF), // cyan
      VpnProtocol.vmess => const Color(0xFFFF9100), // orange
      VpnProtocol.trojan => const Color(0xFFE040FB), // purple
      VpnProtocol.shadowsocks => const Color(0xFF76FF03), // lime
    };
  }
}

class _DurationDisplay extends StatelessWidget {
  final String duration;

  const _DurationDisplay({required this.duration});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: AppLocalizations.of(context).a11yConnectionDurationValue(duration),
      hint: 'Shows how long you have been connected',
      readOnly: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          ExcludeSemantics(
            child: Icon(Icons.timer_outlined,
                color: Colors.grey.shade400, size: 16),
          ),
          const SizedBox(width: 4),
          Text(
            duration,
            style: TextStyle(
              color: Colors.grey.shade300,
              fontSize: 14,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
        ],
      ),
    );
  }
}

class _IpAddressDisplay extends StatelessWidget {
  final String ip;

  const _IpAddressDisplay({required this.ip});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: AppLocalizations.of(context).a11yIpAddress(ip),
      hint: 'Shows your current public IP address',
      readOnly: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          ExcludeSemantics(
            child: Icon(Icons.language, color: Colors.grey.shade500, size: 14),
          ),
          const SizedBox(width: 4),
          Flexible(
            child: Text(
              ip,
              style: TextStyle(
                color: Colors.grey.shade500,
                fontSize: 12,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

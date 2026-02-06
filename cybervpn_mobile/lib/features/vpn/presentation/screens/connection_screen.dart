import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connect_button.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connection_info.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/speed_indicator.dart';
import 'package:cybervpn_mobile/shared/services/tooltip_preferences_service.dart';
import 'package:cybervpn_mobile/shared/widgets/feature_tooltip.dart';

/// Main VPN connection screen.
///
/// Layout (top to bottom):
/// 1. Subscription status badge (top bar area).
/// 2. Large animated connect button (center).
/// 3. Server name, country flag, active protocol badge.
/// 4. Upload/download speed gauges, session duration, data usage.
class ConnectionScreen extends ConsumerStatefulWidget {
  const ConnectionScreen({super.key});

  @override
  ConsumerState<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends ConsumerState<ConnectionScreen> {
  /// Global key for the speed indicator to position the tooltip.
  final GlobalKey _speedIndicatorKey = GlobalKey();

  /// Service to track shown tooltips.
  final TooltipPreferencesService _tooltipService = TooltipPreferencesService();

  @override
  void initState() {
    super.initState();
    // Show tooltip after first frame renders
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_showTooltipIfNeeded());
    });
  }

  Future<void> _showTooltipIfNeeded() async {
    const tooltipId = 'connection_speed_monitor';
    final hasShown = await _tooltipService.hasShownTooltip(tooltipId);

    if (!hasShown && mounted) {
      FeatureTooltip.show(
        context: context,
        targetKey: _speedIndicatorKey,
        message: AppLocalizations.of(context).connectionMonitorSpeedTooltip,
        position: TooltipPosition.top,
        onDismiss: () async {
          await _tooltipService.markTooltipAsShown(tooltipId);
        },
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final asyncState = ref.watch(vpnConnectionProvider);
    final vpnState = asyncState.value ?? const VpnDisconnected();
    final duration = ref.watch(sessionDurationProvider);
    final usage = ref.watch(sessionUsageProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF0A0E1A),
      body: SafeArea(
        child: Column(
          children: [
            // ── Top bar with subscription badge ──────────────────────────
            _TopBar(vpnState: vpnState),

            // ── Main content (centered connect button + info) ────────────
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const SizedBox(height: 24),

                      // Connect button
                      const ConnectButton(),

                      const SizedBox(height: 28),

                      // Connection info (server, protocol, timer, IP)
                      const ConnectionInfo(),

                      const SizedBox(height: 36),

                      // Error message banner
                      if (vpnState is VpnError)
                        _ErrorBanner(message: vpnState.message),
                    ],
                  ),
                ),
              ),
            ),

            // ── Bottom section: speeds + session stats ───────────────────
            _BottomStatsSection(
              key: _speedIndicatorKey,
              vpnState: vpnState,
              duration: duration,
              totalUsage: usage.total,
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Top bar
// ---------------------------------------------------------------------------

class _TopBar extends StatelessWidget {
  final VpnConnectionState vpnState;

  const _TopBar({required this.vpnState});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final label = _statusLabel(vpnState, l10n);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          // Status indicator dot
          _StatusDot(vpnState: vpnState),
          const SizedBox(width: 8),
          Semantics(
            label: l10n.a11yConnectionStatus(label),
            readOnly: true,
            child: Text(
              label,
              style: TextStyle(
                color: _statusColor(vpnState),
                fontSize: 13,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.5,
              ),
            ),
          ),
          const Spacer(),
          // Subscription badge
          const _SubscriptionBadge(),
        ],
      ),
    );
  }

  static String _statusLabel(VpnConnectionState state, AppLocalizations l10n) {
    return switch (state) {
      VpnDisconnected() => l10n.connectionStatusNotProtected,
      VpnConnecting() => l10n.connecting,
      VpnConnected() => l10n.connectionStatusProtected,
      VpnDisconnecting() => l10n.disconnecting,
      VpnReconnecting() => l10n.connectionStatusReconnecting,
      VpnError() => l10n.connectionStatusConnectionError,
    };
  }

  static Color _statusColor(VpnConnectionState state) {
    return switch (state) {
      VpnDisconnected() => Colors.grey.shade500,
      VpnConnecting() => Colors.blue.shade400,
      VpnConnected() => Colors.green.shade400,
      VpnDisconnecting() => Colors.orange.shade400,
      VpnReconnecting() => Colors.orange.shade400,
      VpnError() => Colors.red.shade400,
    };
  }
}

class _StatusDot extends StatelessWidget {
  final VpnConnectionState vpnState;

  const _StatusDot({required this.vpnState});

  @override
  Widget build(BuildContext context) {
    final color = _TopBar._statusColor(vpnState);
    return ExcludeSemantics(
      child: Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color,
          boxShadow: [
            BoxShadow(
              color: color.withValues(alpha: 0.6),
              blurRadius: 6,
              spreadRadius: 1,
            ),
          ],
        ),
      ),
    );
  }
}

class _SubscriptionBadge extends StatelessWidget {
  const _SubscriptionBadge();

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    // TODO: Wire to a real subscription provider when available.
    return Semantics(
      label: l10n.a11yPremiumSubscriptionActive,
      readOnly: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Colors.cyan.shade700.withValues(alpha: 0.4),
              Colors.blue.shade700.withValues(alpha: 0.4),
            ],
          ),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: Colors.cyan.shade400.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            ExcludeSemantics(
              child: Icon(Icons.star_rounded,
                  color: Colors.cyan.shade300, size: 14),
            ),
            const SizedBox(width: 4),
            Text(
              l10n.connectionPremium,
              style: TextStyle(
                color: Colors.cyan.shade300,
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Error banner
// ---------------------------------------------------------------------------

class _ErrorBanner extends StatelessWidget {
  final String message;

  const _ErrorBanner({required this.message});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.red.shade900.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.red.shade700.withValues(alpha: 0.5)),
      ),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: Colors.red.shade300, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: Colors.red.shade200,
                fontSize: 12,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Bottom stats section
// ---------------------------------------------------------------------------

class _BottomStatsSection extends StatelessWidget {
  final VpnConnectionState vpnState;
  final String duration;
  final String totalUsage;

  const _BottomStatsSection({
    super.key,
    required this.vpnState,
    required this.duration,
    required this.totalUsage,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 16),
      decoration: BoxDecoration(
        color: const Color(0xFF111827),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(
          top: BorderSide(
            color: Colors.grey.shade800.withValues(alpha: 0.5),
          ),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Speed gauges
          const SpeedIndicator(),

          const SizedBox(height: 16),

          // Session summary row
          if (vpnState.isConnected || vpnState.isReconnecting)
            _SessionSummaryRow(
              duration: duration,
              totalUsage: totalUsage,
            ),
        ],
      ),
    );
  }
}

class _SessionSummaryRow extends StatelessWidget {
  final String duration;
  final String totalUsage;

  const _SessionSummaryRow({
    required this.duration,
    required this.totalUsage,
  });

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: [
        _SummaryItem(
          icon: Icons.timer_outlined,
          label: l10n.connectionDuration,
          value: duration,
        ),
        Container(
          width: 1,
          height: 28,
          color: Colors.grey.shade800,
        ),
        _SummaryItem(
          icon: Icons.data_usage,
          label: l10n.dataUsed,
          value: totalUsage,
        ),
      ],
    );
  }
}

class _SummaryItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _SummaryItem({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '$label: $value',
      readOnly: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          ExcludeSemantics(
            child: Icon(icon, color: Colors.grey.shade500, size: 16),
          ),
          const SizedBox(width: 6),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  color: Colors.grey.shade600,
                  fontSize: 10,
                  letterSpacing: 0.5,
                ),
              ),
              Text(
                value,
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  fontFeatures: [FontFeature.tabularFigures()],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lottie/lottie.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connect_button.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/connection_info.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/widgets/speed_indicator.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/shared/services/tooltip_preferences_service.dart';
import 'package:cybervpn_mobile/shared/widgets/feature_tooltip.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';
import 'package:cybervpn_mobile/shared/widgets/responsive_layout.dart';

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

class _ConnectionScreenState extends ConsumerState<ConnectionScreen>
    with SingleTickerProviderStateMixin {
  /// Global key for the speed indicator to position the tooltip.
  final GlobalKey _speedIndicatorKey = GlobalKey();

  /// Service to track shown tooltips.
  final TooltipPreferencesService _tooltipService = TooltipPreferencesService();

  /// Controller for the one-shot connected success animation.
  late final AnimationController _successAnimController;

  /// Whether to show the success animation overlay.
  bool _showSuccessAnim = false;

  /// Track previous state to detect transitions.
  VpnConnectionState? _prevVpnState;

  @override
  void initState() {
    super.initState();
    _successAnimController = AnimationController(vsync: this);
    // Show tooltip after first frame renders
    WidgetsBinding.instance.addPostFrameCallback((_) {
      unawaited(_showTooltipIfNeeded());
    });
  }

  @override
  void dispose() {
    _successAnimController.dispose();
    super.dispose();
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

    // Detect connecting→connected transition for one-shot success animation.
    // Skip animation when the user has disabled animations in accessibility settings.
    if (_prevVpnState is VpnConnecting &&
        vpnState is VpnConnected &&
        !MediaQuery.of(context).disableAnimations) {
      _showSuccessAnim = true;
      _successAnimController.reset();
      unawaited(_successAnimController.forward());
    }
    _prevVpnState = vpnState;

    final isConnecting =
        vpnState is VpnConnecting || vpnState is VpnReconnecting;

    // Build reusable content fragments used in both phone and tablet layouts.
    final connectButtonArea = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Lottie connecting animation (shown above button)
        if (isConnecting)
          Padding(
            padding: const EdgeInsets.only(bottom: Spacing.md),
            child: Lottie.asset(
              'assets/animations/connecting.json',
              width: 120,
              height: 120,
              fit: BoxFit.contain,
              animate: !MediaQuery.of(context).disableAnimations,
            ),
          ),

        // Connect button with success overlay
        Stack(
          alignment: Alignment.center,
          children: [
            const ConnectButton(),

            // One-shot connected success animation
            if (_showSuccessAnim)
              IgnorePointer(
                child: Lottie.asset(
                  'assets/animations/connected_success.json',
                  width: 180,
                  height: 180,
                  controller: _successAnimController,
                  fit: BoxFit.contain,
                  repeat: false,
                  onLoaded: (composition) {
                    _successAnimController.duration =
                        composition.duration;
                    unawaited(
                      _successAnimController
                          .forward()
                          .whenComplete(() {
                        if (mounted) {
                          setState(
                              () => _showSuccessAnim = false);
                        }
                      }),
                    );
                  },
                ),
              ),
          ],
        ),
      ],
    );

    final connectionInfoArea = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Connection info (server, protocol, timer, IP)
        const ConnectionInfo(),

        const SizedBox(height: Spacing.xl + Spacing.xs),

        // Error message banner
        if (vpnState is VpnError)
          _ErrorBanner(message: vpnState.message),
      ],
    );

    return Scaffold(
      body: SafeArea(
        child: LayoutBuilder(
          builder: (context, constraints) {
            final isWide =
                ResponsiveLayout.isAtLeastMedium(constraints.maxWidth);

            if (isWide) {
              // ── Tablet layout: side-by-side ──────────────────────────
              return Column(
                children: [
                  _TopBar(vpnState: vpnState),
                  Expanded(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        // Left side: connect button
                        Expanded(
                          child: Center(
                            child: SingleChildScrollView(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: Spacing.lg),
                              child: connectButtonArea,
                            ),
                          ),
                        ),
                        // Right side: info + stats
                        Expanded(
                          child: Center(
                            child: SingleChildScrollView(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: Spacing.lg),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  connectionInfoArea,
                                  const SizedBox(height: Spacing.lg),
                                  _BottomStatsSection(
                                    key: _speedIndicatorKey,
                                    vpnState: vpnState,
                                    duration: duration,
                                    totalUsage: usage.total,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              );
            }

            // ── Phone layout: stacked Column ────────────────────────────
            return Column(
              children: [
                _TopBar(vpnState: vpnState),
                Expanded(
                  child: Center(
                    child: SingleChildScrollView(
                      padding:
                          const EdgeInsets.symmetric(horizontal: Spacing.lg),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const SizedBox(height: Spacing.lg),
                          connectButtonArea,
                          const SizedBox(height: Spacing.lg + Spacing.xs),
                          connectionInfoArea,
                        ],
                      ),
                    ),
                  ),
                ),
                _BottomStatsSection(
                  key: _speedIndicatorKey,
                  vpnState: vpnState,
                  duration: duration,
                  totalUsage: usage.total,
                ),
              ],
            );
          },
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
    final colorScheme = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: Spacing.md, vertical: Spacing.sm + 4),
      child: Row(
        children: [
          // Status indicator dot
          _StatusDot(vpnState: vpnState),
          const SizedBox(width: Spacing.sm),
          Semantics(
            label: l10n.a11yConnectionStatus(label),
            hint: 'Shows current VPN protection status',
            readOnly: true,
            child: vpnState is VpnConnected
                ? GlitchText(
                    text: label,
                    style: TextStyle(
                      color: _statusColor(vpnState, colorScheme),
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                    ),
                  )
                : Text(
                    label,
                    style: TextStyle(
                      color: _statusColor(vpnState, colorScheme),
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

  static Color _statusColor(VpnConnectionState state, ColorScheme colorScheme) {
    return switch (state) {
      VpnDisconnected() => colorScheme.outline,
      VpnConnecting() => colorScheme.primary,
      VpnConnected() => colorScheme.tertiary,
      VpnDisconnecting() => Colors.orange.shade400,
      VpnReconnecting() => Colors.orange.shade400,
      VpnError() => colorScheme.error,
    };
  }
}

class _StatusDot extends StatefulWidget {
  final VpnConnectionState vpnState;

  const _StatusDot({required this.vpnState});

  @override
  State<_StatusDot> createState() => _StatusDotState();
}

class _StatusDotState extends State<_StatusDot>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseScale;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: CyberEffects.pulseDuration,
    );
    // Pulse scale: 1.0 -> 1.1 -> 1.0 using a TweenSequence for smooth looping.
    _pulseScale = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween<double>(begin: 1.0, end: 1.1)
            .chain(CurveTween(curve: CyberEffects.pulseCurve)),
        weight: 50,
      ),
      TweenSequenceItem(
        tween: Tween<double>(begin: 1.1, end: 1.0)
            .chain(CurveTween(curve: CyberEffects.pulseCurve)),
        weight: 50,
      ),
    ]).animate(_pulseController);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _syncPulse();
  }

  @override
  void didUpdateWidget(covariant _StatusDot oldWidget) {
    super.didUpdateWidget(oldWidget);
    _syncPulse();
  }

  /// Start pulse when connected, stop and reset immediately otherwise.
  void _syncPulse() {
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    if (widget.vpnState is VpnConnected && !disableAnimations) {
      if (!_pulseController.isAnimating) {
        unawaited(_pulseController.repeat());
      }
    } else {
      // VPNBussiness-3f93: stop immediately on disconnect / state change.
      if (_pulseController.isAnimating) {
        _pulseController.stop();
        _pulseController.reset();
      }
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color =
        _TopBar._statusColor(widget.vpnState, Theme.of(context).colorScheme);

    return RepaintBoundary(
      child: ExcludeSemantics(
        child: ScaleTransition(
          scale: _pulseScale,
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
    final colorScheme = Theme.of(context).colorScheme;

    // TODO: Wire to a real subscription provider when available.
    return Semantics(
      label: l10n.a11yPremiumSubscriptionActive,
      hint: 'Shows your current subscription tier',
      readOnly: true,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: Spacing.sm + 2, vertical: Spacing.xs),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              colorScheme.primary.withValues(alpha: 0.4),
              colorScheme.primary.withValues(alpha: 0.3),
            ],
          ),
          borderRadius: BorderRadius.circular(Radii.md),
          border: Border.all(
            color: colorScheme.primary.withValues(alpha: 0.3),
          ),
          boxShadow: CyberColors.isCyberpunkTheme(context)
              ? CyberEffects.neonGlow(colorScheme.primary, intensity: 0.35)
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            ExcludeSemantics(
              child: Icon(Icons.star_rounded,
                  color: colorScheme.primary, size: 14),
            ),
            const SizedBox(width: Spacing.xs),
            Text(
              l10n.connectionPremium,
              style: TextStyle(
                color: colorScheme.primary,
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
    final colorScheme = Theme.of(context).colorScheme;
    return Semantics(
      label: 'Connection error: $message',
      hint: 'Describes the connection failure reason',
      readOnly: true,
      liveRegion: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(Spacing.sm + 4),
        decoration: BoxDecoration(
          color: colorScheme.error.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(Radii.sm),
          border: Border.all(color: colorScheme.error.withValues(alpha: 0.5)),
        ),
        child: Row(
          children: [
            ExcludeSemantics(
              child: Icon(Icons.error_outline, color: colorScheme.error, size: 18),
            ),
            const SizedBox(width: Spacing.sm),
            Expanded(
              child: Text(
                message,
                style: TextStyle(
                  color: colorScheme.error.withValues(alpha: 0.8),
                  fontSize: 12,
                ),
              ),
            ),
          ],
        ),
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
    final theme = Theme.of(context);
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.fromLTRB(Spacing.lg, Spacing.lg - 4, Spacing.lg, Spacing.md),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(
          top: BorderSide(
            color: theme.colorScheme.outlineVariant,
          ),
        ),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Speed gauges
          const SpeedIndicator(),

          const SizedBox(height: Spacing.md),

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
          color: Theme.of(context).colorScheme.outlineVariant,
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
    final colorScheme = Theme.of(context).colorScheme;
    return Semantics(
      label: '$label: $value',
      hint: 'Shows current $label',
      readOnly: true,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          ExcludeSemantics(
            child: Icon(icon, color: colorScheme.onSurfaceVariant, size: 16),
          ),
          const SizedBox(width: 6),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  color: colorScheme.onSurfaceVariant,
                  fontSize: 10,
                  letterSpacing: 0.5,
                ),
              ),
              Text(
                value,
                style: TextStyle(
                  color: colorScheme.onSurface.withValues(alpha: 0.7),
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

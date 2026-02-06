import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';

// ---------------------------------------------------------------------------
// SpeedTestResultsCard
// ---------------------------------------------------------------------------

/// Displays the results of a speed test in a cyberpunk-themed card.
///
/// Shows download/upload speeds, latency, and jitter metrics.
/// Optionally displays a comparison with a previous test result.
class SpeedTestResultsCard extends StatelessWidget {
  const SpeedTestResultsCard({
    super.key,
    required this.result,
    this.previousResult,
    this.onCompare,
    this.onShare,
    this.showComparison = false,
  });

  /// The speed test result to display.
  final SpeedTestResult result;

  /// Optional previous result for comparison.
  final SpeedTestResult? previousResult;

  /// Called when the user taps the "Compare" button.
  final VoidCallback? onCompare;

  /// Called when the user taps the "Share" button.
  final VoidCallback? onShare;

  /// Whether to show the comparison panel.
  final bool showComparison;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF111827),
        borderRadius: BorderRadius.circular(Radii.lg),
        border: Border.all(
          color: CyberColors.neonCyan.withValues(alpha: 0.15),
        ),
        boxShadow: [
          BoxShadow(
            color: CyberColors.neonCyan.withValues(alpha: 0.05),
            blurRadius: 16,
            spreadRadius: 0,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header
          _CardHeader(
            testedAt: result.testedAt,
            vpnActive: result.vpnActive,
            serverName: result.serverName,
          ),

          const Divider(color: Colors.white10, height: 1),

          // Metrics grid
          Padding(
            padding: const EdgeInsets.all(Spacing.md),
            child: _MetricsGrid(
              result: result,
              previousResult: showComparison ? previousResult : null,
            ),
          ),

          // Action buttons
          Padding(
            padding: const EdgeInsets.fromLTRB(
              Spacing.md,
              0,
              Spacing.md,
              Spacing.md,
            ),
            child: Row(
              children: [
                if (previousResult != null)
                  Expanded(
                    child: _ActionButton(
                      icon: Icons.compare_arrows,
                      label: showComparison
                          ? l10n.speedTestHideCompare
                          : l10n.speedTestCompare,
                      onTap: onCompare,
                    ),
                  ),
                if (previousResult != null) const SizedBox(width: Spacing.sm),
                Expanded(
                  child: _ActionButton(
                    icon: Icons.share_outlined,
                    label: l10n.commonShare,
                    onTap: onShare,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Card Header
// ---------------------------------------------------------------------------

class _CardHeader extends StatelessWidget {
  const _CardHeader({
    required this.testedAt,
    required this.vpnActive,
    this.serverName,
  });

  final DateTime testedAt;
  final bool vpnActive;
  final String? serverName;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final timeStr = _formatTime(testedAt);

    return Padding(
      padding: const EdgeInsets.all(Spacing.md),
      child: Row(
        children: [
          const Icon(
            Icons.speed,
            color: CyberColors.neonCyan,
            size: 18,
          ),
          const SizedBox(width: Spacing.sm),
          Expanded(
            child: Text(
              l10n.speedTestResult,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.9),
                fontSize: 14,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.5,
              ),
            ),
          ),
          const SizedBox(width: Spacing.sm),
          // VPN badge
          _VpnBadge(active: vpnActive),
          const SizedBox(width: Spacing.sm),
          Text(
            timeStr,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.4),
              fontSize: 11,
              fontFamily: 'JetBrains Mono',
            ),
          ),
        ],
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}

class _VpnBadge extends StatelessWidget {
  const _VpnBadge({required this.active});

  final bool active;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: active
            ? CyberColors.matrixGreen.withValues(alpha: 0.15)
            : Colors.grey.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(
          color: active
              ? CyberColors.matrixGreen.withValues(alpha: 0.3)
              : Colors.grey.withValues(alpha: 0.3),
        ),
      ),
      child: Text(
        active ? l10n.speedTestVpnOn : l10n.speedTestVpnOff,
        style: TextStyle(
          color: active ? CyberColors.matrixGreen : Colors.grey,
          fontSize: 9,
          fontWeight: FontWeight.w700,
          letterSpacing: 1,
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Metrics Grid
// ---------------------------------------------------------------------------

class _MetricsGrid extends StatelessWidget {
  const _MetricsGrid({
    required this.result,
    this.previousResult,
  });

  final SpeedTestResult result;
  final SpeedTestResult? previousResult;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Row(
      children: [
        Expanded(
          child: Column(
            children: [
              _MetricTile(
                icon: Icons.download,
                label: l10n.downloadSpeed,
                value: result.downloadMbps.toStringAsFixed(1),
                unit: 'Mbps',
                color: CyberColors.matrixGreen,
                delta: previousResult != null
                    ? result.downloadMbps - previousResult!.downloadMbps
                    : null,
                higherIsBetter: true,
              ),
              const SizedBox(height: Spacing.md),
              _MetricTile(
                icon: Icons.network_ping,
                label: l10n.speedTestLatency,
                value: result.latencyMs.toString(),
                unit: 'ms',
                color: CyberColors.neonCyan,
                delta: previousResult != null
                    ? (result.latencyMs - previousResult!.latencyMs).toDouble()
                    : null,
                higherIsBetter: false,
              ),
            ],
          ),
        ),
        const SizedBox(width: Spacing.md),
        Expanded(
          child: Column(
            children: [
              _MetricTile(
                icon: Icons.upload,
                label: l10n.uploadSpeed,
                value: result.uploadMbps.toStringAsFixed(1),
                unit: 'Mbps',
                color: CyberColors.neonPink,
                delta: previousResult != null
                    ? result.uploadMbps - previousResult!.uploadMbps
                    : null,
                higherIsBetter: true,
              ),
              const SizedBox(height: Spacing.md),
              _MetricTile(
                icon: Icons.swap_vert,
                label: l10n.speedTestJitter,
                value: result.jitterMs.toString(),
                unit: 'ms',
                color: Colors.amber,
                delta: previousResult != null
                    ? (result.jitterMs - previousResult!.jitterMs).toDouble()
                    : null,
                higherIsBetter: false,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Individual Metric Tile
// ---------------------------------------------------------------------------

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.unit,
    required this.color,
    this.delta,
    this.higherIsBetter = true,
  });

  final IconData icon;
  final String label;
  final String value;
  final String unit;
  final Color color;
  final double? delta;
  final bool higherIsBetter;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(Spacing.sm + 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(Radii.sm),
        border: Border.all(
          color: color.withValues(alpha: 0.1),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 14),
              const SizedBox(width: 4),
              Flexible(
                child: Text(
                  label,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.5),
                    fontSize: 11,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Flexible(
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: AlignmentDirectional.bottomStart,
                  child: Text(
                    value,
                    style: TextStyle(
                      color: color,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      fontFamily: 'Orbitron',
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 4),
              Padding(
                padding: const EdgeInsets.only(bottom: 3),
                child: Text(
                  unit,
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.3),
                    fontSize: 10,
                    fontFamily: 'JetBrains Mono',
                  ),
                ),
              ),
            ],
          ),
          if (delta != null) ...[
            const SizedBox(height: 4),
            _DeltaIndicator(
              delta: delta!,
              higherIsBetter: higherIsBetter,
            ),
          ],
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Delta Indicator
// ---------------------------------------------------------------------------

class _DeltaIndicator extends StatelessWidget {
  const _DeltaIndicator({
    required this.delta,
    required this.higherIsBetter,
  });

  final double delta;
  final bool higherIsBetter;

  @override
  Widget build(BuildContext context) {
    final isImprovement =
        higherIsBetter ? delta > 0 : delta < 0;
    final colorScheme = Theme.of(context).colorScheme;
    final color = isImprovement
        ? CyberColors.matrixGreen
        : (delta == 0 ? colorScheme.outline : colorScheme.error);
    final icon = delta > 0
        ? Icons.arrow_upward
        : (delta < 0 ? Icons.arrow_downward : Icons.remove);

    final displayDelta = delta.abs();

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: color, size: 10),
        const SizedBox(width: 2),
        Text(
          displayDelta.toStringAsFixed(1),
          style: TextStyle(
            color: color,
            fontSize: 10,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Action Button
// ---------------------------------------------------------------------------

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.icon,
    required this.label,
    this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(Radii.sm),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.md,
            vertical: Spacing.sm + 2,
          ),
          decoration: BoxDecoration(
            border: Border.all(
              color: CyberColors.neonCyan.withValues(alpha: 0.2),
            ),
            borderRadius: BorderRadius.circular(Radii.sm),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: CyberColors.neonCyan, size: 14),
              const SizedBox(width: 6),
              Text(
                label,
                style: const TextStyle(
                  color: CyberColors.neonCyan,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

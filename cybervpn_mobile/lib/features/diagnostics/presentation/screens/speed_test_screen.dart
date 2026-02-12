import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lottie/lottie.dart';
import 'package:share_plus/share_plus.dart' as share_plus;

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/haptics/haptic_service.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/speed_test_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/providers/diagnostics_provider.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/widgets/speed_test_results_card.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/widgets/speedometer_gauge.dart';
import 'package:cybervpn_mobile/shared/widgets/adaptive_switch.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_app_bar.dart';

// ---------------------------------------------------------------------------
// SpeedTestScreen
// ---------------------------------------------------------------------------

/// Full-screen speed test interface.
///
/// Layout (top to bottom):
/// 1. Animated speedometer gauge (hero area)
/// 2. Start / Stop test button
/// 3. Results card (when a test has completed)
/// 4. Scrollable history list (last 20 tests)
class SpeedTestScreen extends ConsumerStatefulWidget {
  const SpeedTestScreen({super.key});

  @override
  ConsumerState<SpeedTestScreen> createState() => _SpeedTestScreenState();
}

class _SpeedTestScreenState extends ConsumerState<SpeedTestScreen> {
  bool _showComparison = false;
  bool _vpnToggle = true;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final isRunning = ref.watch(speedTestProgressProvider);
    final latestResult = ref.watch(latestSpeedTestProvider);
    final history = ref.watch(speedHistoryProvider);

    // Find the previous result for comparison (second in history).
    final previousResult =
        history.length >= 2 ? history[1] : null;

    // Determine gauge speed: latest result's download speed or 0 while idle.
    final gaugeSpeed = latestResult?.downloadMbps ?? 0.0;

    return Scaffold(
      backgroundColor: CyberColors.deepNavy,
      appBar: CyberAppBar(
        title: l10n.speedTestTitle,
        transparent: true,
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          // Trigger medium haptic on pull-to-refresh threshold.
          final haptics = ref.read(hapticServiceProvider);
          unawaited(haptics.impact());

          // Trigger provider rebuild to reload history.
          ref.invalidate(diagnosticsProvider);
        },
        color: CyberColors.neonCyan,
        backgroundColor: CyberColors.darkBg,
        child: CustomScrollView(
          slivers: [
            // -- Gauge hero section --
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: Spacing.lg,
                  vertical: Spacing.md,
                ),
                child: Center(
                  child: SpeedometerGauge(
                    speed: isRunning ? gaugeSpeed : gaugeSpeed,
                    maxSpeed: 100.0,
                    size: MediaQuery.sizeOf(context).width * 0.65,
                  ),
                ),
              ),
            ),

            // -- VPN toggle row --
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: Spacing.lg),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      l10n.speedTestWithVpn,
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.6),
                        fontSize: 13,
                        letterSpacing: 0.5,
                      ),
                    ),
                    const SizedBox(width: Spacing.sm),
                    AdaptiveSwitch(
                      value: _vpnToggle,
                      onChanged: isRunning
                          ? null
                          : (v) {
                              // Trigger medium haptic on toggle switch change.
                              final haptics = ref.read(hapticServiceProvider);
                              unawaited(haptics.impact());
                              setState(() => _vpnToggle = v);
                            },
                      activeColor: CyberColors.matrixGreen,
                    ),
                  ],
                ),
              ),
            ),

            // -- Start / Stop button --
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: Spacing.xl,
                  vertical: Spacing.md,
                ),
                child: _StartTestButton(
                  isRunning: isRunning,
                  onPressed: _onStartTest,
                ),
              ),
            ),

            // -- Results card --
            if (latestResult != null)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: Spacing.md,
                    vertical: Spacing.sm,
                  ),
                  child: SpeedTestResultsCard(
                    result: latestResult,
                    previousResult: previousResult,
                    showComparison: _showComparison,
                    onCompare: () {
                      setState(
                          () => _showComparison = !_showComparison);
                    },
                    onShare: () => _shareResults(latestResult),
                  ),
                ),
              ),

            // -- History header --
            if (history.isNotEmpty)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(
                    Spacing.md,
                    Spacing.lg,
                    Spacing.md,
                    Spacing.sm,
                  ),
                  child: Text(
                    l10n.speedTestHistoryLabel,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.7),
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
              ),

            // -- History list --
            if (history.isNotEmpty)
              SliverList.builder(
                itemCount: history.length,
                itemBuilder: (context, index) {
                  return _HistoryTile(
                    result: history[index],
                    isLatest: index == 0,
                  );
                },
              ),

            // -- Empty state --
            if (history.isEmpty && latestResult == null)
              SliverFillRemaining(
                hasScrollBody: false,
                child: Center(
                  child: Padding(
                    padding: const EdgeInsets.only(top: Spacing.xl),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.speed_outlined,
                          color: Colors.white.withValues(alpha: 0.15),
                          size: 64,
                        ),
                        const SizedBox(height: Spacing.md),
                        Text(
                          l10n.speedTestNoResults,
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.3),
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: Spacing.xs),
                        Text(
                          l10n.speedTestTapToStart,
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.2),
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),

            // Bottom padding
            const SliverToBoxAdapter(
              child: SizedBox(height: Spacing.xl),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _onStartTest() async {
    // Trigger light haptic on button tap.
    final haptics = ref.read(hapticServiceProvider);
    unawaited(haptics.selection());

    final notifier = ref.read(diagnosticsProvider.notifier);
    await notifier.runSpeedTest(vpnActive: _vpnToggle);
  }

  void _shareResults(SpeedTestResult result) {
    final l10n = AppLocalizations.of(context);
    final text = StringBuffer()
      ..writeln(l10n.speedTestShareTitle)
      ..writeln('---')
      ..writeln(
          l10n.speedTestShareDownload(result.downloadMbps.toStringAsFixed(1)))
      ..writeln(
          l10n.speedTestShareUpload(result.uploadMbps.toStringAsFixed(1)))
      ..writeln(l10n.speedTestShareLatency(result.latencyMs))
      ..writeln(l10n.speedTestShareJitter(result.jitterMs))
      ..writeln(result.vpnActive ? l10n.speedTestShareVpnOn : l10n.speedTestShareVpnOff)
      ..writeln(l10n.speedTestShareTestedAt(result.testedAt.toLocal().toString()));

    unawaited(share_plus.SharePlus.instance.share(share_plus.ShareParams(text: text.toString())));
  }
}

// ---------------------------------------------------------------------------
// Start Test Button
// ---------------------------------------------------------------------------

class _StartTestButton extends StatelessWidget {
  const _StartTestButton({
    required this.isRunning,
    required this.onPressed,
  });

  final bool isRunning;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: isRunning ? null : onPressed,
        borderRadius: BorderRadius.circular(Radii.xl),
        child: AnimatedContainer(
          duration: AnimDurations.normal,
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            gradient: isRunning
                ? null
                : const LinearGradient(
                    colors: [
                      CyberColors.neonCyan,
                      CyberColors.matrixGreen,
                    ],
                  ),
            color: isRunning ? Colors.white.withValues(alpha: 0.05) : null,
            borderRadius: BorderRadius.circular(Radii.xl),
            boxShadow: isRunning
                ? null
                : [
                    BoxShadow(
                      color: CyberColors.neonCyan.withValues(alpha: 0.3),
                      blurRadius: 16,
                      spreadRadius: 0,
                    ),
                  ],
          ),
          child: Center(
            child: isRunning
                ? Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Lottie.asset(
                        'assets/animations/speed_test.json',
                        width: 24,
                        height: 24,
                        fit: BoxFit.contain,
                        animate: !MediaQuery.of(context).disableAnimations,
                      ),
                      const SizedBox(width: Spacing.sm),
                      Text(
                        l10n.speedTestRunning,
                        style: const TextStyle(
                          color: CyberColors.neonCyan,
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 1,
                        ),
                      ),
                    ],
                  )
                : Text(
                    l10n.speedTestStart,
                    style: const TextStyle(
                      color: CyberColors.deepNavy,
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1,
                    ),
                  ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// History Tile
// ---------------------------------------------------------------------------

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({
    required this.result,
    this.isLatest = false,
  });

  final SpeedTestResult result;
  final bool isLatest;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.md,
        vertical: Spacing.xs,
      ),
      child: Container(
        padding: const EdgeInsets.all(Spacing.sm + 4),
        decoration: BoxDecoration(
          color: isLatest
              ? CyberColors.neonCyan.withValues(alpha: 0.05)
              : Colors.white.withValues(alpha: 0.02),
          borderRadius: BorderRadius.circular(Radii.sm),
          border: Border.all(
            color: isLatest
                ? CyberColors.neonCyan.withValues(alpha: 0.15)
                : Colors.white.withValues(alpha: 0.05),
          ),
        ),
        child: Row(
          children: [
            // Timestamp
            SizedBox(
              width: 68,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _formatDate(result.testedAt),
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.4),
                      fontSize: 10,
                      fontFamily: 'JetBrains Mono',
                    ),
                  ),
                  Text(
                    _formatTime(result.testedAt),
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.6),
                      fontSize: 12,
                      fontFamily: 'JetBrains Mono',
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),

            // VPN indicator
            Container(
              width: 4,
              height: 28,
              margin: const EdgeInsets.symmetric(horizontal: Spacing.sm),
              decoration: BoxDecoration(
                color: result.vpnActive
                    ? CyberColors.matrixGreen
                    : Colors.grey.shade700,
                borderRadius: BorderRadius.circular(2),
              ),
            ),

            // Download speed
            Expanded(
              child: _CompactMetric(
                icon: Icons.download,
                value: result.downloadMbps.toStringAsFixed(1),
                unit: 'Mbps',
                color: CyberColors.matrixGreen,
              ),
            ),

            // Upload speed
            Expanded(
              child: _CompactMetric(
                icon: Icons.upload,
                value: result.uploadMbps.toStringAsFixed(1),
                unit: 'Mbps',
                color: CyberColors.neonPink,
              ),
            ),

            // Latency
            SizedBox(
              width: 52,
              child: Text(
                '${result.latencyMs}ms',
                textAlign: TextAlign.end,
                style: TextStyle(
                  color: CyberColors.neonCyan.withValues(alpha: 0.7),
                  fontSize: 11,
                  fontFamily: 'JetBrains Mono',
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  static String _formatDate(DateTime dt) {
    final m = dt.month.toString().padLeft(2, '0');
    final d = dt.day.toString().padLeft(2, '0');
    return '$m/$d';
  }

  static String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}

// ---------------------------------------------------------------------------
// Compact Metric (for history rows)
// ---------------------------------------------------------------------------

class _CompactMetric extends StatelessWidget {
  const _CompactMetric({
    required this.icon,
    required this.value,
    required this.unit,
    required this.color,
  });

  final IconData icon;
  final String value;
  final String unit;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: color, size: 12),
        const SizedBox(width: 3),
        Text(
          value,
          style: TextStyle(
            color: color,
            fontSize: 12,
            fontWeight: FontWeight.w600,
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
        const SizedBox(width: 2),
        Text(
          unit,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.3),
            fontSize: 9,
          ),
        ),
      ],
    );
  }
}

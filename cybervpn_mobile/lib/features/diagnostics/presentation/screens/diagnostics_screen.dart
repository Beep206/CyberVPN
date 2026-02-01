import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart' as share_plus;

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/diagnostics/data/services/diagnostic_service.dart';
import 'package:cybervpn_mobile/features/diagnostics/domain/entities/diagnostic_result.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/providers/diagnostics_provider.dart';
import 'package:cybervpn_mobile/features/diagnostics/presentation/widgets/diagnostic_step_tile.dart';
import 'package:cybervpn_mobile/shared/widgets/cyber_app_bar.dart';

// ---------------------------------------------------------------------------
// DiagnosticsScreen
// ---------------------------------------------------------------------------

/// Full-screen connection diagnostics interface with animated step checklist.
///
/// Layout (top to bottom):
/// 1. 6-step checklist — each row shows step name, animated status (spinner,
///    green check, or red X), duration, and message.
/// 2. On failure: displays suggestion text and optional 'Fix' button if
///    actionable.
/// 3. 'Export Report' button → shares diagnostics result as formatted text.
/// 4. 'Run Again' button to re-trigger diagnostics.
///
/// Auto-triggered after 3+ connection failures (optional, implemented in
/// parent logic).
class DiagnosticsScreen extends ConsumerStatefulWidget {
  const DiagnosticsScreen({super.key});

  @override
  ConsumerState<DiagnosticsScreen> createState() => _DiagnosticsScreenState();
}

class _DiagnosticsScreenState extends ConsumerState<DiagnosticsScreen> {
  @override
  void initState() {
    super.initState();
    // Auto-run diagnostics on screen open if not already running.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final isRunning = ref.read(isRunningDiagnosticsProvider);
      if (!isRunning) {
        ref.read(diagnosticsProvider.notifier).runDiagnostics();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final isRunning = ref.watch(isRunningDiagnosticsProvider);
    final steps = ref.watch(diagnosticStepsProvider);
    final asyncState = ref.watch(diagnosticsProvider);

    // Determine if we have a completed diagnostic result.
    final hasResult = asyncState.value?.diagnosticResult != null && !isRunning;

    return Scaffold(
      backgroundColor: CyberColors.deepNavy,
      appBar: const CyberAppBar(
        title: 'Connection Diagnostics',
        transparent: true,
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          // Trigger a fresh diagnostic run.
          await ref.read(diagnosticsProvider.notifier).runDiagnostics();
        },
        color: CyberColors.neonCyan,
        backgroundColor: CyberColors.darkBg,
        child: CustomScrollView(
          slivers: [
            // Header section
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(Spacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Diagnostic Steps',
                      style: TextStyle(
                        color: CyberColors.neonCyan.withValues(alpha: 0.9),
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.8,
                      ),
                    ),
                    const SizedBox(height: Spacing.xs),
                    Text(
                      isRunning
                          ? 'Running connection tests...'
                          : hasResult
                              ? 'Diagnostics completed'
                              : 'Tap Run Again to start',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.5),
                        fontSize: 13,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            // 6-step checklist
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
              sliver: SliverList.builder(
                itemCount: _getDisplayStepCount(steps, isRunning),
                itemBuilder: (context, index) {
                  // If running and index >= steps.length, show pending placeholder.
                  if (index >= steps.length) {
                    return DiagnosticStepTile(
                      stepName: _getStepNameByIndex(index),
                      status: DiagnosticStepStatus.pending,
                    );
                  }

                  final step = steps[index];
                  return DiagnosticStepTile(
                    stepName: step.name,
                    status: step.status,
                    duration: step.duration,
                    message: step.message,
                    suggestion: step.suggestion,
                  );
                },
              ),
            ),

            // Action buttons section
            if (hasResult || isRunning)
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(
                    Spacing.md,
                    Spacing.lg,
                    Spacing.md,
                    Spacing.md,
                  ),
                  child: Column(
                    children: [
                      // Export Report button
                      if (hasResult)
                        _ActionButton(
                          label: 'Export Report',
                          icon: Icons.share,
                          onPressed: () => _exportReport(
                            asyncState.value!.diagnosticResult!,
                          ),
                          gradient: const LinearGradient(
                            colors: [
                              CyberColors.neonCyan,
                              CyberColors.matrixGreen,
                            ],
                          ),
                        ),

                      const SizedBox(height: Spacing.sm),

                      // Run Again button
                      _ActionButton(
                        label: isRunning ? 'Running...' : 'Run Again',
                        icon: isRunning ? null : Icons.refresh,
                        onPressed: isRunning ? null : _onRunAgain,
                        isLoading: isRunning,
                        gradient: isRunning
                            ? null
                            : const LinearGradient(
                                colors: [
                                  CyberColors.neonPink,
                                  CyberColors.matrixGreen,
                                ],
                              ),
                      ),
                    ],
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

  /// Returns the number of step tiles to display: all 6 steps when running
  /// (to show pending state), or the actual completed step count when done.
  int _getDisplayStepCount(List<DiagnosticStep> steps, bool isRunning) {
    if (isRunning) {
      // Show all 6 steps to indicate pending state for uncompleted ones.
      return 6;
    }
    return steps.length;
  }

  /// Maps a step index (0-5) to the corresponding step name constant.
  String _getStepNameByIndex(int index) {
    switch (index) {
      case 0:
        return DiagnosticStepNames.networkConnectivity;
      case 1:
        return DiagnosticStepNames.dnsResolution;
      case 2:
        return DiagnosticStepNames.apiReachability;
      case 3:
        return DiagnosticStepNames.vpnTcpHandshake;
      case 4:
        return DiagnosticStepNames.tlsHandshake;
      case 5:
        return DiagnosticStepNames.fullTunnel;
      default:
        return 'Unknown Step';
    }
  }

  Future<void> _onRunAgain() async {
    await ref.read(diagnosticsProvider.notifier).runDiagnostics();
  }

  void _exportReport(DiagnosticResult result) {
    final buffer = StringBuffer()
      ..writeln('CyberVPN Connection Diagnostics Report')
      ..writeln('=' * 45)
      ..writeln('Ran at: ${result.ranAt.toLocal()}')
      ..writeln('Total duration: ${result.totalDuration.inSeconds}s')
      ..writeln()
      ..writeln('Steps:')
      ..writeln('-' * 45);

    for (final step in result.steps) {
      buffer
        ..writeln()
        ..writeln(step.name)
        ..writeln('  Status: ${_formatStatus(step.status)}')
        ..writeln(
          '  Duration: ${step.duration != null ? '${step.duration!.inMilliseconds}ms' : 'N/A'}',
        );

      if (step.message != null) {
        buffer.writeln('  Message: ${step.message}');
      }

      if (step.suggestion != null) {
        buffer.writeln('  Suggestion: ${step.suggestion}');
      }
    }

    share_plus.Share.share(buffer.toString());
  }

  String _formatStatus(DiagnosticStepStatus status) {
    switch (status) {
      case DiagnosticStepStatus.pending:
        return 'PENDING';
      case DiagnosticStepStatus.running:
        return 'RUNNING';
      case DiagnosticStepStatus.success:
        return 'SUCCESS';
      case DiagnosticStepStatus.failed:
        return 'FAILED';
      case DiagnosticStepStatus.warning:
        return 'WARNING';
    }
  }
}

// ---------------------------------------------------------------------------
// ActionButton
// ---------------------------------------------------------------------------

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.label,
    this.icon,
    this.onPressed,
    this.gradient,
    this.isLoading = false,
  });

  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;
  final Gradient? gradient;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(Radii.md),
        child: AnimatedContainer(
          duration: AnimDurations.normal,
          padding: const EdgeInsets.symmetric(
            vertical: 14,
            horizontal: Spacing.md,
          ),
          decoration: BoxDecoration(
            gradient: gradient,
            color: gradient == null
                ? Colors.white.withValues(alpha: 0.05)
                : null,
            borderRadius: BorderRadius.circular(Radii.md),
            boxShadow: gradient != null
                ? [
                    BoxShadow(
                      color: CyberColors.neonCyan.withValues(alpha: 0.2),
                      blurRadius: 12,
                      spreadRadius: 0,
                    ),
                  ]
                : null,
          ),
          child: Center(
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (isLoading)
                  const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: CyberColors.neonCyan,
                    ),
                  )
                else if (icon != null)
                  Icon(
                    icon,
                    color: gradient != null
                        ? CyberColors.deepNavy
                        : CyberColors.neonCyan,
                    size: 18,
                  ),
                const SizedBox(width: Spacing.sm),
                Text(
                  label,
                  style: TextStyle(
                    color: gradient != null
                        ? CyberColors.deepNavy
                        : CyberColors.neonCyan,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.8,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

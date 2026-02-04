import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_connection_provider.dart';
import 'package:cybervpn_mobile/features/vpn/presentation/providers/vpn_stats_provider.dart';

/// Two side-by-side speed indicators (upload + download) with session totals.
///
/// Active speeds are color-coded green; idle values are gray.
/// Values animate smoothly between updates.
///
/// Wrapped in [RepaintBoundary] to isolate repaints and improve performance.
class SpeedIndicator extends ConsumerWidget {
  const SpeedIndicator({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isConnected = ref.watch(isConnectedProvider);
    final speed = ref.watch(currentSpeedProvider);
    final usage = ref.watch(sessionUsageProvider);

    // Speed indicators should always remain LTR for consistency in data visualization
    return Directionality(
      textDirection: TextDirection.ltr,
      child: RepaintBoundary(
        child: Semantics(
          label:
              'Download speed: ${speed.download}, Upload speed: ${speed.upload}',
          readOnly: true,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _SpeedGauge(
                icon: Icons.arrow_downward_rounded,
                label: 'Download',
                speed: speed.download,
                total: usage.download,
                isActive: isConnected,
              ),
              const SizedBox(width: 32),
              _SpeedGauge(
                icon: Icons.arrow_upward_rounded,
                label: 'Upload',
                speed: speed.upload,
                total: usage.upload,
                isActive: isConnected,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SpeedGauge extends StatelessWidget {
  final IconData icon;
  final String label;
  final String speed;
  final String total;
  final bool isActive;

  const _SpeedGauge({
    required this.icon,
    required this.label,
    required this.speed,
    required this.total,
    required this.isActive,
  });

  @override
  Widget build(BuildContext context) {
    final activeColor = isActive ? Colors.green.shade400 : Colors.grey.shade600;
    final textColor = isActive ? Colors.white : Colors.grey.shade500;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Direction icon
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: activeColor.withValues(alpha: 0.15),
            border: Border.all(
              color: activeColor.withValues(alpha: 0.4),
            ),
          ),
          child: Icon(icon, color: activeColor, size: 20),
        ),

        const SizedBox(height: 8),

        // Label
        Text(
          label,
          style: TextStyle(
            color: Colors.grey.shade500,
            fontSize: 10,
            fontWeight: FontWeight.w500,
            letterSpacing: 0.8,
          ),
        ),

        const SizedBox(height: 4),

        // Current speed (animated text swap)
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 200),
          child: Text(
            speed,
            key: ValueKey(speed),
            style: TextStyle(
              color: textColor,
              fontSize: 16,
              fontWeight: FontWeight.w700,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
          ),
        ),

        const SizedBox(height: 4),

        // Session total
        Text(
          total,
          style: TextStyle(
            color: Colors.grey.shade600,
            fontSize: 11,
            fontFeatures: const [FontFeature.tabularFigures()],
          ),
        ),
      ],
    );
  }
}

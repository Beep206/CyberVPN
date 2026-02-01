import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

/// Base skeleton loading widget that provides shimmer effect
/// for various loading states across the app.
///
/// This widget adapts to the current theme's brightness to provide
/// appropriate shimmer colors for dark and light modes.
class SkeletonLoader extends StatelessWidget {
  /// The child widget to apply shimmer effect to.
  final Widget child;

  const SkeletonLoader({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // Theme-aware shimmer colors
    final baseColor = isDark
        ? const Color(0xFF1E2538) // Dark mode base
        : const Color(0xFFE5E7EB); // Light mode base

    final highlightColor = isDark
        ? const Color(0xFF2D3548) // Dark mode highlight
        : const Color(0xFFF9FAFB); // Light mode highlight

    return Shimmer.fromColors(
      baseColor: baseColor,
      highlightColor: highlightColor,
      child: child,
    );
  }
}

/// A rectangular skeleton placeholder with rounded corners.
///
/// Used for loading text, buttons, and other rectangular UI elements.
class SkeletonLine extends StatelessWidget {
  /// The width of the skeleton line.
  final double width;

  /// The height of the skeleton line.
  final double height;

  /// The border radius of the skeleton line.
  final double borderRadius;

  const SkeletonLine({
    super.key,
    required this.width,
    this.height = 16,
    this.borderRadius = 4,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return SkeletonLoader(
      child: Container(
        width: width,
        height: height,
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E2538) : Colors.grey[300],
          borderRadius: BorderRadius.circular(borderRadius),
        ),
      ),
    );
  }
}

/// A circular skeleton placeholder.
///
/// Used for loading avatars, profile pictures, and circular icons.
class SkeletonCircle extends StatelessWidget {
  /// The diameter of the circular skeleton.
  final double size;

  const SkeletonCircle({super.key, required this.size});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return SkeletonLoader(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E2538) : Colors.grey[300],
          shape: BoxShape.circle,
        ),
      ),
    );
  }
}

/// A generic card-shaped skeleton placeholder.
///
/// Used for loading card-based UI elements with consistent styling.
class SkeletonCard extends StatelessWidget {
  /// The width of the card. If null, card takes full available width.
  final double? width;

  /// The height of the card.
  final double height;

  /// The border radius of the card.
  final double borderRadius;

  /// Optional padding inside the card.
  final EdgeInsetsGeometry? padding;

  const SkeletonCard({
    super.key,
    this.width,
    this.height = 120,
    this.borderRadius = 12,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return SkeletonLoader(
      child: Container(
        width: width,
        height: height,
        padding: padding,
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E2538) : Colors.grey[300],
          borderRadius: BorderRadius.circular(borderRadius),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Domain-specific skeleton components
// ---------------------------------------------------------------------------

/// Skeleton loader for server list cards.
///
/// Mimics the structure of [ServerCard] with:
/// - Leading circular placeholder (flag emoji area)
/// - Title and subtitle lines
/// - Trailing ping indicator and load bar placeholders
class ServerCardSkeleton extends StatelessWidget {
  const ServerCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Row(
          children: [
            // Leading: flag emoji placeholder
            const SkeletonCircle(size: 28),
            const SizedBox(width: 12),

            // Title + Subtitle
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Server name placeholder
                  SkeletonLine(
                    width: MediaQuery.of(context).size.width * 0.4,
                    height: 18,
                    borderRadius: 4,
                  ),
                  const SizedBox(height: 6),

                  // City + protocol badge placeholder
                  Row(
                    children: [
                      SkeletonLine(
                        width: MediaQuery.of(context).size.width * 0.25,
                        height: 14,
                        borderRadius: 4,
                      ),
                      const SizedBox(width: 8),
                      SkeletonLine(
                        width: 50,
                        height: 14,
                        borderRadius: 6,
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // Trailing section: latency + load
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisSize: MainAxisSize.min,
              children: [
                // Ping indicator placeholder
                SkeletonLine(
                  width: 50,
                  height: 24,
                  borderRadius: 12,
                ),
                const SizedBox(height: 6),

                // Load bar placeholder
                SkeletonLine(
                  width: 48,
                  height: 3,
                  borderRadius: 2,
                ),
              ],
            ),
            const SizedBox(width: 8),

            // Favorite star placeholder
            const SkeletonCircle(size: 22),
          ],
        ),
      ),
    );
  }
}

/// Skeleton loader for profile header cards.
///
/// Mimics the structure of a profile header with:
/// - Circular avatar placeholder
/// - Name and email line placeholders
/// - Badge/status placeholder
class ProfileCardSkeleton extends StatelessWidget {
  const ProfileCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            // Avatar placeholder
            const SkeletonCircle(size: 64),
            const SizedBox(width: 16),

            // User details
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Name placeholder
                  SkeletonLine(
                    width: MediaQuery.of(context).size.width * 0.4,
                    height: 20,
                    borderRadius: 4,
                  ),
                  const SizedBox(height: 8),

                  // Email placeholder
                  SkeletonLine(
                    width: MediaQuery.of(context).size.width * 0.5,
                    height: 14,
                    borderRadius: 4,
                  ),
                  const SizedBox(height: 8),

                  // Badge/status placeholder
                  SkeletonLine(
                    width: 80,
                    height: 20,
                    borderRadius: 10,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Skeleton loader for subscription plan cards.
///
/// Mimics the structure of [PlanCard] with:
/// - Plan name and tag chip placeholders
/// - Feature list item placeholders
/// - Price display placeholder
/// - Action button placeholder
class PlanCardSkeleton extends StatelessWidget {
  const PlanCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row: name + tag chip
            Row(
              children: [
                Expanded(
                  child: SkeletonLine(
                    width: MediaQuery.of(context).size.width * 0.35,
                    height: 24,
                    borderRadius: 4,
                  ),
                ),
                SkeletonLine(
                  width: 70,
                  height: 24,
                  borderRadius: 12,
                ),
              ],
            ),
            const SizedBox(height: 8),

            // Description placeholder
            SkeletonLine(
              width: MediaQuery.of(context).size.width * 0.7,
              height: 14,
              borderRadius: 4,
            ),
            const SizedBox(height: 16),

            // Feature list (3 items)
            ...List.generate(
              3,
              (index) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    const SkeletonCircle(size: 18),
                    const SizedBox(width: 8),
                    SkeletonLine(
                      width: MediaQuery.of(context).size.width * 0.5,
                      height: 14,
                      borderRadius: 4,
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            // Price display placeholder
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                SkeletonLine(
                  width: 100,
                  height: 28,
                  borderRadius: 4,
                ),
                const SizedBox(width: 8),
                SkeletonLine(
                  width: 60,
                  height: 14,
                  borderRadius: 4,
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Duration pill placeholder
            SkeletonLine(
              width: 50,
              height: 24,
              borderRadius: 12,
            ),
            const SizedBox(height: 16),

            // Action button placeholder
            SkeletonLine(
              width: double.infinity,
              height: 48,
              borderRadius: 8,
            ),
          ],
        ),
      ),
    );
  }
}

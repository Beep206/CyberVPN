import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/providers/notification_provider.dart';

/// A badge widget that displays the unread notification count.
///
/// Features:
/// - Red circular badge with white text
/// - Shows count up to 99, displays '99+' for counts above 99
/// - Hides automatically when count is 0
/// - Scale animation when count changes from/to 0
/// - Designed to overlay a bell icon in the app bar
///
/// Usage:
/// ```dart
/// Stack(
///   clipBehavior: Clip.none,
///   children: [
///     IconButton(
///       icon: Icon(Icons.notifications),
///       onPressed: () {},
///     ),
///     Positioned(
///       top: 8,
///       right: 8,
///       child: NotificationBadge(),
///     ),
///   ],
/// )
/// ```
class NotificationBadge extends ConsumerWidget {
  const NotificationBadge({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final count = ref.watch(unreadCountProvider);

    return AnimatedScale(
      scale: count > 0 ? 1.0 : 0.0,
      duration: AnimDurations.medium,
      curve: Curves.easeInOut,
      child: count > 0 ? _BadgeContent(count: count) : const SizedBox.shrink(),
    );
  }
}

/// The visual content of the badge (red circle with count text).
class _BadgeContent extends StatelessWidget {
  const _BadgeContent({required this.count});

  final int count;

  /// Formats the count for display.
  /// Shows the actual count if <= 99, or '99+' if > 99.
  String get _displayText => count > 99 ? '99+' : count.toString();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      constraints: const BoxConstraints(
        minWidth: 18,
        minHeight: 18,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: theme.colorScheme.error,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: theme.colorScheme.error.withValues(alpha: 0.4),
            blurRadius: 4,
            spreadRadius: 0,
          ),
        ],
      ),
      child: Center(
        child: Text(
          _displayText,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 11,
            fontWeight: FontWeight.bold,
            height: 1.2,
          ),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}

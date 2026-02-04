import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/features/notifications/presentation/widgets/notification_badge.dart';

/// Example demonstrating how to use [NotificationBadge] with a bell icon
/// in an app bar or terminal header.
///
/// This file serves as documentation and can be referenced when implementing
/// the badge in actual UI components.
class NotificationBadgeUsageExample extends StatelessWidget {
  const NotificationBadgeUsageExample({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notification Badge Example'),
        actions: [
          // Example 1: Badge on IconButton in AppBar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8.0),
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                IconButton(
                  icon: const Icon(Icons.notifications_outlined),
                  onPressed: () {
                    // Navigate to notification center
                  },
                  tooltip: 'Notifications',
                ),
                const Positioned(
                  top: 8,
                  right: 8,
                  child: NotificationBadge(),
                ),
              ],
            ),
          ),
        ],
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Example 2: Badge on custom bell icon
            Stack(
              clipBehavior: Clip.none,
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.1),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.notifications,
                    size: 28,
                  ),
                ),
                const Positioned(
                  top: 0,
                  right: 0,
                  child: NotificationBadge(),
                ),
              ],
            ),
            const SizedBox(height: 32),

            // Example 3: Badge positioning variants
            const Text(
              'Badge automatically scales in/out when count changes',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 8),
            const Text(
              'Shows count up to 99, then displays "99+"',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 8),
            const Text(
              'Hides when count is 0',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }
}

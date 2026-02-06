import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/providers/notification_provider.dart';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Maps each [NotificationType] to a representative icon.
const _typeIcons = <NotificationType, IconData>{
  NotificationType.subscriptionExpiring: Icons.timer_outlined,
  NotificationType.expired: Icons.cancel_outlined,
  NotificationType.paymentConfirmed: Icons.payment_outlined,
  NotificationType.referralJoined: Icons.group_add_outlined,
  NotificationType.securityAlert: Icons.shield_outlined,
  NotificationType.promotional: Icons.local_offer_outlined,
  NotificationType.serverMaintenance: Icons.build_outlined,
  NotificationType.appUpdate: Icons.system_update_outlined,
};

// ---------------------------------------------------------------------------
// NotificationCenterScreen
// ---------------------------------------------------------------------------

/// Notification center screen displaying all in-app notifications.
///
/// Features:
/// - ListView of notifications with icon, title, body preview, timestamp,
///   and read/unread indicator dot.
/// - Swipe-to-dismiss to delete a notification.
/// - Tap to mark as read and navigate to the notification's [actionRoute].
/// - "Mark all as read" action in the app bar when unread notifications exist.
/// - Empty state illustration when no notifications are present.
class NotificationCenterScreen extends ConsumerWidget {
  const NotificationCenterScreen({super.key});

  // ---- Helpers --------------------------------------------------------------

  /// Returns a human-readable relative timestamp string.
  String _formatTimestamp(DateTime receivedAt) {
    final now = DateTime.now();
    final diff = now.difference(receivedAt);

    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inMinutes < 60) return '${diff.inMinutes}m ago';
    if (diff.inHours < 24) return '${diff.inHours}h ago';
    if (diff.inDays < 7) return '${diff.inDays}d ago';
    if (diff.inDays < 30) return '${(diff.inDays / 7).floor()}w ago';
    return '${(diff.inDays / 30).floor()}mo ago';
  }

  /// Returns the icon for a given [NotificationType].
  IconData _iconForType(NotificationType type) {
    return _typeIcons[type] ?? Icons.notifications_outlined;
  }

  // ---- Build ----------------------------------------------------------------

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final asyncState = ref.watch(notificationProvider);
    final unreadCount = ref.watch(unreadCountProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          if (unreadCount > 0)
            TextButton(
              key: const Key('btn_mark_all_read'),
              onPressed: () {
                unawaited(ref.read(notificationProvider.notifier).markAllAsRead());
              },
              child: const Text('Mark all read'),
            ),
        ],
      ),
      body: asyncState.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, _) => _buildError(context, ref, error),
        data: (state) {
          if (state.notifications.isEmpty) {
            return _buildEmptyState(context);
          }
          return _buildNotificationList(context, ref, state.notifications);
        },
      ),
    );
  }

  // ---- Error state ----------------------------------------------------------

  Widget _buildError(BuildContext context, WidgetRef ref, Object error) {
    final theme = Theme.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
          const SizedBox(height: 12),
          Text('Failed to load notifications',
              style: theme.textTheme.bodyLarge),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: () => ref.invalidate(notificationProvider),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  // ---- Empty state ----------------------------------------------------------

  Widget _buildEmptyState(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Center(
      key: const Key('empty_state'),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.notifications_off_outlined,
            size: 64,
            color: colorScheme.onSurfaceVariant.withValues(alpha: 0.5),
          ),
          const SizedBox(height: 16),
          Text(
            'No notifications yet',
            style: theme.textTheme.titleMedium?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'When you receive notifications, they will appear here.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: colorScheme.onSurfaceVariant.withValues(alpha: 0.7),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  // ---- Notification list ----------------------------------------------------

  Widget _buildNotificationList(
    BuildContext context,
    WidgetRef ref,
    List<AppNotification> notifications,
  ) {
    return ListView.builder(
      itemCount: notifications.length,
      padding: const EdgeInsets.only(bottom: 80),
      itemBuilder: (context, index) {
        final notification = notifications[index];
        return _NotificationTile(
          key: ValueKey(notification.id),
          notification: notification,
          icon: _iconForType(notification.type),
          timestamp: _formatTimestamp(notification.receivedAt),
          onTap: () => _onNotificationTap(context, ref, notification),
          onDismissed: () => _onNotificationDismissed(context, ref, notification),
        );
      },
    );
  }

  // ---- Actions --------------------------------------------------------------

  void _onNotificationTap(
    BuildContext context,
    WidgetRef ref,
    AppNotification notification,
  ) {
    if (!notification.isRead) {
      unawaited(ref.read(notificationProvider.notifier).markAsRead(notification.id));
    }
    if (notification.actionRoute != null &&
        notification.actionRoute!.isNotEmpty) {
      unawaited(context.push(notification.actionRoute!));
    }
  }

  void _onNotificationDismissed(
    BuildContext context,
    WidgetRef ref,
    AppNotification notification,
  ) {
    unawaited(ref.read(notificationProvider.notifier).delete(notification.id));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Notification dismissed'),
        duration: Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// _NotificationTile (private widget)
// ---------------------------------------------------------------------------

/// A single notification item inside the notification list.
///
/// Shows the notification type icon, title, body preview (max 2 lines),
/// relative timestamp, and a colored dot indicating read/unread status.
/// Wrapped in a [Dismissible] for swipe-to-delete functionality.
class _NotificationTile extends StatelessWidget {
  const _NotificationTile({
    required this.notification,
    required this.icon,
    required this.timestamp,
    required this.onTap,
    required this.onDismissed,
    super.key,
  });

  final AppNotification notification;
  final IconData icon;
  final String timestamp;
  final VoidCallback onTap;
  final VoidCallback onDismissed;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Dismissible(
      key: ValueKey('dismiss_${notification.id}'),
      direction: DismissDirection.endToStart,
      onDismissed: (_) => onDismissed(),
      background: Container(
        alignment: AlignmentDirectional.centerEnd,
        padding: const EdgeInsetsDirectional.only(end: 20),
        color: colorScheme.error,
        child: Icon(
          Icons.delete_outline,
          color: colorScheme.onError,
        ),
      ),
      child: ListTile(
        onTap: onTap,
        leading: CircleAvatar(
          backgroundColor: notification.isRead
              ? colorScheme.surfaceContainerHighest
              : colorScheme.primaryContainer,
          child: Icon(
            icon,
            size: 20,
            color: notification.isRead
                ? colorScheme.onSurfaceVariant
                : colorScheme.onPrimaryContainer,
          ),
        ),
        title: Text(
          notification.title,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: theme.textTheme.bodyLarge?.copyWith(
            fontWeight: notification.isRead ? FontWeight.normal : FontWeight.w600,
          ),
        ),
        subtitle: Text(
          notification.body,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: theme.textTheme.bodySmall?.copyWith(
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              timestamp,
              style: theme.textTheme.labelSmall?.copyWith(
                color: colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 4),
            if (!notification.isRead)
              Container(
                key: const Key('unread_dot'),
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: colorScheme.primary,
                  shape: BoxShape.circle,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

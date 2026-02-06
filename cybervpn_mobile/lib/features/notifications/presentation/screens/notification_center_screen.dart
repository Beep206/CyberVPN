import 'package:flutter/material.dart';
import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
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
  String _formatTimestamp(DateTime receivedAt, AppLocalizations l10n) {
    final now = DateTime.now();
    final diff = now.difference(receivedAt);

    if (diff.inMinutes < 1) return l10n.notificationTimeJustNow;
    if (diff.inMinutes < 60) return l10n.notificationTimeMinutesAgo(diff.inMinutes);
    if (diff.inHours < 24) return l10n.notificationTimeHoursAgo(diff.inHours);
    if (diff.inDays < 7) return l10n.notificationTimeDaysAgo(diff.inDays);
    if (diff.inDays < 30) return l10n.notificationTimeWeeksAgo((diff.inDays / 7).floor());
    return l10n.notificationTimeMonthsAgo((diff.inDays / 30).floor());
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
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.notificationCenterTitle),
        actions: [
          if (unreadCount > 0)
            TextButton(
              key: const Key('btn_mark_all_read'),
              onPressed: () {
                unawaited(ref.read(notificationProvider.notifier).markAllAsRead());
              },
              child: Text(l10n.notificationCenterMarkAllRead),
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
    final l10n = AppLocalizations.of(context);

    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.error_outline, size: 48, color: theme.colorScheme.error),
          const SizedBox(height: 12),
          Text(l10n.notificationCenterLoadError,
              style: theme.textTheme.bodyLarge),
          const SizedBox(height: 8),
          FilledButton.tonal(
            onPressed: () => ref.invalidate(notificationProvider),
            child: Text(l10n.retry),
          ),
        ],
      ),
    );
  }

  // ---- Empty state ----------------------------------------------------------

  Widget _buildEmptyState(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;
    final l10n = AppLocalizations.of(context);

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
            l10n.notificationCenterEmpty,
            style: theme.textTheme.titleMedium?.copyWith(
              color: colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            l10n.notificationCenterEmptyDescription,
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
    final l10n = AppLocalizations.of(context);

    return ListView.builder(
      itemCount: notifications.length,
      padding: const EdgeInsets.only(bottom: 80),
      itemBuilder: (context, index) {
        final notification = notifications[index];
        return _NotificationTile(
          key: ValueKey(notification.id),
          notification: notification,
          icon: _iconForType(notification.type),
          timestamp: _formatTimestamp(notification.receivedAt, l10n),
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
    final l10n = AppLocalizations.of(context);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(l10n.notificationCenterDismissed),
        duration: const Duration(seconds: 2),
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

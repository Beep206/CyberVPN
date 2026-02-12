import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/auth/domain/services/offline_session_service.dart';

/// A banner that displays when the app is offline.
///
/// Shows a message indicating the app is in offline mode with limited
/// functionality. Automatically hides when connectivity is restored.
class OfflineBanner extends ConsumerWidget {
  /// Optional timestamp of last successful sync.
  final DateTime? lastSyncTime;

  /// Whether to show in a compact mode (just icon and short text).
  final bool compact;

  const OfflineBanner({
    super.key,
    this.lastSyncTime,
    this.compact = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isOnline = ref.watch(isOnlineProvider);

    return isOnline.when(
      data: (online) {
        if (online) return const SizedBox.shrink();
        return _OfflineBannerContent(
          lastSyncTime: lastSyncTime,
          compact: compact,
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, _) => const SizedBox.shrink(),
    );
  }
}

class _OfflineBannerContent extends StatelessWidget {
  final DateTime? lastSyncTime;
  final bool compact;

  const _OfflineBannerContent({
    this.lastSyncTime,
    this.compact = false,
  });

  String _formatLastSync(AppLocalizations l10n) {
    if (lastSyncTime == null) return '';

    final now = DateTime.now();
    final diff = now.difference(lastSyncTime!);

    if (diff.inMinutes < 1) {
      return l10n.offlineLastSyncJustNow;
    } else if (diff.inMinutes < 60) {
      return l10n.offlineLastSyncMinutes(diff.inMinutes);
    } else if (diff.inHours < 24) {
      return l10n.offlineLastSyncHours(diff.inHours);
    } else {
      return l10n.offlineLastSyncDays(diff.inDays);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);

    if (compact) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: theme.colorScheme.errorContainer,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.cloud_off,
              size: 16,
              color: theme.colorScheme.onErrorContainer,
            ),
            const SizedBox(width: 6),
            Text(
              l10n.offlineLabel,
              style: theme.textTheme.labelSmall?.copyWith(
                color: theme.colorScheme.onErrorContainer,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      );
    }

    return Material(
      color: theme.colorScheme.errorContainer,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Icon(
                Icons.cloud_off,
                size: 20,
                color: theme.colorScheme.onErrorContainer,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      l10n.offlineYouAreOffline,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        color: theme.colorScheme.onErrorContainer,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (lastSyncTime != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        _formatLastSync(l10n),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: theme.colorScheme.onErrorContainer
                              .withValues(alpha: 0.8),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              Text(
                l10n.offlineSomeFeaturesUnavailable,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onErrorContainer.withValues(alpha: 0.8),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// A wrapper that disables its child when offline.
///
/// Use this to wrap buttons or interactive elements that require
/// network connectivity.
class OfflineDisabled extends ConsumerWidget {
  /// The child widget to conditionally disable.
  final Widget child;

  /// Whether to show a tooltip explaining why the widget is disabled.
  final bool showTooltip;

  /// Custom tooltip message.
  final String? tooltipMessage;

  const OfflineDisabled({
    super.key,
    required this.child,
    this.showTooltip = true,
    this.tooltipMessage,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isOnline = ref.watch(isOnlineProvider);

    return isOnline.when(
      data: (online) {
        if (online) return child;

        final Widget disabledChild = IgnorePointer(
          child: Opacity(
            opacity: 0.5,
            child: child,
          ),
        );

        if (showTooltip) {
          return Tooltip(
            message: tooltipMessage ?? AppLocalizations.of(context).offlineNotAvailable,
            child: disabledChild,
          );
        }

        return disabledChild;
      },
      loading: () => child,
      error: (_, _) => child,
    );
  }
}

/// A small offline indicator icon for use in app bars.
class OfflineIndicatorIcon extends ConsumerWidget {
  final double size;

  const OfflineIndicatorIcon({
    super.key,
    this.size = 20,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final isOnline = ref.watch(isOnlineProvider);
    final theme = Theme.of(context);

    return isOnline.when(
      data: (online) {
        if (online) return const SizedBox.shrink();
        return Tooltip(
          message: AppLocalizations.of(context).offlineYouAreOffline,
          child: Icon(
            Icons.cloud_off,
            size: size,
            color: theme.colorScheme.error,
          ),
        );
      },
      loading: () => const SizedBox.shrink(),
      error: (_, _) => const SizedBox.shrink(),
    );
  }
}

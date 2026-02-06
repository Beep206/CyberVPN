import 'dart:async';
import 'dart:ui';

import 'package:flutter/material.dart';

import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';

/// Type of in-app banner notification.
enum BannerNotificationType {
  error,
  success,
  info,
}

/// Configuration for a banner notification.
class BannerConfig {
  const BannerConfig({
    required this.type,
    required this.title,
    required this.message,
    this.onTap,
    this.duration = const Duration(seconds: 4),
  });

  final BannerNotificationType type;
  final String title;
  final String message;
  final VoidCallback? onTap;
  final Duration duration;

  /// Creates a [BannerConfig] from an [AppNotification].
  factory BannerConfig.fromAppNotification(
    AppNotification notification, {
    VoidCallback? onTap,
  }) {
    return BannerConfig(
      type: _mapNotificationType(notification.type),
      title: notification.title,
      message: notification.body,
      onTap: onTap,
    );
  }

  static BannerNotificationType _mapNotificationType(NotificationType type) {
    switch (type) {
      case NotificationType.securityAlert:
      case NotificationType.expired:
        return BannerNotificationType.error;
      case NotificationType.paymentConfirmed:
      case NotificationType.referralJoined:
        return BannerNotificationType.success;
      case NotificationType.subscriptionExpiring:
      case NotificationType.promotional:
      case NotificationType.serverMaintenance:
      case NotificationType.appUpdate:
        return BannerNotificationType.info;
    }
  }
}

/// Displays an in-app notification banner at the top of the screen.
///
/// Features:
/// - Slide-down animation from top
/// - Auto-dismiss after [duration]
/// - Swipe up to dismiss
/// - Tap to navigate
/// - Type-based color styling (error, success, info)
/// - Overlay above current content
class InAppBanner extends StatefulWidget {
  const InAppBanner({
    super.key,
    required this.config,
  });

  final BannerConfig config;

  /// Shows a banner notification above the current screen.
  ///
  /// Returns a function that can be called to manually dismiss the banner.
  static VoidCallback show(
    BuildContext context,
    BannerConfig config,
  ) {
    final overlay = Overlay.of(context);
    late final OverlayEntry entry;

    entry = OverlayEntry(
      builder: (context) => _BannerOverlay(
        config: config,
        onDismiss: () => entry.remove(),
      ),
    );

    overlay.insert(entry);

    // Return a function to manually remove the overlay.
    return () {
      if (entry.mounted) {
        entry.remove();
      }
    };
  }

  @override
  State<InAppBanner> createState() => _InAppBannerState();
}

class _InAppBannerState extends State<InAppBanner>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -1),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeOut,
      ),
    );

    // Start slide-in animation.
    unawaited(_controller.forward());
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _animateOut() async {
    await _controller.reverse();
  }

  @override
  Widget build(BuildContext context) {
    return SlideTransition(
      position: _slideAnimation,
      child: _BannerContent(
        config: widget.config,
        onDismiss: _animateOut,
      ),
    );
  }
}

/// Internal overlay wrapper that handles auto-dismiss and swipe gestures.
class _BannerOverlay extends StatefulWidget {
  const _BannerOverlay({
    required this.config,
    required this.onDismiss,
  });

  final BannerConfig config;
  final VoidCallback onDismiss;

  @override
  State<_BannerOverlay> createState() => _BannerOverlayState();
}

class _BannerOverlayState extends State<_BannerOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<Offset> _slideAnimation;
  Timer? _autoDismissTimer;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, -1),
      end: Offset.zero,
    ).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeOut,
      ),
    );

    // Start slide-in animation.
    unawaited(_controller.forward());

    // Start auto-dismiss timer.
    _autoDismissTimer = Timer(widget.config.duration, _dismiss);
  }

  @override
  void dispose() {
    _autoDismissTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  Future<void> _dismiss() async {
    _autoDismissTimer?.cancel();
    await _controller.reverse();
    if (mounted) {
      widget.onDismiss();
    }
  }

  void _handleVerticalDragEnd(DragEndDetails details) {
    // Swipe up to dismiss (negative velocity).
    if (details.primaryVelocity != null && details.primaryVelocity! < -200) {
      unawaited(_dismiss());
    }
  }

  void _handleTap() {
    widget.config.onTap?.call();
    unawaited(_dismiss());
  }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: 0,
      left: 0,
      right: 0,
      child: SafeArea(
        child: GestureDetector(
          onTap: _handleTap,
          onVerticalDragEnd: _handleVerticalDragEnd,
          child: SlideTransition(
            position: _slideAnimation,
            child: _BannerContent(
              config: widget.config,
              onDismiss: _dismiss,
            ),
          ),
        ),
      ),
    );
  }
}

/// The visual content of the banner.
class _BannerContent extends StatelessWidget {
  const _BannerContent({
    required this.config,
    required this.onDismiss,
  });

  final BannerConfig config;
  final VoidCallback onDismiss;

  Color _getAccentColor(ColorScheme colorScheme) {
    switch (config.type) {
      case BannerNotificationType.error:
        return colorScheme.error;
      case BannerNotificationType.success:
        return colorScheme.tertiary;
      case BannerNotificationType.info:
        return colorScheme.primary;
    }
  }

  IconData _getIcon() {
    switch (config.type) {
      case BannerNotificationType.error:
        return Icons.error_outline;
      case BannerNotificationType.success:
        return Icons.check_circle_outline;
      case BannerNotificationType.info:
        return Icons.info_outline;
    }
  }

  @override
  Widget build(BuildContext context) {
    final accentColor = _getAccentColor(Theme.of(context).colorScheme);
    final icon = _getIcon();

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.85),
        borderRadius: const BorderRadius.only(
          bottomLeft: Radius.circular(12),
          bottomRight: Radius.circular(12),
          topLeft: Radius.circular(12),
          topRight: Radius.circular(12),
        ),
        border: Border(
          left: BorderSide(
            color: accentColor,
            width: 4,
          ),
        ),
      ),
      child: ClipRRect(
        borderRadius: const BorderRadius.only(
          bottomLeft: Radius.circular(12),
          bottomRight: Radius.circular(12),
          topLeft: Radius.circular(12),
          topRight: Radius.circular(12),
        ),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Leading icon
                Icon(
                  icon,
                  color: accentColor,
                  size: 24,
                ),
                const SizedBox(width: 12),

                // Title and message
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        config.title,
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        config.message,
                        style: TextStyle(
                          fontSize: 12,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
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

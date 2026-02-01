// ignore_for_file: unused_element

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/widgets/in_app_banner.dart';

/// Example usage of [InAppBanner] widget.
///
/// This file demonstrates how to integrate the in-app notification banner
/// into your application to show foreground notifications.
///
/// USAGE PATTERNS:
///
/// 1. Show a simple banner with auto-dismiss:
/// ```dart
/// InAppBanner.show(
///   context,
///   BannerConfig(
///     type: BannerNotificationType.success,
///     title: 'Connected',
///     message: 'VPN connection established',
///   ),
/// );
/// ```
///
/// 2. Show a banner from AppNotification with navigation:
/// ```dart
/// final notification = AppNotification(...);
/// InAppBanner.show(
///   context,
///   BannerConfig.fromAppNotification(
///     notification,
///     onTap: () {
///       // Navigate to relevant screen
///       context.push(notification.actionRoute ?? '/notifications');
///     },
///   ),
/// );
/// ```
///
/// 3. Manual dismiss control:
/// ```dart
/// final dismiss = InAppBanner.show(context, config);
/// // Later, manually dismiss:
/// dismiss();
/// ```
///
/// INTEGRATION WITH NOTIFICATION PROVIDER:
///
/// To automatically show banners for incoming FCM notifications,
/// you can listen to the notification stream in your app's root widget
/// or a dedicated notification listener widget.

/// Example: Notification listener widget that shows banners automatically.
class _NotificationBannerListener extends ConsumerStatefulWidget {
  const _NotificationBannerListener({required this.child});

  final Widget child;

  @override
  ConsumerState<_NotificationBannerListener> createState() =>
      _NotificationBannerListenerState();
}

class _NotificationBannerListenerState
    extends ConsumerState<_NotificationBannerListener> {
  @override
  Widget build(BuildContext context) {
    // Listen to new notifications from provider
    // When a new notification arrives, show banner

    // Example implementation (pseudo-code):
    // ref.listen(notificationProvider, (previous, next) {
    //   final newNotifications = next.value?.notifications ?? [];
    //   if (newNotifications.isNotEmpty) {
    //     final latest = newNotifications.first;
    //     _showBannerForNotification(latest);
    //   }
    // });

    return widget.child;
  }

  void _showBannerForNotification(AppNotification notification) {
    InAppBanner.show(
      context,
      BannerConfig.fromAppNotification(
        notification,
        onTap: () {
          // Navigate to notification details or relevant screen
          final route = notification.actionRoute;
          if (route != null) {
            context.push(route);
          } else {
            context.push('/notifications');
          }
        },
      ),
    );
  }
}

/// Example: Manual banner trigger in a screen
class _ExampleScreen extends StatelessWidget {
  const _ExampleScreen();

  void _showSuccessBanner(BuildContext context) {
    InAppBanner.show(
      context,
      const BannerConfig(
        type: BannerNotificationType.success,
        title: 'Success',
        message: 'Operation completed successfully',
      ),
    );
  }

  void _showErrorBanner(BuildContext context) {
    InAppBanner.show(
      context,
      const BannerConfig(
        type: BannerNotificationType.error,
        title: 'Error',
        message: 'Something went wrong. Please try again.',
        duration: Duration(seconds: 6), // Custom duration
      ),
    );
  }

  void _showInfoBanner(BuildContext context) {
    InAppBanner.show(
      context,
      BannerConfig(
        type: BannerNotificationType.info,
        title: 'Server Maintenance',
        message: 'Server will be under maintenance from 2 AM to 4 AM UTC',
        onTap: () {
          // Navigate to server status page
          context.push('/servers');
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Banner Example')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            ElevatedButton(
              onPressed: () => _showSuccessBanner(context),
              child: const Text('Show Success Banner'),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => _showErrorBanner(context),
              child: const Text('Show Error Banner'),
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => _showInfoBanner(context),
              child: const Text('Show Info Banner'),
            ),
          ],
        ),
      ),
    );
  }
}

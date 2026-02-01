import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/features/notifications/domain/entities/app_notification.dart';
import 'package:cybervpn_mobile/features/notifications/presentation/widgets/in_app_banner.dart';

void main() {
  Widget buildTestWidget(Widget child) {
    return MaterialApp(
      home: Scaffold(
        body: Center(
          child: child,
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // BannerConfig.fromAppNotification
  // ---------------------------------------------------------------------------

  group('BannerConfig.fromAppNotification', () {
    test('maps security alert to error type', () {
      final notification = AppNotification(
        id: '1',
        type: NotificationType.securityAlert,
        title: 'Security Alert',
        body: 'Suspicious activity detected',
        receivedAt: DateTime.now(),
      );

      final config = BannerConfig.fromAppNotification(notification);

      expect(config.type, BannerNotificationType.error);
      expect(config.title, 'Security Alert');
      expect(config.message, 'Suspicious activity detected');
    });

    test('maps payment confirmed to success type', () {
      final notification = AppNotification(
        id: '2',
        type: NotificationType.paymentConfirmed,
        title: 'Payment Confirmed',
        body: 'Your payment was successful',
        receivedAt: DateTime.now(),
      );

      final config = BannerConfig.fromAppNotification(notification);

      expect(config.type, BannerNotificationType.success);
    });

    test('maps promotional to info type', () {
      final notification = AppNotification(
        id: '3',
        type: NotificationType.promotional,
        title: 'Special Offer',
        body: 'Get 50% off premium',
        receivedAt: DateTime.now(),
      );

      final config = BannerConfig.fromAppNotification(notification);

      expect(config.type, BannerNotificationType.info);
    });
  });

  // ---------------------------------------------------------------------------
  // InAppBanner rendering
  // ---------------------------------------------------------------------------

  group('InAppBanner rendering', () {
    testWidgets('renders title and message', (tester) async {
      const config = BannerConfig(
        type: BannerNotificationType.info,
        title: 'Test Title',
        message: 'Test message body',
      );

      await tester.pumpWidget(
        buildTestWidget(
          const InAppBanner(config: config),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Test Title'), findsOneWidget);
      expect(find.text('Test message body'), findsOneWidget);
    });

    testWidgets('shows error icon for error type', (tester) async {
      const config = BannerConfig(
        type: BannerNotificationType.error,
        title: 'Error',
        message: 'Something went wrong',
      );

      await tester.pumpWidget(
        buildTestWidget(
          const InAppBanner(config: config),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });

    testWidgets('shows success icon for success type', (tester) async {
      const config = BannerConfig(
        type: BannerNotificationType.success,
        title: 'Success',
        message: 'Operation completed',
      );

      await tester.pumpWidget(
        buildTestWidget(
          const InAppBanner(config: config),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.check_circle_outline), findsOneWidget);
    });

    testWidgets('shows info icon for info type', (tester) async {
      const config = BannerConfig(
        type: BannerNotificationType.info,
        title: 'Info',
        message: 'New update available',
      );

      await tester.pumpWidget(
        buildTestWidget(
          const InAppBanner(config: config),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.info_outline), findsOneWidget);
    });

    testWidgets('truncates long message to 2 lines', (tester) async {
      const config = BannerConfig(
        type: BannerNotificationType.info,
        title: 'Long Message',
        message:
            'This is a very long message that should be truncated to only two lines maximum with an ellipsis at the end to indicate there is more text',
      );

      await tester.pumpWidget(
        buildTestWidget(
          const InAppBanner(config: config),
        ),
      );
      await tester.pumpAndSettle();

      // Find the message Text widget.
      final textFinder = find.text(config.message);
      expect(textFinder, findsOneWidget);

      // Verify maxLines is 2.
      final textWidget = tester.widget<Text>(textFinder);
      expect(textWidget.maxLines, 2);
      expect(textWidget.overflow, TextOverflow.ellipsis);
    });
  });

  // ---------------------------------------------------------------------------
  // InAppBanner.show overlay integration
  // ---------------------------------------------------------------------------

  group('InAppBanner.show', () {
    testWidgets('shows banner in overlay', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              return Scaffold(
                body: Center(
                  child: ElevatedButton(
                    onPressed: () {
                      InAppBanner.show(
                        context,
                        const BannerConfig(
                          type: BannerNotificationType.info,
                          title: 'Overlay Test',
                          message: 'Banner shown in overlay',
                        ),
                      );
                    },
                    child: const Text('Show Banner'),
                  ),
                ),
              );
            },
          ),
        ),
      );

      // Initially, banner should not be visible.
      expect(find.text('Overlay Test'), findsNothing);

      // Tap button to show banner.
      await tester.tap(find.text('Show Banner'));
      await tester.pump();
      await tester.pumpAndSettle();

      // Banner should now be visible.
      expect(find.text('Overlay Test'), findsOneWidget);
      expect(find.text('Banner shown in overlay'), findsOneWidget);
    });

    testWidgets('auto-dismisses after duration', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              return Scaffold(
                body: Center(
                  child: ElevatedButton(
                    onPressed: () {
                      InAppBanner.show(
                        context,
                        const BannerConfig(
                          type: BannerNotificationType.info,
                          title: 'Auto Dismiss',
                          message: 'This will disappear',
                          duration: Duration(seconds: 2),
                        ),
                      );
                    },
                    child: const Text('Show Banner'),
                  ),
                ),
              );
            },
          ),
        ),
      );

      // Show the banner.
      await tester.tap(find.text('Show Banner'));
      await tester.pump();
      await tester.pumpAndSettle();

      // Banner should be visible.
      expect(find.text('Auto Dismiss'), findsOneWidget);

      // Wait for auto-dismiss duration + animation time.
      await tester.pump(const Duration(seconds: 2));
      await tester.pumpAndSettle();

      // Banner should be dismissed.
      expect(find.text('Auto Dismiss'), findsNothing);
    });

    testWidgets('calls onTap and dismisses when tapped', (tester) async {
      var tapped = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              return Scaffold(
                body: Center(
                  child: ElevatedButton(
                    onPressed: () {
                      InAppBanner.show(
                        context,
                        BannerConfig(
                          type: BannerNotificationType.success,
                          title: 'Tap Test',
                          message: 'Tap me',
                          onTap: () => tapped = true,
                        ),
                      );
                    },
                    child: const Text('Show Banner'),
                  ),
                ),
              );
            },
          ),
        ),
      );

      // Show the banner.
      await tester.tap(find.text('Show Banner'));
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.text('Tap Test'), findsOneWidget);
      expect(tapped, isFalse);

      // Tap the banner.
      await tester.tap(find.text('Tap Test'));
      await tester.pumpAndSettle();

      // onTap should be called and banner dismissed.
      expect(tapped, isTrue);
      expect(find.text('Tap Test'), findsNothing);
    });

    testWidgets('dismisses on swipe up gesture', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              return Scaffold(
                body: Center(
                  child: ElevatedButton(
                    onPressed: () {
                      InAppBanner.show(
                        context,
                        const BannerConfig(
                          type: BannerNotificationType.info,
                          title: 'Swipe Test',
                          message: 'Swipe up to dismiss',
                        ),
                      );
                    },
                    child: const Text('Show Banner'),
                  ),
                ),
              );
            },
          ),
        ),
      );

      // Show the banner.
      await tester.tap(find.text('Show Banner'));
      await tester.pump();
      await tester.pumpAndSettle();

      expect(find.text('Swipe Test'), findsOneWidget);

      // Perform swipe up gesture with fling velocity to trigger dismissal.
      await tester.fling(
        find.text('Swipe Test'),
        const Offset(0, -500),
        500.0, // Velocity in pixels per second
      );
      await tester.pumpAndSettle();

      // Banner should be dismissed.
      expect(find.text('Swipe Test'), findsNothing);
    });
  });

  // ---------------------------------------------------------------------------
  // Slide animation
  // ---------------------------------------------------------------------------

  group('Slide animation', () {
    testWidgets('banner slides down from top', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) {
              return Scaffold(
                body: Center(
                  child: ElevatedButton(
                    onPressed: () {
                      InAppBanner.show(
                        context,
                        const BannerConfig(
                          type: BannerNotificationType.info,
                          title: 'Animation Test',
                          message: 'Sliding down',
                        ),
                      );
                    },
                    child: const Text('Show Banner'),
                  ),
                ),
              );
            },
          ),
        ),
      );

      // Show the banner.
      await tester.tap(find.text('Show Banner'));
      await tester.pump();

      // Banner starts off-screen (animation in progress).
      // We can verify SlideTransition exists (multiple may exist due to navigation).
      expect(find.byType(SlideTransition), findsWidgets);

      // Complete the animation.
      await tester.pumpAndSettle();

      // Banner is now fully visible.
      expect(find.text('Animation Test'), findsOneWidget);
    });
  });
}

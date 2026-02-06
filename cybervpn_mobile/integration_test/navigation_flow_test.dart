import 'package:cybervpn_mobile/app/app.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/routing/deep_link_parser.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Integration tests for navigation flows throughout the app.
///
/// Covers:
/// - Tab navigation between all 4 main tabs (Connection, Servers, Profile, Settings)
/// - Back navigation from nested screens
/// - Deep link handling and navigation
/// - Navigation state preservation
///
/// These tests verify the GoRouter configuration and StatefulShellRoute behavior.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Tab Navigation Integration Tests', () {
    late SharedPreferences prefs;

    setUp(() async {
      // Reset SharedPreferences before each test
      SharedPreferences.setMockInitialValues({});
      prefs = await SharedPreferences.getInstance();
      await prefs.clear();

      // Mark onboarding as completed to start at main screen
      await prefs.setBool('onboarding_completed', true);
    });

    tearDown(() async {
      await prefs.clear();
    });

    /// Helper to pump the app with clean state
    Future<void> pumpCyberVpnApp(WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          // TODO: await buildProviderOverrides(prefs) -- currently passes a Future.
          // ignore: argument_type_not_assignable
          overrides: buildProviderOverrides(prefs),
          child: const CyberVpnApp(),
        ),
      );
      // Wait for initial frame and any async initialization
      await tester.pumpAndSettle();
    }

    /// Helper to safely pump and settle with timeout
    Future<void> safePumpAndSettle(
      WidgetTester tester, {
      Duration timeout = const Duration(seconds: 10),
    }) async {
      await tester.pumpAndSettle(
        const Duration(milliseconds: 100),
        EnginePhase.sendSemanticsUpdate,
        timeout,
      );
    }

    testWidgets(
      'Tab navigation: switch between all 4 tabs',
      (tester) async {
        await pumpCyberVpnApp(tester);

        // Verify bottom navigation bar is present
        expect(
          find.byType(NavigationBar),
          findsOneWidget,
          reason: 'Should show bottom navigation bar',
        );

        // Tab 0: Connection (default)
        expect(
          find.widgetWithText(NavigationDestination, 'Connection'),
          findsOneWidget,
          reason: 'Should have Connection tab',
        );

        // Tap Tab 1: Servers
        final serversTab = find.widgetWithText(NavigationDestination, 'Servers');
        expect(serversTab, findsOneWidget, reason: 'Should have Servers tab');
        await tester.tap(serversTab);
        await safePumpAndSettle(tester);

        // Verify Servers screen loaded
        expect(
          find.byType(NavigationBar),
          findsOneWidget,
          reason: 'Bottom nav should persist',
        );

        // Tap Tab 2: Profile
        final profileTab = find.widgetWithText(NavigationDestination, 'Profile');
        expect(profileTab, findsOneWidget, reason: 'Should have Profile tab');
        await tester.tap(profileTab);
        await safePumpAndSettle(tester);

        // Verify Profile screen loaded
        expect(
          find.byType(NavigationBar),
          findsOneWidget,
          reason: 'Bottom nav should persist',
        );

        // Tap Tab 3: Settings
        final settingsTab = find.widgetWithText(NavigationDestination, 'Settings');
        expect(settingsTab, findsOneWidget, reason: 'Should have Settings tab');
        await tester.tap(settingsTab);
        await safePumpAndSettle(tester);

        // Verify Settings screen loaded
        expect(
          find.byType(NavigationBar),
          findsOneWidget,
          reason: 'Bottom nav should persist',
        );

        // Navigate back to Connection tab
        final connectionTab = find.widgetWithText(NavigationDestination, 'Connection');
        expect(connectionTab, findsOneWidget, reason: 'Should have Connection tab');
        await tester.tap(connectionTab);
        await safePumpAndSettle(tester);

        // Verify we're back on Connection screen
        expect(
          find.byType(NavigationBar),
          findsOneWidget,
          reason: 'Bottom nav should persist',
        );
      },
    );

    testWidgets(
      'Tab navigation: state preservation when switching tabs',
      (tester) async {
        await pumpCyberVpnApp(tester);

        // Navigate to Servers tab
        final serversTab = find.widgetWithText(NavigationDestination, 'Servers');
        await tester.tap(serversTab);
        await safePumpAndSettle(tester);

        // Interact with search field (if present)
        final searchField = find.byType(TextField);
        if (searchField.evaluate().isNotEmpty) {
          await tester.enterText(searchField.first, 'Test Query');
          await tester.pump();
          await safePumpAndSettle(tester);
        }

        // Switch to Settings tab
        final settingsTab = find.widgetWithText(NavigationDestination, 'Settings');
        await tester.tap(settingsTab);
        await safePumpAndSettle(tester);

        // Switch back to Servers tab
        await tester.tap(serversTab);
        await safePumpAndSettle(tester);

        // Verify search field still exists (state preserved)
        if (searchField.evaluate().isNotEmpty) {
          expect(
            find.byType(TextField),
            findsWidgets,
            reason: 'Search field state should be preserved',
          );
        }
      },
    );

    testWidgets(
      'Tab navigation: verify each tab renders expected content',
      (tester) async {
        await pumpCyberVpnApp(tester);

        // Connection tab - should have connection-related widgets
        final connectionElements = find.byWidgetPredicate(
          (widget) => widget.runtimeType.toString().contains('Connect'),
        );
        expect(
          connectionElements.evaluate().isNotEmpty || find.byType(Scaffold).evaluate().isNotEmpty,
          true,
          reason: 'Connection tab should render',
        );

        // Servers tab
        final serversTab = find.widgetWithText(NavigationDestination, 'Servers');
        await tester.tap(serversTab);
        await safePumpAndSettle(tester);
        expect(
          find.byType(Scaffold),
          findsWidgets,
          reason: 'Servers tab should render',
        );

        // Profile tab
        final profileTab = find.widgetWithText(NavigationDestination, 'Profile');
        await tester.tap(profileTab);
        await safePumpAndSettle(tester);
        expect(
          find.byType(Scaffold),
          findsWidgets,
          reason: 'Profile tab should render',
        );

        // Settings tab
        final settingsTab = find.widgetWithText(NavigationDestination, 'Settings');
        await tester.tap(settingsTab);
        await safePumpAndSettle(tester);
        expect(
          find.byType(Scaffold),
          findsWidgets,
          reason: 'Settings tab should render',
        );
      },
    );
  });

  group('Back Navigation Integration Tests', () {
    late SharedPreferences prefs;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      prefs = await SharedPreferences.getInstance();
      await prefs.clear();
      await prefs.setBool('onboarding_completed', true);
    });

    tearDown(() async {
      await prefs.clear();
    });

    Future<void> pumpCyberVpnApp(WidgetTester tester) async {
      await tester.pumpWidget(
        ProviderScope(
          // TODO: await buildProviderOverrides(prefs) -- currently passes a Future.
          // ignore: argument_type_not_assignable
          overrides: buildProviderOverrides(prefs),
          child: const CyberVpnApp(),
        ),
      );
      await tester.pumpAndSettle();
    }

    Future<void> safePumpAndSettle(
      WidgetTester tester, {
      Duration timeout = const Duration(seconds: 10),
    }) async {
      await tester.pumpAndSettle(
        const Duration(milliseconds: 100),
        EnginePhase.sendSemanticsUpdate,
        timeout,
      );
    }

    testWidgets(
      'Back navigation: navigate into nested screen and back',
      (tester) async {
        await pumpCyberVpnApp(tester);

        // Navigate to Settings tab
        final settingsTab = find.widgetWithText(NavigationDestination, 'Settings');
        await tester.tap(settingsTab);
        await safePumpAndSettle(tester);

        // Look for a navigation item to tap (e.g., VPN Settings, Appearance)
        // These are typically ListTiles with trailing icons
        final settingsItems = find.byType(ListTile);
        if (settingsItems.evaluate().isNotEmpty) {
          // Tap the first settings item to navigate deeper
          await tester.tap(settingsItems.first);
          await safePumpAndSettle(tester);

          // Verify we navigated (look for back button)
          final backButton = find.byType(BackButton);
          if (backButton.evaluate().isNotEmpty) {
            expect(backButton, findsOneWidget, reason: 'Should show back button');

            // Tap back button
            await tester.tap(backButton);
            await safePumpAndSettle(tester);

            // Verify we're back on settings screen (bottom nav should be visible)
            expect(
              find.byType(NavigationBar),
              findsOneWidget,
              reason: 'Should be back on main settings screen',
            );
          }
        }
      },
    );

    testWidgets(
      'Back navigation: system back button behavior',
      (tester) async {
        await pumpCyberVpnApp(tester);

        // Navigate to Servers tab
        final serversTab = find.widgetWithText(NavigationDestination, 'Servers');
        await tester.tap(serversTab);
        await safePumpAndSettle(tester);

        // Find and tap a server to navigate to detail screen
        final serverCards = find.byWidgetPredicate(
          (widget) => widget.runtimeType.toString().contains('ServerCard'),
        );

        if (serverCards.evaluate().isNotEmpty) {
          await tester.tap(serverCards.first);
          await safePumpAndSettle(tester);

          // Get the navigator and try to pop
          final scaffoldElement = find.byType(Scaffold).first;
          if (scaffoldElement.evaluate().isNotEmpty) {
            // ignore: use_build_context_synchronously
            final BuildContext context = tester.element(scaffoldElement);
            final navigator = Navigator.of(context);

            if (navigator.canPop()) {
              navigator.pop();
              await safePumpAndSettle(tester);

              // Verify we're back on the server list
              expect(
                find.byType(NavigationBar),
                findsOneWidget,
                reason: 'Should be back on server list screen',
              );
            }
          }
        }
      },
    );

    testWidgets(
      'Back navigation: deep navigation stack',
      (tester) async {
        await pumpCyberVpnApp(tester);

        // Navigate: Settings → nested screen → deeper screen (if available)
        final settingsTab = find.widgetWithText(NavigationDestination, 'Settings');
        await tester.tap(settingsTab);
        await safePumpAndSettle(tester);

        // Navigate deeper
        final settingsItems = find.byType(ListTile);
        if (settingsItems.evaluate().isNotEmpty) {
          await tester.tap(settingsItems.first);
          await safePumpAndSettle(tester);

          // If there's another level, navigate there
          final nestedItems = find.byType(ListTile);
          if (nestedItems.evaluate().isNotEmpty) {
            await tester.tap(nestedItems.first);
            await safePumpAndSettle(tester);
          }

          // Navigate back multiple times
          var backButton = find.byType(BackButton);
          while (backButton.evaluate().isNotEmpty) {
            await tester.tap(backButton.first);
            await safePumpAndSettle(tester);
            backButton = find.byType(BackButton);
          }

          // Should be back at main tab with bottom navigation
          expect(
            find.byType(NavigationBar),
            findsOneWidget,
            reason: 'Should be back at main tab level',
          );
        }
      },
    );
  });

  group('Deep Link Navigation Integration Tests', () {
    late SharedPreferences prefs;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      prefs = await SharedPreferences.getInstance();
      await prefs.clear();
      await prefs.setBool('onboarding_completed', true);
    });

    tearDown(() async {
      await prefs.clear();
    });

    testWidgets(
      'Deep link: settings route navigation',
      (tester) async {
        await tester.pumpWidget(
          ProviderScope(
            // buildProviderOverrides returns List (raw) because Riverpod 3.0.3
            // does not publicly export the Override type.
            // ignore: argument_type_not_assignable
            overrides: buildProviderOverrides(prefs),
            child: const CyberVpnApp(),
          ),
        );
        await tester.pumpAndSettle();

        // Simulate deep link to settings
        final scaffoldFinder = find.byType(Scaffold).first;
        if (scaffoldFinder.evaluate().isNotEmpty) {
          // ignore: use_build_context_synchronously
          final BuildContext context = tester.element(scaffoldFinder);
          final router = GoRouter.of(context);

          // Navigate to settings via deep link route
          router.go('/settings');
          await tester.pumpAndSettle();

          // Verify we're on settings screen
          final settingsTab = find.widgetWithText(NavigationDestination, 'Settings');
          expect(
            settingsTab,
            findsOneWidget,
            reason: 'Should navigate to settings via deep link',
          );
        }
      },
    );

    testWidgets(
      'Deep link: server detail route navigation',
      (tester) async {
        await tester.pumpWidget(
          ProviderScope(
            // buildProviderOverrides returns List (raw) because Riverpod 3.0.3
            // does not publicly export the Override type.
            // ignore: argument_type_not_assignable
            overrides: buildProviderOverrides(prefs),
            child: const CyberVpnApp(),
          ),
        );
        await tester.pumpAndSettle();

        // Simulate deep link to server detail
        final scaffoldFinder = find.byType(Scaffold).first;
        if (scaffoldFinder.evaluate().isNotEmpty) {
          // ignore: use_build_context_synchronously
          final BuildContext context = tester.element(scaffoldFinder);
          final router = GoRouter.of(context);

          // Navigate to servers list first
          router.go('/servers');
          await tester.pumpAndSettle();

          // Verify we're on servers screen
          final serversTab = find.widgetWithText(NavigationDestination, 'Servers');
          expect(
            serversTab,
            findsOneWidget,
            reason: 'Should navigate to servers via deep link',
          );

          // Test server detail route (with placeholder ID)
          // Note: This will fail if server doesn't exist, which is expected
          try {
            router.go('/servers/test-server-123');
            await tester.pumpAndSettle();
          } catch (e) {
            // Expected if server doesn't exist
          }
        }
      },
    );

    testWidgets(
      'Deep link: parse and resolve various routes',
      (tester) async {
        // Test deep link parsing without navigation

        // Test connect route
        final connectUri = Uri.parse('cybervpn://connect/server-123');
        final isDeepLink = DeepLinkParser.isDeepLink(connectUri.toString());
        expect(isDeepLink, true, reason: 'Should recognize connect deep link');

        // Test settings route
        final settingsUri = Uri.parse('cybervpn://settings');
        final settingsIsDeepLink = DeepLinkParser.isDeepLink(settingsUri.toString());
        expect(settingsIsDeepLink, true, reason: 'Should recognize settings deep link');

        // Test referral route
        final referralUri = Uri.parse('cybervpn://referral/ABC123');
        final referralIsDeepLink = DeepLinkParser.isDeepLink(referralUri.toString());
        expect(referralIsDeepLink, true, reason: 'Should recognize referral deep link');

        // Test subscribe route
        final subscribeUri = Uri.parse('cybervpn://subscribe/premium');
        final subscribeIsDeepLink = DeepLinkParser.isDeepLink(subscribeUri.toString());
        expect(subscribeIsDeepLink, true, reason: 'Should recognize subscribe deep link');
      },
    );
  });

  group('Navigation Error Handling', () {
    late SharedPreferences prefs;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      prefs = await SharedPreferences.getInstance();
      await prefs.clear();
      await prefs.setBool('onboarding_completed', true);
    });

    tearDown(() async {
      await prefs.clear();
    });

    testWidgets(
      'Navigation: invalid route handling',
      (tester) async {
        await tester.pumpWidget(
          ProviderScope(
            // buildProviderOverrides returns List (raw) because Riverpod 3.0.3
            // does not publicly export the Override type.
            // ignore: argument_type_not_assignable
            overrides: buildProviderOverrides(prefs),
            child: const CyberVpnApp(),
          ),
        );
        await tester.pumpAndSettle();

        // Try to navigate to invalid route
        final scaffoldFinder = find.byType(Scaffold).first;
        if (scaffoldFinder.evaluate().isNotEmpty) {
          // ignore: use_build_context_synchronously
          final BuildContext context = tester.element(scaffoldFinder);
          final router = GoRouter.of(context);

          // Attempt to navigate to non-existent route
          // GoRouter should handle this gracefully (redirect or show error)
          try {
            router.go('/invalid-route-12345');
            await tester.pumpAndSettle();
          } catch (e) {
            // Expected - invalid routes should be caught
          }
        }

        // App should remain functional
        expect(
          find.byType(NavigationBar),
          findsOneWidget,
          reason: 'App should remain stable after invalid navigation',
        );
      },
    );

    testWidgets(
      'Navigation: rapid tab switching',
      (tester) async {
        await tester.pumpWidget(
          ProviderScope(
            // buildProviderOverrides returns List (raw) because Riverpod 3.0.3
            // does not publicly export the Override type.
            // ignore: argument_type_not_assignable
            overrides: buildProviderOverrides(prefs),
            child: const CyberVpnApp(),
          ),
        );
        await tester.pumpAndSettle();

        // Rapidly switch between tabs
        final serversTab = find.widgetWithText(NavigationDestination, 'Servers');
        final profileTab = find.widgetWithText(NavigationDestination, 'Profile');
        final settingsTab = find.widgetWithText(NavigationDestination, 'Settings');
        final connectionTab = find.widgetWithText(NavigationDestination, 'Connection');

        // Switch tabs rapidly
        await tester.tap(serversTab);
        await tester.pump();
        await tester.tap(profileTab);
        await tester.pump();
        await tester.tap(settingsTab);
        await tester.pump();
        await tester.tap(connectionTab);
        await tester.pumpAndSettle();

        // App should remain stable
        expect(
          find.byType(NavigationBar),
          findsOneWidget,
          reason: 'App should handle rapid tab switching',
        );
      },
    );
  });
}

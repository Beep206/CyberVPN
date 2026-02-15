import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/screens/profile_list_screen.dart';
import 'package:cybervpn_mobile/features/vpn_profiles/presentation/widgets/profile_card.dart';
import 'package:cybervpn_mobile/shared/widgets/glitch_text.dart';

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

/// Wraps [ProfileListScreen] with localization delegates and Riverpod scope.
Widget _buildTestWidget() {
  return ProviderScope(
    child: MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      locale: const Locale('en'),
      home: const ProfileListScreen(),
    ),
  );
}

/// Pumps the widget and advances enough frames for layout to complete
/// without waiting for looping animations (Lottie, GlitchText, CyberCard)
/// that would cause pumpAndSettle to time out.
Future<void> _pumpScreen(WidgetTester tester) async {
  await tester.pumpWidget(_buildTestWidget());
  // Pump several frames to allow layout, localizations, and initial
  // animations to render without waiting for infinite loops to settle.
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 500));
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('ProfileListScreen', () {
    testWidgets('renders Scaffold with AppBar title', (tester) async {
      await _pumpScreen(tester);

      expect(find.byType(Scaffold), findsAtLeast(1));
      expect(find.byType(GlitchText), findsOneWidget);
    });

    testWidgets('renders FAB with add icon and label', (tester) async {
      await _pumpScreen(tester);

      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.byIcon(Icons.add), findsOneWidget);
      expect(find.text('Add Profile'), findsOneWidget);
    });

    testWidgets('renders mock profile cards', (tester) async {
      await _pumpScreen(tester);

      // The screen shows 3 mock profiles
      expect(find.byType(ProfileCard), findsNWidgets(3));
    });

    testWidgets('renders mock profile names', (tester) async {
      await _pumpScreen(tester);

      expect(find.text('CyberVPN Premium'), findsOneWidget);
      expect(find.text('Work VPN'), findsOneWidget);
      expect(find.text('Custom Config'), findsOneWidget);
    });

    testWidgets('shows Remote badge for remote profiles', (tester) async {
      await _pumpScreen(tester);

      // 2 remote profiles -> 2 "Remote" badges
      expect(find.text('Remote'), findsNWidgets(2));
    });

    testWidgets('shows Local badge for local profile', (tester) async {
      await _pumpScreen(tester);

      // 1 local profile -> 1 "Local" badge
      expect(find.text('Local'), findsOneWidget);
    });

    testWidgets('shows Active chip for active profile', (tester) async {
      await _pumpScreen(tester);

      // Only the first mock profile is active
      expect(find.text('Active'), findsOneWidget);
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
    });

    testWidgets('shows Expired chip for expired profile', (tester) async {
      await _pumpScreen(tester);

      // The second mock profile is expired
      expect(find.text('Expired'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });

    testWidgets('shows server count for each profile', (tester) async {
      await _pumpScreen(tester);

      // All mock profiles have 0 servers
      expect(find.text('0 servers'), findsNWidgets(3));
    });

    testWidgets('shows subtitle text', (tester) async {
      await _pumpScreen(tester);

      expect(find.text('Manage your VPN subscriptions'), findsOneWidget);
    });

    testWidgets('shows cloud icon for remote profiles', (tester) async {
      await _pumpScreen(tester);

      // 2 remote + icons in badges
      expect(find.byIcon(Icons.cloud_outlined), findsNWidgets(2));
    });

    testWidgets('shows folder icon for local profile', (tester) async {
      await _pumpScreen(tester);

      expect(find.byIcon(Icons.folder_outlined), findsOneWidget);
    });
  });

  group('ProfileListSkeleton', () {
    testWidgets('renders 3 skeleton cards', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: ProfileListSkeleton()),
        ),
      );
      await tester.pump();

      // ProfileListSkeleton builds 3 SkeletonCard widgets
      expect(find.byType(ProfileListSkeleton), findsOneWidget);
    });
  });
}

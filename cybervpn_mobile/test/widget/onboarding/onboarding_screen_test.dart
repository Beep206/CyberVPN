import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/constants/onboarding_pages.dart';
import 'package:cybervpn_mobile/features/onboarding/domain/repositories/onboarding_repository.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/screens/onboarding_screen.dart';
import 'package:cybervpn_mobile/features/onboarding/presentation/widgets/page_indicator.dart';

// ---------------------------------------------------------------------------
// Mock
// ---------------------------------------------------------------------------

class MockOnboardingRepository extends Mock implements OnboardingRepository {}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

/// Default stub: onboarding not yet completed, returns 4 pages.
void stubOnboardingDefaults(MockOnboardingRepository mock) {
  when(() => mock.hasCompletedOnboarding()).thenAnswer((_) async => false);
  when(() => mock.getPages())
      .thenAnswer((_) async => getDefaultOnboardingPages());
  when(() => mock.completeOnboarding()).thenAnswer((_) async {});
}

/// Builds a testable widget tree with the [OnboardingScreen] at `/onboarding`,
/// with placeholder routes for `/login` so navigation assertions work.
Widget buildTestableOnboardingScreen({
  required MockOnboardingRepository mockRepo,
}) {
  final router = GoRouter(
    initialLocation: '/onboarding',
    routes: [
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const Scaffold(body: Text('Login Screen')),
      ),
    ],
  );

  return ProviderScope(
    overrides: [
      onboardingRepositoryProvider.overrideWithValue(mockRepo),
    ],
    child: MaterialApp.router(
      routerConfig: router,
      theme: ThemeData.light(useMaterial3: true),
    ),
  );
}

/// Suppresses [FlutterError]s caused by RenderFlex overflow in widget tests.
void ignoreOverflowErrors() {
  FlutterError.onError = (details) {
    final isOverflow = details.toString().contains('overflowed');
    if (!isOverflow) {
      FlutterError.dumpErrorToConsole(details);
      throw details.exception;
    }
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockOnboardingRepository mockRepo;

  setUp(() {
    mockRepo = MockOnboardingRepository();
    stubOnboardingDefaults(mockRepo);
  });

  group('OnboardingScreen', () {
    testWidgets('renders 4 pages and page indicator', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildTestableOnboardingScreen(mockRepo: mockRepo));
      await tester.pumpAndSettle();

      // Page indicator should be present.
      expect(find.byType(PageIndicator), findsOneWidget);

      // First page content should be visible.
      expect(find.text('Privacy Title'), findsOneWidget);
      expect(find.text('Privacy Description'), findsOneWidget);

      // Skip button visible on first page.
      expect(find.text('Skip'), findsOneWidget);
    });

    testWidgets('can swipe through all 4 pages', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildTestableOnboardingScreen(mockRepo: mockRepo));
      await tester.pumpAndSettle();

      // Page 1: Privacy
      expect(find.text('Privacy Title'), findsOneWidget);

      // Swipe to page 2: Connect
      await tester.drag(find.byType(PageView), const Offset(-400, 0));
      await tester.pumpAndSettle();
      expect(find.text('Connect Title'), findsOneWidget);

      // Swipe to page 3: Globe
      await tester.drag(find.byType(PageView), const Offset(-400, 0));
      await tester.pumpAndSettle();
      expect(find.text('Globe Title'), findsOneWidget);

      // Swipe to page 4: GetStarted
      await tester.drag(find.byType(PageView), const Offset(-400, 0));
      await tester.pumpAndSettle();
      expect(find.text('GetStarted Title'), findsOneWidget);
    });

    testWidgets('Skip button completes onboarding and navigates to login',
        (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildTestableOnboardingScreen(mockRepo: mockRepo));
      await tester.pumpAndSettle();

      await tester.tap(find.text('Skip'));
      await tester.pumpAndSettle();

      // Should have called completeOnboarding.
      verify(() => mockRepo.completeOnboarding()).called(1);

      // Should navigate to login screen.
      expect(find.text('Login Screen'), findsOneWidget);
    });

    testWidgets(
        'Get Started button visible on last page and navigates to login',
        (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildTestableOnboardingScreen(mockRepo: mockRepo));
      await tester.pumpAndSettle();

      // Get Started should not be visible on first page.
      expect(find.text('Get Started'), findsNothing);

      // Swipe to last page.
      for (var i = 0; i < 3; i++) {
        await tester.drag(find.byType(PageView), const Offset(-400, 0));
        await tester.pumpAndSettle();
      }

      // Get Started should now be visible.
      expect(find.text('Get Started'), findsOneWidget);

      // Skip should be hidden (opacity 0).
      // We verify by checking that Skip button is not tappable.
      // The button exists but is wrapped in IgnorePointer when on last page.

      await tester.tap(find.text('Get Started'));
      await tester.pumpAndSettle();

      // Should have called completeOnboarding.
      verify(() => mockRepo.completeOnboarding()).called(1);

      // Should navigate to login screen.
      expect(find.text('Login Screen'), findsOneWidget);
    });

    testWidgets('Skip button is hidden on last page', (tester) async {
      ignoreOverflowErrors();
      await tester.pumpWidget(buildTestableOnboardingScreen(mockRepo: mockRepo));
      await tester.pumpAndSettle();

      // Swipe to last page.
      for (var i = 0; i < 3; i++) {
        await tester.drag(find.byType(PageView), const Offset(-400, 0));
        await tester.pumpAndSettle();
      }

      // The Skip TextButton widget is still in the tree but wrapped in
      // IgnorePointer(ignoring: true) and AnimatedOpacity(opacity: 0.0).
      // Verify that tapping Skip on the last page does nothing.
      // The text still exists in the widget tree, but it is not interactive.
      // We can verify by checking IgnorePointer state.
      final ignorePointer = tester.widget<IgnorePointer>(
        find.ancestor(
          of: find.widgetWithText(TextButton, 'Skip'),
          matching: find.byType(IgnorePointer),
        ),
      );
      expect(ignorePointer.ignoring, isTrue);
    });
  });
}

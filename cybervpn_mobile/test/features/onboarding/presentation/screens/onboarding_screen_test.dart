import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:mocktail/mocktail.dart';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
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
  when(
    () => mock.getPages(),
  ).thenAnswer((_) async => getDefaultOnboardingPages());
  when(() => mock.completeOnboarding()).thenAnswer((_) async {});
}

/// Builds a testable widget tree with the [OnboardingScreen] at `/onboarding`,
/// with placeholder routes for `/permissions` so navigation assertions work.
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
        path: '/permissions',
        builder: (context, state) =>
            const Scaffold(body: Text('Permissions Screen')),
      ),
    ],
  );

  return ProviderScope(
    overrides: [onboardingRepositoryProvider.overrideWithValue(mockRepo)],
    child: MaterialApp.router(
      routerConfig: router,
      theme: ThemeData.light(useMaterial3: true),
      locale: const Locale('en'),
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
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

Future<void> pumpOnboardingScreen(WidgetTester tester, Widget widget) async {
  await tester.pumpWidget(widget);
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 500));
}

Future<void> settleOnboardingTransition(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 450));
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
      await pumpOnboardingScreen(
        tester,
        buildTestableOnboardingScreen(mockRepo: mockRepo),
      );

      // Page indicator should be present.
      expect(find.byType(PageIndicator), findsOneWidget);

      // First page content should be visible.
      expect(find.text('Your Privacy Matters'), findsOneWidget);
      expect(
        find.text(
          'Zero-log policy. We never track, store, or share your browsing data.',
        ),
        findsOneWidget,
      );

      // Skip button visible on first page.
      expect(find.text('Skip'), findsOneWidget);
    });

    testWidgets('can swipe through all 4 pages', (tester) async {
      ignoreOverflowErrors();
      await pumpOnboardingScreen(
        tester,
        buildTestableOnboardingScreen(mockRepo: mockRepo),
      );

      // Page 1: Privacy
      expect(find.text('Your Privacy Matters'), findsOneWidget);

      // Swipe to page 2: Connect
      await tester.drag(find.byType(PageView), const Offset(-800, 0));
      await settleOnboardingTransition(tester);
      expect(find.text('One Tap Connect'), findsOneWidget);

      // Swipe to page 3: Globe
      await tester.drag(find.byType(PageView), const Offset(-800, 0));
      await settleOnboardingTransition(tester);
      expect(find.text('Global Network'), findsOneWidget);

      // Swipe to page 4: GetStarted
      await tester.drag(find.byType(PageView), const Offset(-800, 0));
      await settleOnboardingTransition(tester);
      expect(find.text('Get Started'), findsOneWidget);
    });

    testWidgets(
      'Skip button completes onboarding and navigates to permissions',
      (tester) async {
        ignoreOverflowErrors();
        await pumpOnboardingScreen(
          tester,
          buildTestableOnboardingScreen(mockRepo: mockRepo),
        );

        await tester.tap(find.text('Skip'));
        await settleOnboardingTransition(tester);

        // Should have called completeOnboarding.
        verify(() => mockRepo.completeOnboarding()).called(1);

        // Should navigate to permissions screen.
        expect(find.text('Permissions Screen'), findsOneWidget);
      },
    );

    testWidgets(
      'Get Started button visible on last page and navigates to permissions',
      (tester) async {
        ignoreOverflowErrors();
        await pumpOnboardingScreen(
          tester,
          buildTestableOnboardingScreen(mockRepo: mockRepo),
        );

        // Get Started should not be visible on first page.
        expect(find.text('Get Started'), findsNothing);

        // Swipe to last page.
        for (var i = 0; i < 3; i++) {
          await tester.drag(find.byType(PageView), const Offset(-800, 0));
          await settleOnboardingTransition(tester);
        }

        // Get Started should now be visible.
        expect(find.text('Get Started'), findsOneWidget);

        // Skip should be hidden (opacity 0).
        // We verify by checking that Skip button is not tappable.
        // The button exists but is wrapped in IgnorePointer when on last page.

        await tester.tap(find.text('Get Started'));
        await settleOnboardingTransition(tester);

        // Should have called completeOnboarding.
        verify(() => mockRepo.completeOnboarding()).called(1);

        // Should navigate to permissions screen.
        expect(find.text('Permissions Screen'), findsOneWidget);
      },
    );

    testWidgets('Skip button is hidden on last page', (tester) async {
      ignoreOverflowErrors();
      await pumpOnboardingScreen(
        tester,
        buildTestableOnboardingScreen(mockRepo: mockRepo),
      );

      // Swipe to last page.
      for (var i = 0; i < 3; i++) {
        await tester.drag(find.byType(PageView), const Offset(-800, 0));
        await settleOnboardingTransition(tester);
      }

      // The Skip TextButton widget is still in the tree but wrapped in
      // IgnorePointer(ignoring: true) and AnimatedOpacity(opacity: 0.0).
      // Verify that tapping Skip on the last page does nothing.
      // The text still exists in the widget tree, but it is not interactive.
      // We can verify by checking IgnorePointer state.
      final ignorePointers = tester.widgetList<IgnorePointer>(
        find.ancestor(
          of: find.widgetWithText(TextButton, 'Skip'),
          matching: find.byType(IgnorePointer),
        ),
      );
      expect(ignorePointers.any((widget) => widget.ignoring), isTrue);
    });
  });
}

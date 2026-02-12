import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/trial_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockSubscriptionRepository extends Mock {}

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

Widget buildTestableTrialCard({
  Map<String, dynamic>? trialStatusData,
  bool shouldSucceed = true,
}) {
  final mockRepo = MockSubscriptionRepository();

  if (shouldSucceed && trialStatusData != null) {
    when(mockRepo.getTrialStatus)
        .thenAnswer((_) async => Success(data: trialStatusData));
  } else if (!shouldSucceed) {
    when(mockRepo.getTrialStatus).thenAnswer(
      (_) async => Failure(failure: Exception('Failed to load trial status')),
    );
  }

  when(mockRepo.activateTrial).thenAnswer(
    (_) async => shouldSucceed
        ? const Success(data: {})
        : Failure(failure: Exception('Failed to activate trial')),
  );

  return ProviderScope(
    overrides: [
      subscriptionRepositoryProvider.overrideWithValue(mockRepo),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(
        body: TrialCard(),
      ),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('TrialCard - Eligible State', () {
    testWidgets('test_shows_trial_card_when_eligible', (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': true,
            'days_remaining': null,
            'trial_used': false,
          },
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('7-Day Free Trial'), findsOneWidget);
      expect(find.text('Start Trial'), findsOneWidget);
    });

    testWidgets('test_shows_start_trial_button', (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': true,
            'days_remaining': null,
            'trial_used': false,
          },
        ),
      );
      await tester.pumpAndSettle();

      expect(find.widgetWithText(ElevatedButton, 'Start Trial'), findsOneWidget);
    });
  });

  group('TrialCard - Active Trial State', () {
    testWidgets('test_shows_days_remaining_when_trial_active', (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': false,
            'days_remaining': 5,
            'trial_used': false,
          },
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('5 days remaining'), findsOneWidget);
    });

    testWidgets('test_shows_trial_active_badge', (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': false,
            'days_remaining': 3,
            'trial_used': false,
          },
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Trial Active'), findsOneWidget);
    });

    testWidgets('test_does_not_show_start_button_when_active', (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': false,
            'days_remaining': 7,
            'trial_used': false,
          },
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Start Trial'), findsNothing);
    });
  });

  group('TrialCard - Trial Used State', () {
    testWidgets('test_hides_card_when_trial_already_used', (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': false,
            'days_remaining': null,
            'trial_used': true,
          },
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(TrialCard), findsNothing);
    });
  });

  group('TrialCard - Activation Flow', () {
    testWidgets('test_shows_loading_indicator_during_activation',
        (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': true,
            'days_remaining': null,
            'trial_used': false,
          },
        ),
      );
      await tester.pumpAndSettle();

      final startButton = find.text('Start Trial');
      await tester.tap(startButton);
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('test_shows_success_snackbar_on_activation', (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': true,
            'days_remaining': null,
            'trial_used': false,
          },
        ),
      );
      await tester.pumpAndSettle();

      final startButton = find.text('Start Trial');
      await tester.tap(startButton);
      await tester.pumpAndSettle();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Trial activated successfully'), findsOneWidget);
    });

    testWidgets('test_shows_error_snackbar_on_activation_failure',
        (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': true,
            'days_remaining': null,
            'trial_used': false,
          },
          shouldSucceed: false,
        ),
      );
      await tester.pumpAndSettle();

      final startButton = find.text('Start Trial');
      await tester.tap(startButton);
      await tester.pumpAndSettle();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Failed to activate trial'), findsOneWidget);
    });
  });

  group('TrialCard - Loading State', () {
    testWidgets('test_shows_loading_indicator_initially', (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': true,
            'days_remaining': null,
            'trial_used': false,
          },
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('TrialCard - Error State', () {
    testWidgets('test_shows_error_message_on_fetch_failure', (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(shouldSucceed: false),
      );
      await tester.pumpAndSettle();

      expect(find.text('Failed to load trial status'), findsOneWidget);
    });
  });
}

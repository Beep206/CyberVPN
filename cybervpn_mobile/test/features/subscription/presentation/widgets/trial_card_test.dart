import 'dart:async';

import 'package:cybervpn_mobile/core/errors/failures.dart' as failures;
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/features/subscription/domain/entities/subscription_entity.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/trial_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../../../helpers/mock_repositories.dart';

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

Widget buildTestableTrialCard({
  Map<String, dynamic>? trialStatusData,
  bool fetchShouldSucceed = true,
  bool activationShouldSucceed = true,
  Completer<Result<Map<String, dynamic>>>? trialStatusCompleter,
  Completer<Result<SubscriptionEntity>>? activationCompleter,
}) {
  final mockRepo = MockSubscriptionRepository();

  if (trialStatusCompleter != null) {
    when(
      mockRepo.getTrialStatus,
    ).thenAnswer((_) => trialStatusCompleter.future);
  } else if (fetchShouldSucceed && trialStatusData != null) {
    when(
      mockRepo.getTrialStatus,
    ).thenAnswer((_) async => Success<Map<String, dynamic>>(trialStatusData));
  } else if (!fetchShouldSucceed) {
    when(mockRepo.getTrialStatus).thenAnswer(
      (_) async => const Failure<Map<String, dynamic>>(
        failures.ServerFailure(message: 'Failed to load trial status'),
      ),
    );
  }

  when(mockRepo.activateTrial).thenAnswer(
    (_) =>
        activationCompleter?.future ??
        Future.value(
          activationShouldSucceed
              ? Success<SubscriptionEntity>(
                  SubscriptionEntity(
                    id: 'trial-sub',
                    planId: 'trial-plan',
                    userId: 'user-1',
                    status: SubscriptionStatus.trial,
                    startDate: DateTime.now(),
                    endDate: DateTime.now().add(const Duration(days: 7)),
                    trafficUsedBytes: 0,
                    trafficLimitBytes: 100 * 1024 * 1024 * 1024,
                    maxDevices: 5,
                  ),
                )
              : const Failure<SubscriptionEntity>(
                  failures.ServerFailure(message: 'Failed to activate trial'),
                ),
        ),
  );

  return ProviderScope(
    overrides: [subscriptionRepositoryProvider.overrideWithValue(mockRepo)],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(body: TrialCard()),
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

      expect(find.widgetWithText(FilledButton, 'Start Trial'), findsOneWidget);
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

      expect(find.byKey(const Key('trial_card_eligible')), findsNothing);
      expect(find.byKey(const Key('trial_card_active')), findsNothing);
    });
  });

  group('TrialCard - Activation Flow', () {
    testWidgets('test_shows_loading_indicator_during_activation', (
      tester,
    ) async {
      final activationCompleter = Completer<Result<SubscriptionEntity>>();
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': true,
            'days_remaining': null,
            'trial_used': false,
          },
          activationCompleter: activationCompleter,
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
      expect(find.text('Trial activated successfully!'), findsOneWidget);
    });

    testWidgets('test_shows_error_snackbar_on_activation_failure', (
      tester,
    ) async {
      await tester.pumpWidget(
        buildTestableTrialCard(
          trialStatusData: {
            'is_eligible': true,
            'days_remaining': null,
            'trial_used': false,
          },
          activationShouldSucceed: false,
        ),
      );
      await tester.pumpAndSettle();

      final startButton = find.text('Start Trial');
      await tester.tap(startButton);
      await tester.pumpAndSettle();

      expect(find.byType(SnackBar), findsNothing);
      expect(find.text('Failed to activate trial'), findsOneWidget);
    });
  });

  group('TrialCard - Loading State', () {
    testWidgets('test_hides_nonessential_card_while_loading', (tester) async {
      final trialStatusCompleter = Completer<Result<Map<String, dynamic>>>();
      await tester.pumpWidget(
        buildTestableTrialCard(trialStatusCompleter: trialStatusCompleter),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsNothing);
      expect(find.byKey(const Key('trial_card_eligible')), findsNothing);
    });
  });

  group('TrialCard - Error State', () {
    testWidgets('test_hides_card_on_fetch_failure', (tester) async {
      await tester.pumpWidget(
        buildTestableTrialCard(fetchShouldSucceed: false),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('trial_card_eligible')), findsNothing);
      expect(find.byKey(const Key('trial_card_active')), findsNothing);
    });
  });
}

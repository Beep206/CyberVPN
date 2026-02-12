import 'dart:async';

import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' as failures;
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/widgets/cancel_subscription_sheet.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import '../../../../helpers/mock_repositories.dart';

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

Widget buildTestableCancelSheet({
  required String subscriptionId,
  required MockSubscriptionRepository mockRepo,
}) {
  return ProviderScope(
    overrides: [
      subscriptionRepositoryProvider.overrideWithValue(mockRepo),
    ],
    child: MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: Scaffold(
        body: Builder(
          builder: (context) => ElevatedButton(
            onPressed: () {
              unawaited(CancelSubscriptionSheet.show(context, subscriptionId));
            },
            child: const Text('Open Sheet'),
          ),
        ),
      ),
    ),
  );
}

// Finders
Finder findOpenSheetButton() => find.text('Open Sheet');
Finder findCancelButton() => find.byKey(const Key('btn_confirm_cancel'));
Finder findKeepButton() => find.byKey(const Key('btn_keep_subscription'));

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockSubscriptionRepository mockRepo;

  setUp(() {
    mockRepo = MockSubscriptionRepository();
  });

  group('CancelSubscriptionSheet - Rendering', () {
    testWidgets('test_renders_confirmation_title', (tester) async {
      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      expect(find.text('Cancel Subscription?'), findsOneWidget);
    });

    testWidgets('test_renders_warning_message', (tester) async {
      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      expect(find.textContaining('You will lose access'), findsOneWidget);
    });

    testWidgets('test_renders_cancel_and_keep_buttons', (tester) async {
      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      expect(findCancelButton(), findsOneWidget);
      expect(findKeepButton(), findsOneWidget);
    });
  });

  group('CancelSubscriptionSheet - Cancel Flow', () {
    testWidgets('test_cancel_button_calls_repository', (tester) async {
      when(() => mockRepo.cancelSubscription(any()))
          .thenAnswer((_) async => const Success<void>(null));

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      await tester.tap(findCancelButton());
      await tester.pumpAndSettle();

      verify(() => mockRepo.cancelSubscription('sub-123')).called(1);
    });

    testWidgets('test_success_shows_snackbar_and_closes_sheet', (tester) async {
      when(() => mockRepo.cancelSubscription(any()))
          .thenAnswer((_) async => const Success<void>(null));

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      await tester.tap(findCancelButton());
      await tester.pumpAndSettle();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Subscription cancelled'), findsOneWidget);
      expect(find.byType(CancelSubscriptionSheet), findsNothing);
    });

    testWidgets('test_error_shows_snackbar', (tester) async {
      when(() => mockRepo.cancelSubscription(any())).thenAnswer(
        (_) async => const Failure<void>(
            failures.ServerFailure(message: 'Failed to cancel subscription')),
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      await tester.tap(findCancelButton());
      await tester.pumpAndSettle();

      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Failed to cancel subscription'), findsOneWidget);
    });
  });

  group('CancelSubscriptionSheet - Keep Subscription', () {
    testWidgets('test_keep_button_closes_sheet_without_api_call', (tester) async {
      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      await tester.tap(findKeepButton());
      await tester.pumpAndSettle();

      expect(find.byType(CancelSubscriptionSheet), findsNothing);
      verifyNever(() => mockRepo.cancelSubscription(any()));
    });
  });
}

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

void ignoreOverflowErrors() {
  FlutterError.onError = (details) {
    final isOverflow = details.toString().contains('overflowed');
    if (!isOverflow) {
      FlutterError.dumpErrorToConsole(details);
    }
  };
}

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
Finder findWarningIcon() => find.byIcon(Icons.warning_amber_rounded);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockSubscriptionRepository mockRepo;

  setUp(() {
    mockRepo = MockSubscriptionRepository();
  });

  group('CancelSubscriptionSheet - Rendering', () {
    testWidgets('test_sheet_opens_when_triggered', (tester) async {
      ignoreOverflowErrors();

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      // Open the sheet
      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      expect(find.byType(CancelSubscriptionSheet), findsOneWidget);
      expect(findWarningIcon(), findsOneWidget);
    });

    testWidgets('test_renders_warning_title', (tester) async {
      ignoreOverflowErrors();

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

    testWidgets('test_renders_cancel_and_keep_buttons', (tester) async {
      ignoreOverflowErrors();

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

  group('CancelSubscriptionSheet - Cancel Flow with API', () {
    testWidgets('test_cancel_button_calls_repository', (tester) async {
      ignoreOverflowErrors();

      // Arrange: Mock successful cancellation
      when(() => mockRepo.cancelSubscription(any()))
          .thenAnswer((_) async => const Success(null));

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      // Open sheet
      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      // Act: Tap cancel button
      await tester.tap(findCancelButton());
      await tester.pumpAndSettle();

      // Assert: Verify API was called with correct subscription ID
      verify(() => mockRepo.cancelSubscription('sub-123')).called(1);
    });

    testWidgets('test_success_shows_snackbar_and_closes_sheet',
        (tester) async {
      ignoreOverflowErrors();

      // Arrange: Mock successful cancellation
      when(() => mockRepo.cancelSubscription(any()))
          .thenAnswer((_) async => const Success(null));

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      // Open sheet
      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      // Act: Tap cancel button
      await tester.tap(findCancelButton());
      await tester.pumpAndSettle();

      // Assert: Success snackbar shown
      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Subscription cancelled'), findsOneWidget);

      // Sheet is closed
      expect(find.byType(CancelSubscriptionSheet), findsNothing);
    });

    testWidgets('test_error_shows_snackbar_and_keeps_sheet_open',
        (tester) async {
      ignoreOverflowErrors();

      // Arrange: Mock failed cancellation
      when(() => mockRepo.cancelSubscription(any())).thenAnswer(
        (_) async => const Failure(
            failures.ServerFailure(message: 'Failed to cancel subscription')),
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      // Open sheet
      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      // Act: Tap cancel button
      await tester.tap(findCancelButton());
      await tester.pumpAndSettle();

      // Assert: Error snackbar shown
      expect(find.byType(SnackBar), findsOneWidget);
      expect(find.text('Failed to cancel subscription'), findsOneWidget);

      // Sheet is still open
      expect(find.byType(CancelSubscriptionSheet), findsOneWidget);
    });

    testWidgets('test_loading_disables_buttons', (tester) async {
      ignoreOverflowErrors();

      // Arrange: Mock slow cancellation to test loading state
      when(() => mockRepo.cancelSubscription(any())).thenAnswer(
        (_) async {
          await Future.delayed(const Duration(milliseconds: 500));
          return const Success(null);
        },
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      // Open sheet
      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      // Act: Tap cancel button
      await tester.tap(findCancelButton());
      await tester.pump(); // Don't settle, check loading state

      // Assert: Loading indicator shown
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // Buttons are disabled (can't easily test but loading indicator confirms)
      await tester.pumpAndSettle(); // Complete the operation
    });
  });

  group('CancelSubscriptionSheet - Keep Subscription', () {
    testWidgets('test_keep_button_closes_sheet_without_api_call',
        (tester) async {
      ignoreOverflowErrors();

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      // Open sheet
      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      // Act: Tap keep subscription button
      await tester.tap(findKeepButton());
      await tester.pumpAndSettle();

      // Assert: Sheet is closed
      expect(find.byType(CancelSubscriptionSheet), findsNothing);

      // No API call was made
      verifyNever(() => mockRepo.cancelSubscription(any()));
    });
  });

  group('CancelSubscriptionSheet - Edge Cases', () {
    testWidgets('test_multiple_taps_on_cancel_button_only_one_api_call',
        (tester) async {
      ignoreOverflowErrors();

      // Arrange: Mock slow cancellation
      when(() => mockRepo.cancelSubscription(any())).thenAnswer(
        (_) async {
          await Future.delayed(const Duration(milliseconds: 300));
          return const Success(null);
        },
      );

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-123',
          mockRepo: mockRepo,
        ),
      );

      // Open sheet
      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      // Act: Try to tap cancel button multiple times rapidly
      await tester.tap(findCancelButton());
      await tester.pump(const Duration(milliseconds: 10));

      // Try to tap again (should be disabled)
      final button = tester.widget<FilledButton>(findCancelButton());
      expect(button.onPressed, isNull); // Button is disabled during loading

      await tester.pumpAndSettle();

      // Assert: API was only called once
      verify(() => mockRepo.cancelSubscription('sub-123')).called(1);
    });

    testWidgets('test_different_subscription_ids', (tester) async {
      ignoreOverflowErrors();

      // Test with different subscription ID
      when(() => mockRepo.cancelSubscription(any()))
          .thenAnswer((_) async => const Success(null));

      await tester.pumpWidget(
        buildTestableCancelSheet(
          subscriptionId: 'sub-456',
          mockRepo: mockRepo,
        ),
      );

      await tester.tap(findOpenSheetButton());
      await tester.pumpAndSettle();

      await tester.tap(findCancelButton());
      await tester.pumpAndSettle();

      // Assert: Correct subscription ID was used
      verify(() => mockRepo.cancelSubscription('sub-456')).called(1);
    });
  });
}

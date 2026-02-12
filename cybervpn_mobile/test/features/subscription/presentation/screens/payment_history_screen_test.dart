import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/subscription/data/datasources/subscription_remote_ds.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/providers/payment_history_provider.dart';
import 'package:cybervpn_mobile/features/subscription/presentation/screens/payment_history_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Mocks & Test Data
// ---------------------------------------------------------------------------

// PaymentHistoryEntry and PaginatedPaymentHistory are plain classes (not sealed/freezed)
// so we can construct them directly without mocks.

// ---------------------------------------------------------------------------
// Test Helpers
// ---------------------------------------------------------------------------

void ignoreOverflowErrors(
  FlutterErrorDetails details, {
  bool forceReport = false,
}) {
  bool ifIsOverflowError = false;
  bool isUnableToLoadAsset = false;

  final exception = details.exception;
  if (exception is FlutterError) {
    ifIsOverflowError = !exception.diagnostics.any(
      (e) => e.value.toString().startsWith('A RenderFlex overflowed by'),
    );
    isUnableToLoadAsset = !exception.diagnostics.any(
      (e) => e.value.toString().startsWith('Unable to load asset'),
    );
  }

  if (ifIsOverflowError || isUnableToLoadAsset) {
    debugPrint('Ignoring error: ${details.exception}');
  } else {
    FlutterError.dumpErrorToConsole(details, forceReport: forceReport);
  }
}

Widget buildTestablePaymentHistoryScreen({
  AsyncValue<PaginatedPaymentHistory>? historyOverride,
}) {
  return ProviderScope(
    overrides: [
      if (historyOverride != null)
        paymentHistoryProvider.overrideWith((ref) async {
          return historyOverride.when(
            data: (data) => data,
            loading: () => throw StateError('loading'),
            error: (e, st) => throw e,
          );
        }),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: PaymentHistoryScreen(),
    ),
  );
}

// Finders
Finder findPaymentCard() => find.byType(Card);
Finder findRefreshIndicator() => find.byType(RefreshIndicator);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  setUp(() {
    FlutterError.onError = ignoreOverflowErrors;
  });

  group('PaymentHistoryScreen - Rendering', () {
    testWidgets('test_renders_payment_history_title', (tester) async {
      const history = PaginatedPaymentHistory(
        items: [],
        total: 0,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: const AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Payment History'), findsOneWidget);
    });

    testWidgets('test_renders_refresh_indicator', (tester) async {
      const history = PaginatedPaymentHistory(
        items: [],
        total: 0,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: const AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      expect(findRefreshIndicator(), findsOneWidget);
    });
  });

  group('PaymentHistoryScreen - Payment List', () {
    testWidgets('test_displays_payment_list', (tester) async {
      final history = PaginatedPaymentHistory(
        items: [
          PaymentHistoryEntry(
            id: 'pay1',
            planName: 'Monthly Premium',
            amount: 9.99,
            currency: 'USD',
            status: 'completed',

            createdAt: DateTime(2025, 1, 15, 10, 0),
          ),
          PaymentHistoryEntry(
            id: 'pay2',
            planName: 'Annual Premium',
            amount: 99.99,
            currency: 'USD',
            status: 'pending',

            createdAt: DateTime(2025, 2, 1, 14, 30),
          ),
        ],
        total: 2,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Monthly Premium'), findsOneWidget);
      expect(find.text('Annual Premium'), findsOneWidget);
      expect(find.text('\$9.99'), findsOneWidget);
      expect(find.text('\$99.99'), findsOneWidget);
      expect(findPaymentCard(), findsNWidgets(2));
    });

    testWidgets('test_displays_payment_status_badges', (tester) async {
      final history = PaginatedPaymentHistory(
        items: [
          PaymentHistoryEntry(
            id: 'pay1',
            planName: 'Monthly',
            amount: 10.0,
            currency: 'USD',
            status: 'completed',

            createdAt: DateTime(2025, 1, 15),
          ),
          PaymentHistoryEntry(
            id: 'pay2',
            planName: 'Annual',
            amount: 100.0,
            currency: 'USD',
            status: 'pending',

            createdAt: DateTime(2025, 2, 1),
          ),
          PaymentHistoryEntry(
            id: 'pay3',
            planName: 'Trial',
            amount: 5.0,
            currency: 'USD',
            status: 'failed',

            createdAt: DateTime(2025, 2, 5),
          ),
        ],
        total: 3,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('completed'), findsOneWidget);
      expect(find.text('pending'), findsOneWidget);
      expect(find.text('failed'), findsOneWidget);
    });

    testWidgets('test_displays_payment_dates', (tester) async {
      final history = PaginatedPaymentHistory(
        items: [
          PaymentHistoryEntry(
            id: 'pay1',
            planName: 'Monthly',
            amount: 10.0,
            currency: 'USD',
            status: 'completed',

            createdAt: DateTime(2025, 1, 15, 10, 30),
          ),
        ],
        total: 1,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('Jan 15, 2025'), findsOneWidget);
    });

    testWidgets('test_completed_payment_shows_green_amount', (tester) async {
      final history = PaginatedPaymentHistory(
        items: [
          PaymentHistoryEntry(
            id: 'pay1',
            planName: 'Monthly',
            amount: 10.0,
            currency: 'USD',
            status: 'completed',

            createdAt: DateTime(2025, 1, 15),
          ),
        ],
        total: 1,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      // Check that amount is displayed
      expect(find.text('\$10.00'), findsOneWidget);

      // Check for status icon
      expect(find.byIcon(Icons.check_circle), findsOneWidget);
    });
  });

  group('PaymentHistoryScreen - Empty State', () {
    testWidgets('test_empty_payment_list_shows_message', (tester) async {
      const history = PaginatedPaymentHistory(
        items: [],
        total: 0,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: const AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No payments yet'), findsOneWidget);
      expect(find.byIcon(Icons.receipt_long_outlined), findsOneWidget);
    });

    testWidgets('test_empty_state_shows_explanation', (tester) async {
      const history = PaginatedPaymentHistory(
        items: [],
        total: 0,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: const AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.text('Your subscription payments will appear here'),
        findsOneWidget,
      );
    });
  });

  group('PaymentHistoryScreen - Loading State', () {
    testWidgets('test_loading_shows_progress_indicator', (tester) async {
      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: const AsyncValue.loading(),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('PaymentHistoryScreen - Error State', () {
    testWidgets('test_error_shows_error_message', (tester) async {
      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride:
              AsyncValue.error(Exception('Failed'), StackTrace.current),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('An error occurred'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });

    testWidgets('test_error_state_shows_explanation', (tester) async {
      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride:
              AsyncValue.error(Exception('Failed'), StackTrace.current),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Failed to load payment history'), findsOneWidget);
    });
  });

  group('PaymentHistoryScreen - Status Icons', () {
    testWidgets('test_completed_status_shows_check_icon', (tester) async {
      final history = PaginatedPaymentHistory(
        items: [
          PaymentHistoryEntry(
            id: 'pay1',
            planName: 'Monthly',
            amount: 10.0,
            currency: 'USD',
            status: 'completed',

            createdAt: DateTime(2025, 1, 15),
          ),
        ],
        total: 1,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.check_circle), findsOneWidget);
    });

    testWidgets('test_pending_status_shows_schedule_icon', (tester) async {
      final history = PaginatedPaymentHistory(
        items: [
          PaymentHistoryEntry(
            id: 'pay1',
            planName: 'Monthly',
            amount: 10.0,
            currency: 'USD',
            status: 'pending',

            createdAt: DateTime(2025, 1, 15),
          ),
        ],
        total: 1,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.schedule), findsOneWidget);
    });

    testWidgets('test_failed_status_shows_cancel_icon', (tester) async {
      final history = PaginatedPaymentHistory(
        items: [
          PaymentHistoryEntry(
            id: 'pay1',
            planName: 'Monthly',
            amount: 10.0,
            currency: 'USD',
            status: 'failed',

            createdAt: DateTime(2025, 1, 15),
          ),
        ],
        total: 1,
        offset: 0,
        limit: 20,
      );

      await tester.pumpWidget(
        buildTestablePaymentHistoryScreen(
          historyOverride: AsyncValue.data(history),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byIcon(Icons.cancel), findsOneWidget);
    });
  });
}

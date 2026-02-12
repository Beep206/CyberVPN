import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/wallet/domain/entities/wallet.dart';
import 'package:cybervpn_mobile/features/wallet/presentation/providers/wallet_provider.dart';
import 'package:cybervpn_mobile/features/wallet/presentation/screens/wallet_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

// ---------------------------------------------------------------------------
// Mocks & Test Data
// ---------------------------------------------------------------------------

class MockWalletBalance extends WalletBalance {
  MockWalletBalance({
    required super.balance,
    required super.pendingBalance,
    required super.currency,
  });
}

class MockWalletTransaction extends WalletTransaction {
  MockWalletTransaction({
    required super.id,
    required super.amount,
    required super.currency,
    required super.description,
    required super.type,
    required super.status,
    required super.createdAt,
  });
}

class MockWalletTransactionList extends WalletTransactionList {
  MockWalletTransactionList({required super.transactions});
}

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

Widget buildTestableWalletScreen({
  bool walletAvailable = true,
  AsyncValue<WalletBalance>? balanceOverride,
  AsyncValue<WalletTransactionList>? transactionsOverride,
}) {
  return ProviderScope(
    overrides: [
      walletAvailabilityProvider.overrideWith((ref) async => walletAvailable),
      if (balanceOverride != null)
        walletBalanceProvider.overrideWith((ref) => balanceOverride),
      if (transactionsOverride != null)
        walletTransactionsProvider
            .overrideWith((ref) => transactionsOverride),
    ],
    child: const MaterialApp(
      localizationsDelegates: AppLocalizations.localizationsDelegates,
      supportedLocales: AppLocalizations.supportedLocales,
      home: WalletScreen(),
    ),
  );
}

// Finders
Finder findWithdrawButton() => find.widgetWithText(FilledButton, 'Withdraw');
Finder findBalanceCard() => find.byType(Card).first;
Finder findTransactionList() => find.byType(ListTile);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  setUp(() {
    FlutterError.onError = ignoreOverflowErrors;
  });

  group('WalletScreen - Rendering', () {
    testWidgets('test_renders_wallet_title', (tester) async {
      final balance = MockWalletBalance(
        balance: 100.0,
        pendingBalance: 0.0,
        currency: 'USD',
      );

      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Wallet'), findsOneWidget);
    });

    testWidgets('test_renders_balance_card', (tester) async {
      final balance = MockWalletBalance(
        balance: 250.50,
        pendingBalance: 10.0,
        currency: 'USD',
      );

      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Balance'), findsOneWidget);
      expect(find.text('250.50 USD'), findsOneWidget);
      expect(find.textContaining('Pending:'), findsOneWidget);
    });

    testWidgets('test_renders_withdraw_button', (tester) async {
      final balance = MockWalletBalance(
        balance: 100.0,
        pendingBalance: 0.0,
        currency: 'USD',
      );

      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      expect(findWithdrawButton(), findsOneWidget);
    });

    testWidgets('test_renders_transaction_history_header', (tester) async {
      final balance = MockWalletBalance(
        balance: 100.0,
        pendingBalance: 0.0,
        currency: 'USD',
      );

      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Transaction History'), findsOneWidget);
    });
  });

  group('WalletScreen - Wallet Unavailable', () {
    testWidgets('test_wallet_unavailable_shows_message', (tester) async {
      await tester.pumpWidget(
        buildTestableWalletScreen(walletAvailable: false),
      );
      await tester.pumpAndSettle();

      expect(find.text('Wallet Unavailable'), findsOneWidget);
      expect(find.byIcon(Icons.wallet_outlined), findsOneWidget);
    });

    testWidgets('test_wallet_unavailable_shows_explanation', (tester) async {
      await tester.pumpWidget(
        buildTestableWalletScreen(walletAvailable: false),
      );
      await tester.pumpAndSettle();

      expect(
        find.text('Wallet is not available for this account'),
        findsOneWidget,
      );
    });
  });

  group('WalletScreen - Balance Display', () {
    testWidgets('test_displays_zero_balance', (tester) async {
      final balance = MockWalletBalance(
        balance: 0.0,
        pendingBalance: 0.0,
        currency: 'USD',
      );

      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('0.00 USD'), findsOneWidget);
    });

    testWidgets('test_displays_pending_balance_when_greater_than_zero',
        (tester) async {
      final balance = MockWalletBalance(
        balance: 100.0,
        pendingBalance: 25.50,
        currency: 'USD',
      );

      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('Pending: 25.50 USD'), findsOneWidget);
    });

    testWidgets('test_loading_balance_shows_progress_indicator',
        (tester) async {
      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: const AsyncValue.loading(),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsWidgets);
    });

    testWidgets('test_balance_error_shows_error_message', (tester) async {
      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride:
              AsyncValue.error(Exception('Failed'), StackTrace.current),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Failed to load balance'), findsOneWidget);
    });
  });

  group('WalletScreen - Transaction List', () {
    testWidgets('test_displays_transaction_list', (tester) async {
      final balance = MockWalletBalance(
        balance: 100.0,
        pendingBalance: 0.0,
        currency: 'USD',
      );

      final transactions = MockWalletTransactionList(
        transactions: [
          MockWalletTransaction(
            id: 'tx1',
            amount: 50.0,
            currency: 'USD',
            description: 'Referral bonus',
            type: TransactionType.referral,
            status: TransactionStatus.completed,
            createdAt: DateTime(2025, 1, 15),
          ),
          MockWalletTransaction(
            id: 'tx2',
            amount: -25.0,
            currency: 'USD',
            description: 'Withdrawal',
            type: TransactionType.withdrawal,
            status: TransactionStatus.pending,
            createdAt: DateTime(2025, 2, 1),
          ),
        ],
      );

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Referral bonus'), findsOneWidget);
      expect(find.text('Withdrawal'), findsOneWidget);
      expect(findTransactionList(), findsNWidgets(2));
    });

    testWidgets('test_empty_transaction_list_shows_message', (tester) async {
      final balance = MockWalletBalance(
        balance: 100.0,
        pendingBalance: 0.0,
        currency: 'USD',
      );

      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('No transactions yet'), findsOneWidget);
    });

    testWidgets('test_transaction_list_loading_shows_progress_indicator',
        (tester) async {
      final balance = MockWalletBalance(
        balance: 100.0,
        pendingBalance: 0.0,
        currency: 'USD',
      );

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: const AsyncValue.loading(),
        ),
      );
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsWidgets);
    });

    testWidgets('test_transaction_list_error_shows_error_message',
        (tester) async {
      final balance = MockWalletBalance(
        balance: 100.0,
        pendingBalance: 0.0,
        currency: 'USD',
      );

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride:
              AsyncValue.error(Exception('Failed'), StackTrace.current),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Failed to load transactions'), findsOneWidget);
    });
  });

  group('WalletScreen - Withdraw Dialog', () {
    testWidgets('test_withdraw_button_opens_dialog', (tester) async {
      final balance = MockWalletBalance(
        balance: 100.0,
        pendingBalance: 0.0,
        currency: 'USD',
      );

      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findWithdrawButton());
      await tester.pumpAndSettle();

      expect(find.byType(AlertDialog), findsOneWidget);
      expect(find.text('Withdraw not implemented'), findsOneWidget);
    });

    testWidgets('test_withdraw_dialog_can_be_closed', (tester) async {
      final balance = MockWalletBalance(
        balance: 100.0,
        pendingBalance: 0.0,
        currency: 'USD',
      );

      final transactions = MockWalletTransactionList(transactions: []);

      await tester.pumpWidget(
        buildTestableWalletScreen(
          balanceOverride: AsyncValue.data(balance),
          transactionsOverride: AsyncValue.data(transactions),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(findWithdrawButton());
      await tester.pumpAndSettle();

      await tester.tap(find.text('Close'));
      await tester.pumpAndSettle();

      expect(find.byType(AlertDialog), findsNothing);
    });
  });
}

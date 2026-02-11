import 'package:freezed_annotation/freezed_annotation.dart';

part 'wallet.freezed.dart';

/// Type of wallet transaction.
enum TransactionType {
  /// Funds added to wallet (top-up, referral bonus, etc.).
  deposit,

  /// Funds withdrawn from wallet.
  withdrawal,

  /// Referral commission earned.
  referral,

  /// Promotional bonus or credit.
  bonus,

  /// Subscription payment deducted from wallet.
  subscription,
}

/// Status of a transaction.
enum TransactionStatus {
  /// Transaction is being processed.
  pending,

  /// Transaction completed successfully.
  completed,

  /// Transaction failed or was cancelled.
  failed,
}

/// Wallet balance information.
@freezed
sealed class WalletBalance with _$WalletBalance {
  const factory WalletBalance({
    /// Available balance in the wallet.
    required double balance,

    /// Currency code (e.g., "USD", "EUR").
    required String currency,

    /// Pending balance (e.g., from pending withdrawals).
    @Default(0.0) double pendingBalance,
  }) = _WalletBalance;
}

/// A single wallet transaction entry.
@freezed
sealed class WalletTransaction with _$WalletTransaction {
  const factory WalletTransaction({
    /// Unique transaction identifier.
    required String id,

    /// Type of transaction.
    required TransactionType type,

    /// Transaction amount (positive for deposits, negative for withdrawals).
    required double amount,

    /// Currency code (e.g., "USD").
    required String currency,

    /// Current status of the transaction.
    required TransactionStatus status,

    /// Transaction description or note.
    required String description,

    /// Date and time of the transaction.
    required DateTime createdAt,
  }) = _WalletTransaction;
}

/// Wallet transaction list with pagination info.
@freezed
sealed class WalletTransactionList with _$WalletTransactionList {
  const factory WalletTransactionList({
    /// List of transactions.
    required List<WalletTransaction> transactions,

    /// Total number of transactions (for pagination).
    required int total,
  }) = _WalletTransactionList;
}

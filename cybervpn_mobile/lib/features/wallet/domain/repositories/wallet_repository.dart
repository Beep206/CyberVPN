import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/wallet/domain/entities/wallet.dart';

/// Abstract repository for wallet feature operations.
///
/// Implementations must support graceful degradation via [isAvailable],
/// allowing the UI to conditionally render wallet features when the
/// backend does not yet support them.
///
/// All methods return [Result<T>] to provide type-safe error handling
/// without relying on exceptions for control flow.
abstract class WalletRepository {
  /// Checks whether the wallet feature is available on the backend.
  Future<Result<bool>> isAvailable();

  /// Retrieves the current user's wallet balance.
  ///
  /// Returns zero balance if the wallet feature is unavailable.
  Future<Result<WalletBalance>> getBalance({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  });

  /// Fetches wallet transaction history for the current user.
  ///
  /// [limit] controls the maximum number of transactions returned (default 20).
  /// [offset] is the starting point for pagination (default 0).
  /// [type] filters transactions by type (optional).
  ///
  /// Returns an empty list if the wallet feature is unavailable.
  /// Returns [Failure] if the backend returns an unexpected error.
  Future<Result<WalletTransactionList>> getTransactions({
    int limit = 20,
    int offset = 0,
    TransactionType? type,
  });

  /// Initiates a withdrawal request from the user's wallet.
  ///
  /// [amount] is the amount to withdraw.
  /// [method] is the withdrawal method (e.g., "bank_transfer", "crypto").
  /// [details] contains method-specific withdrawal details.
  ///
  /// Returns [Failure] if withdrawal is not supported or fails validation.
  Future<Result<String>> withdrawFunds({
    required double amount,
    required String method,
    required Map<String, dynamic> details,
  });
}

import 'package:cybervpn_mobile/core/constants/api_constants.dart';
import 'package:cybervpn_mobile/core/constants/cache_constants.dart';
import 'package:cybervpn_mobile/core/errors/exceptions.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/core/utils/app_logger.dart';
import 'package:cybervpn_mobile/features/wallet/domain/entities/wallet.dart';

/// Abstract data source for wallet-related API calls.
abstract class WalletRemoteDataSource {
  /// Checks whether the wallet feature is supported by the backend.
  ///
  /// Returns `true` on HTTP 200, `false` on 404/501 or any network error.
  Future<bool> checkAvailability();

  /// Fetches the current user's wallet balance.
  Future<WalletBalance> getBalance();

  /// Fetches wallet transaction history.
  Future<WalletTransactionList> getTransactions({
    int limit = 20,
    int offset = 0,
    TransactionType? type,
  });

  /// Initiates a withdrawal request.
  Future<String> withdraw({
    required double amount,
    required String method,
    required Map<String, dynamic> details,
  });
}

/// Implementation of [WalletRemoteDataSource] using [ApiClient].
///
/// Caches the availability check result in-memory for the session to avoid
/// repeated network calls to an endpoint that may not exist yet.
class WalletRemoteDataSourceImpl implements WalletRemoteDataSource {
  final ApiClient _apiClient;

  /// In-memory cached availability result.
  bool? _cachedAvailable;
  DateTime? _cachedAt;

  /// Duration to cache the availability result.
  static const _cacheDuration = CacheConstants.walletCacheTtl;

  WalletRemoteDataSourceImpl(this._apiClient);

  @override
  Future<bool> checkAvailability() async {
    // Return cached result if still valid.
    if (_cachedAvailable != null && _cachedAt != null) {
      final elapsed = DateTime.now().difference(_cachedAt!);
      if (elapsed < _cacheDuration) return _cachedAvailable!;
    }

    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiConstants.walletBalance,
      );
      final available = response.statusCode == 200;
      _setCachedAvailability(available);
      return available;
    } on ServerException catch (e) {
      // 404 or 501 means the feature is not available.
      if (e.code == 404 || e.code == 501) {
        _setCachedAvailability(false);
        return false;
      }
      AppLogger.warning(
        'Wallet availability check failed: ${e.message}',
        category: 'WalletRemoteDataSource',
      );
      _setCachedAvailability(false);
      return false;
    } on NetworkException {
      // Network errors -- fail gracefully.
      _setCachedAvailability(false);
      return false;
    } catch (e) {
      // Any unexpected error -- log and fail gracefully.
      AppLogger.error(
        'Unexpected error checking wallet availability: $e',
        category: 'WalletRemoteDataSource',
      );
      _setCachedAvailability(false);
      return false;
    }
  }

  void _setCachedAvailability(bool available) {
    _cachedAvailable = available;
    _cachedAt = DateTime.now();
  }

  @override
  Future<WalletBalance> getBalance() async {
    try {
      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiConstants.walletBalance,
      );

      final data = response.data;
      if (data == null) {
        throw const ServerException(
          message: 'Invalid response from wallet balance endpoint',
          code: 500,
        );
      }

      return WalletBalance(
        balance: (data['balance'] as num?)?.toDouble() ?? 0.0,
        currency: data['currency'] as String? ?? 'USD',
        pendingBalance: (data['pending_balance'] as num?)?.toDouble() ?? 0.0,
      );
    } catch (e) {
      AppLogger.error(
        'Failed to fetch wallet balance',
        error: e,
        category: 'WalletRemoteDataSource',
      );
      rethrow;
    }
  }

  @override
  Future<WalletTransactionList> getTransactions({
    int limit = 20,
    int offset = 0,
    TransactionType? type,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit.toString(),
        'offset': offset.toString(),
      };

      if (type != null) {
        queryParams['type'] = type.name;
      }

      final response = await _apiClient.get<Map<String, dynamic>>(
        ApiConstants.walletTransactions,
        queryParameters: queryParams,
      );

      final data = response.data;
      if (data == null) {
        throw const ServerException(
          message: 'Invalid response from wallet transactions endpoint',
          code: 500,
        );
      }

      final transactionsJson = data['transactions'] as List<dynamic>? ?? [];
      final transactions = transactionsJson.map((json) {
        final txMap = json as Map<String, dynamic>;
        return WalletTransaction(
          id: txMap['id'] as String,
          type: _parseTransactionType(txMap['type'] as String?),
          amount: (txMap['amount'] as num).toDouble(),
          currency: txMap['currency'] as String? ?? 'USD',
          status: _parseTransactionStatus(txMap['status'] as String?),
          description: txMap['description'] as String? ?? '',
          createdAt: DateTime.parse(txMap['created_at'] as String),
        );
      }).toList();

      return WalletTransactionList(
        transactions: transactions,
        total: data['total'] as int? ?? transactions.length,
      );
    } catch (e) {
      AppLogger.error(
        'Failed to fetch wallet transactions',
        error: e,
        category: 'WalletRemoteDataSource',
      );
      rethrow;
    }
  }

  @override
  Future<String> withdraw({
    required double amount,
    required String method,
    required Map<String, dynamic> details,
  }) async {
    try {
      final response = await _apiClient.post<Map<String, dynamic>>(
        ApiConstants.walletWithdraw,
        data: {
          'amount': amount,
          'method': method,
          'details': details,
        },
      );

      final data = response.data;
      if (data == null) {
        throw const ServerException(
          message: 'Invalid response from wallet withdraw endpoint',
          code: 500,
        );
      }

      return data['withdrawal_id'] as String? ?? '';
    } catch (e) {
      AppLogger.error(
        'Failed to initiate withdrawal',
        error: e,
        category: 'WalletRemoteDataSource',
      );
      rethrow;
    }
  }

  TransactionType _parseTransactionType(String? type) {
    switch (type?.toLowerCase()) {
      case 'deposit':
        return TransactionType.deposit;
      case 'withdrawal':
        return TransactionType.withdrawal;
      case 'referral':
        return TransactionType.referral;
      case 'bonus':
        return TransactionType.bonus;
      case 'subscription':
        return TransactionType.subscription;
      default:
        return TransactionType.deposit;
    }
  }

  TransactionStatus _parseTransactionStatus(String? status) {
    switch (status?.toLowerCase()) {
      case 'pending':
        return TransactionStatus.pending;
      case 'completed':
        return TransactionStatus.completed;
      case 'failed':
        return TransactionStatus.failed;
      default:
        return TransactionStatus.pending;
    }
  }
}

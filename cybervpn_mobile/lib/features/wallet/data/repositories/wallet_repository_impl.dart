import 'package:cybervpn_mobile/core/data/cache_strategy.dart';
import 'package:cybervpn_mobile/core/errors/failures.dart' hide Failure;
import 'package:cybervpn_mobile/core/types/result.dart';
import 'package:cybervpn_mobile/features/wallet/data/datasources/wallet_remote_ds.dart';
import 'package:cybervpn_mobile/features/wallet/domain/entities/wallet.dart';
import 'package:cybervpn_mobile/features/wallet/domain/repositories/wallet_repository.dart';

/// Implementation of [WalletRepository] using [WalletRemoteDataSource].
class WalletRepositoryImpl implements WalletRepository {
  final WalletRemoteDataSource _remoteDataSource;

  WalletRepositoryImpl(this._remoteDataSource);

  @override
  Future<Result<bool>> isAvailable() async {
    try {
      final available = await _remoteDataSource.checkAvailability();
      return Success(available);
    } catch (e) {
      return const Success(false);
    }
  }

  @override
  Future<Result<WalletBalance>> getBalance({
    CacheStrategy strategy = CacheStrategy.networkFirst,
  }) async {
    try {
      final balance = await _remoteDataSource.getBalance();
      return Success(balance);
    } catch (e) {
      return Failure(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<WalletTransactionList>> getTransactions({
    int limit = 20,
    int offset = 0,
    TransactionType? type,
  }) async {
    try {
      final transactions = await _remoteDataSource.getTransactions(
        limit: limit,
        offset: offset,
        type: type,
      );
      return Success(transactions);
    } catch (e) {
      return Failure(ServerFailure(message: e.toString()));
    }
  }

  @override
  Future<Result<String>> withdrawFunds({
    required double amount,
    required String method,
    required Map<String, dynamic> details,
  }) async {
    try {
      final withdrawalId = await _remoteDataSource.withdraw(
        amount: amount,
        method: method,
        details: details,
      );
      return Success(withdrawalId);
    } catch (e) {
      return Failure(ServerFailure(message: e.toString()));
    }
  }
}

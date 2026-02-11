import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cybervpn_mobile/core/di/providers.dart';
import 'package:cybervpn_mobile/core/network/api_client.dart';
import 'package:cybervpn_mobile/features/wallet/data/datasources/wallet_remote_ds.dart';
import 'package:cybervpn_mobile/features/wallet/data/repositories/wallet_repository_impl.dart';
import 'package:cybervpn_mobile/features/wallet/domain/entities/wallet.dart';
import 'package:cybervpn_mobile/features/wallet/domain/repositories/wallet_repository.dart';

// ── Repository providers ──────────────────────────────────────────────────

/// Provides the wallet remote data source.
final walletRemoteDataSourceProvider = Provider<WalletRemoteDataSource>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return WalletRemoteDataSourceImpl(apiClient);
});

/// Provides the wallet repository.
final walletRepositoryProvider = Provider<WalletRepository>((ref) {
  final remoteDataSource = ref.watch(walletRemoteDataSourceProvider);
  return WalletRepositoryImpl(remoteDataSource);
});

// ── Feature availability provider ─────────────────────────────────────────

/// Provides the availability status of the wallet feature.
final walletAvailabilityProvider = FutureProvider<bool>((ref) async {
  final repository = ref.watch(walletRepositoryProvider);
  final result = await repository.isAvailable();
  return result.dataOrNull ?? false;
});

// ── Wallet balance provider ───────────────────────────────────────────────

/// Provides the user's current wallet balance.
final walletBalanceProvider = FutureProvider.autoDispose<WalletBalance>((ref) async {
  final repository = ref.watch(walletRepositoryProvider);
  final result = await repository.getBalance();

  return result.dataOrNull ??
      const WalletBalance(balance: 0.0, currency: 'USD');
});

// ── Wallet transactions provider ──────────────────────────────────────────

/// Provides the user's wallet transaction history.
final walletTransactionsProvider =
    FutureProvider.autoDispose<WalletTransactionList>((ref) async {
  final repository = ref.watch(walletRepositoryProvider);
  final result = await repository.getTransactions(limit: 20);

  return result.dataOrNull ??
      const WalletTransactionList(transactions: [], total: 0);
});

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:cybervpn_mobile/app/theme/tokens.dart';
import 'package:cybervpn_mobile/core/l10n/generated/app_localizations.dart';
import 'package:cybervpn_mobile/features/wallet/domain/entities/wallet.dart';
import 'package:cybervpn_mobile/features/wallet/presentation/providers/wallet_provider.dart';
import 'package:cybervpn_mobile/features/wallet/presentation/widgets/withdraw_bottom_sheet.dart';

/// Wallet screen displaying balance, transaction history, and withdraw button.
///
/// Features graceful degradation if the wallet feature is not available
/// on the backend.
class WalletScreen extends ConsumerWidget {
  const WalletScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);

    final walletAvailable = ref.watch(walletAvailabilityProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.wallet),
      ),
      body: walletAvailable.when(
        data: (available) {
          if (!available) {
            return _buildUnavailableState(context, l10n);
          }
          return _buildWalletContent(context, ref, l10n, theme);
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (_, __) => _buildUnavailableState(context, l10n),
      ),
    );
  }

  Widget _buildUnavailableState(BuildContext context, AppLocalizations l10n) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(Spacing.xl),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.wallet_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: Spacing.lg),
            Text(
              l10n.walletUnavailable,
              style: Theme.of(context).textTheme.headlineSmall,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: Spacing.sm),
            Text(
              l10n.walletUnavailableMessage,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildWalletContent(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations l10n,
    ThemeData theme,
  ) {
    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(walletBalanceProvider);
        ref.invalidate(walletTransactionsProvider);
      },
      child: CustomScrollView(
        slivers: [
          // Balance Card
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(Spacing.md),
              child: _buildBalanceCard(ref, l10n, theme),
            ),
          ),

          // Withdraw Button
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
              child: FilledButton.icon(
                onPressed: () => _showWithdrawDialog(context, ref, l10n),
                icon: const Icon(Icons.arrow_upward),
                label: Text(l10n.walletWithdraw),
              ),
            ),
          ),

          // Transaction List Header
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.all(Spacing.md),
              child: Text(
                l10n.walletTransactionHistory,
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),

          // Transaction List
          _buildTransactionList(ref, l10n, theme),
        ],
      ),
    );
  }

  Widget _buildBalanceCard(
    WidgetRef ref,
    AppLocalizations l10n,
    ThemeData theme,
  ) {
    final balanceAsync = ref.watch(walletBalanceProvider);

    return balanceAsync.when(
      data: (balance) => Card(
        child: Padding(
          padding: const EdgeInsets.all(Spacing.lg),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                l10n.walletBalance,
                style: theme.textTheme.titleMedium?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: Spacing.sm),
              Text(
                '${balance.balance.toStringAsFixed(2)} ${balance.currency}',
                style: theme.textTheme.displaySmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: theme.colorScheme.primary,
                ),
              ),
              if (balance.pendingBalance > 0) ...[
                const SizedBox(height: Spacing.xs),
                Text(
                  '${l10n.walletPending}: ${balance.pendingBalance.toStringAsFixed(2)} ${balance.currency}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
      loading: () => const Card(
        child: Padding(
          padding: EdgeInsets.all(Spacing.lg),
          child: Center(child: CircularProgressIndicator()),
        ),
      ),
      error: (e, _) => Card(
        child: Padding(
          padding: const EdgeInsets.all(Spacing.lg),
          child: Text(l10n.errorLoadingBalance),
        ),
      ),
    );
  }

  Widget _buildTransactionList(
    WidgetRef ref,
    AppLocalizations l10n,
    ThemeData theme,
  ) {
    final transactionsAsync = ref.watch(walletTransactionsProvider);

    return transactionsAsync.when(
      data: (transactionList) {
        if (transactionList.transactions.isEmpty) {
          return SliverFillRemaining(
            child: Center(
              child: Text(
                l10n.walletNoTransactions,
                style: theme.textTheme.bodyLarge?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          );
        }

        return SliverList(
          delegate: SliverChildBuilderDelegate(
            (context, index) {
              final transaction = transactionList.transactions[index];
              return _buildTransactionTile(transaction, l10n, theme);
            },
            childCount: transactionList.transactions.length,
          ),
        );
      },
      loading: () => const SliverFillRemaining(
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => SliverFillRemaining(
        child: Center(child: Text(l10n.errorLoadingTransactions)),
      ),
    );
  }

  Widget _buildTransactionTile(
    WalletTransaction transaction,
    AppLocalizations l10n,
    ThemeData theme,
  ) {
    final isPositive = transaction.amount > 0;
    final icon = _getTransactionIcon(transaction.type);
    final color = _getTransactionColor(transaction.type, theme);

    return ListTile(
      leading: Icon(icon, color: color),
      title: Text(transaction.description),
      subtitle: Text(
        '${_formatDate(transaction.createdAt)} • ${transaction.status.name}',
        style: theme.textTheme.bodySmall,
      ),
      trailing: Text(
        '${isPositive ? '+' : ''}${transaction.amount.toStringAsFixed(2)} ${transaction.currency}',
        style: theme.textTheme.titleMedium?.copyWith(
          color: isPositive ? CyberColors.matrixGreen : color,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }

  IconData _getTransactionIcon(TransactionType type) {
    switch (type) {
      case TransactionType.deposit:
        return Icons.arrow_downward;
      case TransactionType.withdrawal:
        return Icons.arrow_upward;
      case TransactionType.referral:
        return Icons.people;
      case TransactionType.bonus:
        return Icons.card_giftcard;
      case TransactionType.subscription:
        return Icons.subscriptions;
    }
  }

  Color _getTransactionColor(TransactionType type, ThemeData theme) {
    switch (type) {
      case TransactionType.deposit:
      case TransactionType.referral:
      case TransactionType.bonus:
        return CyberColors.matrixGreen;
      case TransactionType.withdrawal:
      case TransactionType.subscription:
        return theme.colorScheme.error;
    }
  }

  String _formatDate(DateTime date) {
    return '${date.day}/${date.month}/${date.year}';
  }

  void _showWithdrawDialog(
    BuildContext context,
    WidgetRef ref,
    AppLocalizations l10n,
  ) {
    final balanceAsync = ref.read(walletBalanceProvider);

    balanceAsync.whenData((balance) async {
      final result = await WithdrawBottomSheet.show(context, balance.balance);
      if (result == true && context.mounted) {
        // Refresh wallet data after successful withdrawal
        ref.invalidate(walletBalanceProvider);
        ref.invalidate(walletTransactionsProvider);
      }
    });
  }
}

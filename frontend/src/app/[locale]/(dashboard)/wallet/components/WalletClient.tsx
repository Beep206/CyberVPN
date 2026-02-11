'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { walletApi } from '@/lib/api';
import { Wallet, ArrowDownLeft, ArrowUpRight } from 'lucide-react';
import { WithdrawalModal } from './WithdrawalModal';

export function WalletClient() {
  const t = useTranslations('Wallet');
  const [page, setPage] = useState(0);
  const limit = 20;
  const queryClient = useQueryClient();

  const { data: balance, isLoading: balanceLoading } = useQuery({
    queryKey: ['wallet', 'balance'],
    queryFn: async () => {
      const response = await walletApi.getBalance();
      return response.data;
    },
    staleTime: 30 * 1000,
    refetchInterval: 30 * 1000,
  });

  const { data: transactions, isLoading: txLoading } = useQuery({
    queryKey: ['wallet', 'transactions', page],
    queryFn: async () => {
      const response = await walletApi.getTransactions({ offset: page * limit, limit });
      return response.data;
    },
    staleTime: 30 * 1000,
  });

  const [showWithdraw, setShowWithdraw] = useState(false);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  };

  return (
    <div className="space-y-8 max-w-6xl">
      {/* Balance Card */}
      <div className="cyber-card p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Wallet className="h-8 w-8 text-neon-cyan" />
            <h2 className="text-2xl font-display text-neon-cyan">{t('balance') || 'Available Balance'}</h2>
          </div>
          <button
            onClick={() => setShowWithdraw(true)}
            className="px-6 py-3 bg-neon-cyan/20 hover:bg-neon-cyan/30 border border-neon-cyan/50 text-neon-cyan font-mono text-sm rounded transition-colors flex items-center gap-2"
            aria-label={t('withdraw') || 'Withdraw'}
          >
            <ArrowUpRight className="h-4 w-4" />
            {t('withdraw') || 'Withdraw'}
          </button>
        </div>

        {balanceLoading ? (
          <div className="h-16 bg-grid-line/20 rounded animate-pulse" />
        ) : (
          <div className="text-5xl font-display text-matrix-green drop-shadow-glow">
            {formatCurrency((balance as any)?.balance || 0)}
          </div>
        )}
      </div>

      {/* Transactions List */}
      <section>
        <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
          {t('transactions') || 'Transaction History'}
        </h2>

        {txLoading ? (
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="cyber-card p-4 animate-pulse">
                <div className="h-4 bg-grid-line/20 rounded w-3/4 mb-2" />
                <div className="h-3 bg-grid-line/20 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : !transactions || (transactions as any[]).length === 0 ? (
          <div className="cyber-card p-8 text-center">
            <p className="text-muted-foreground font-mono">{t('noTransactions') || 'No transactions yet'}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {(transactions as any[]).map((tx) => (
              <div key={tx.id} className="cyber-card p-4 flex items-center justify-between hover:bg-terminal-surface/50 transition-colors">
                <div className="flex items-center gap-4">
                  {tx.type === 'credit' ? (
                    <ArrowDownLeft className="h-5 w-5 text-matrix-green" />
                  ) : (
                    <ArrowUpRight className="h-5 w-5 text-neon-pink" />
                  )}
                  <div>
                    <p className="font-mono text-sm">{tx.description || tx.type}</p>
                    <p className="text-xs text-muted-foreground">{new Date(tx.created_at).toLocaleString()}</p>
                  </div>
                </div>
                <div className={`font-display text-lg ${tx.type === 'credit' ? 'text-matrix-green' : 'text-neon-pink'}`}>
                  {tx.type === 'credit' ? '+' : '-'}{formatCurrency(Math.abs(tx.amount))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {transactions && (transactions as any[]).length >= limit && (
          <div className="flex justify-center gap-2 mt-6">
            <button
              onClick={() => setPage(Math.max(0, page - 1))}
              disabled={page === 0}
              className="px-4 py-2 bg-muted/20 hover:bg-muted/30 disabled:opacity-50 disabled:cursor-not-allowed border border-muted/50 text-muted-foreground font-mono text-sm rounded transition-colors"
            >
              {t('previous') || 'Previous'}
            </button>
            <span className="px-4 py-2 font-mono text-sm text-muted-foreground">
              {t('page') || 'Page'} {page + 1}
            </span>
            <button
              onClick={() => setPage(page + 1)}
              className="px-4 py-2 bg-muted/20 hover:bg-muted/30 border border-muted/50 text-muted-foreground font-mono text-sm rounded transition-colors"
            >
              {t('next') || 'Next'}
            </button>
          </div>
        )}
      </section>

      {/* Withdrawal Modal */}
      <WithdrawalModal
        isOpen={showWithdraw}
        onClose={() => setShowWithdraw(false)}
        onSuccess={() => {
          queryClient.invalidateQueries({ queryKey: ['wallet'] });
        }}
        currentBalance={(balance as any)?.balance || 0}
      />
    </div>
  );
}

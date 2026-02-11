'use client';

import { useState } from 'react';
import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { walletApi } from '@/lib/api';
import { motion, AnimatePresence } from 'motion/react';
import {
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  X
} from 'lucide-react';
import { useTelegramWebApp } from '../hooks/useTelegramWebApp';

type TransactionStatus = 'pending' | 'completed' | 'failed' | 'cancelled';

/**
 * Mini App Wallet page
 * Shows balance, transaction history, and withdrawal interface
 */
export default function MiniAppWalletPage() {
  const t = useTranslations('MiniApp.wallet');
  const { haptic, colorScheme } = useTelegramWebApp();
  const [showWithdrawSheet, setShowWithdrawSheet] = useState(false);

  // Fetch wallet balance
  const { data: walletData, isLoading: balanceLoading } = useQuery({
    queryKey: ['wallet'],
    queryFn: async () => {
      const { data } = await walletApi.getBalance();
      return data;
    },
  });

  // Fetch transactions with infinite scroll
  const {
    data: transactionsData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading: transactionsLoading,
  } = useInfiniteQuery({
    queryKey: ['wallet-transactions'],
    queryFn: async ({ pageParam = 0 }) => {
      const { data } = await walletApi.getTransactions({
        offset: pageParam,
        limit: 20,
      });
      return data;
    },
    getNextPageParam: (lastPage, allPages) => {
      const loadedCount = allPages.reduce((sum, page) => sum + (Array.isArray(page) ? page.length : 0), 0);
      // Keep loading if we got a full page (20 items)
      return Array.isArray(lastPage) && lastPage.length === 20 ? loadedCount : undefined;
    },
    initialPageParam: 0,
  });

  const allTransactions = transactionsData?.pages.flatMap((page) => (Array.isArray(page) ? page : [])) || [];

  // Theme colors
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';
  const accentColor = 'text-[var(--tg-link-color,var(--color-neon-cyan))]';

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  return (
    <div className="max-w-screen-sm mx-auto space-y-4">
      {/* Balance Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`${cardBg} ${borderColor} border rounded-lg p-6`}
      >
        {balanceLoading ? (
          <div className="flex items-center justify-center h-24">
            <Loader2 className="h-8 w-8 animate-spin text-neon-cyan" />
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 mb-4">
              <Wallet className={`h-6 w-6 ${accentColor}`} />
              <h2 className="text-lg font-display">{t('balance')}</h2>
            </div>

            <div className="mb-6">
              <div className="text-4xl font-display text-neon-cyan mb-2">
                {formatCurrency(walletData?.balance || 0)}
              </div>
              {walletData?.frozen && walletData.frozen > 0 && (
                <div className="text-sm text-muted-foreground font-mono">
                  {t('frozen')}: {formatCurrency(walletData.frozen)}
                </div>
              )}
            </div>

            <button
              onClick={() => {
                haptic('medium');
                setShowWithdrawSheet(true);
              }}
              className="w-full py-3 px-4 bg-neon-cyan text-black font-mono rounded-lg hover:bg-neon-cyan/90 transition-colors touch-manipulation"
            >
              {t('withdraw')}
            </button>
          </>
        )}
      </motion.div>

      {/* Transactions Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-display text-sm text-muted-foreground">{t('transactions')}</h3>
        {transactionsData && (
          <span className="text-xs font-mono text-muted-foreground">
            {allTransactions.length} {t('total')}
          </span>
        )}
      </div>

      {/* Transactions List */}
      {transactionsLoading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="h-8 w-8 animate-spin text-neon-cyan" />
        </div>
      ) : allTransactions.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={`${cardBg} ${borderColor} border rounded-lg p-8 text-center`}
        >
          <Wallet className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
          <p className="text-sm text-muted-foreground font-mono">{t('noTransactions')}</p>
        </motion.div>
      ) : (
        <div className="space-y-2">
          {allTransactions.map((transaction, index) => (
            <TransactionCard
              key={transaction.id || index}
              transaction={transaction}
              colorScheme={colorScheme}
              formatCurrency={formatCurrency}
              t={t}
            />
          ))}

          {/* Load More */}
          {hasNextPage && (
            <button
              onClick={() => {
                haptic('light');
                fetchNextPage();
              }}
              disabled={isFetchingNextPage}
              className={`w-full py-3 px-4 ${cardBg} ${borderColor} border rounded-lg font-mono text-sm hover:border-neon-cyan/50 transition-colors disabled:opacity-50 touch-manipulation`}
            >
              {isFetchingNextPage ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('loading')}
                </span>
              ) : (
                t('loadMore')
              )}
            </button>
          )}
        </div>
      )}

      {/* Withdraw Bottom Sheet */}
      <WithdrawSheet
        isOpen={showWithdrawSheet}
        onClose={() => setShowWithdrawSheet(false)}
        balance={walletData?.balance || 0}
        colorScheme={colorScheme}
        haptic={haptic}
        t={t}
        formatCurrency={formatCurrency}
      />
    </div>
  );
}

// Transaction Card Component
function TransactionCard({
  transaction,
  colorScheme,
  formatCurrency,
  t,
}: {
  transaction: {
    id?: string;
    amount?: number;
    type?: string;
    status?: string;
    description?: string | null;
    created_at?: string;
    reason?: string;
  };
  colorScheme: 'light' | 'dark';
  formatCurrency: (amount: number) => string;
  t: (key: string) => string;
}) {
  const isDark = colorScheme === 'dark';
  const cardBg = isDark ? 'bg-[var(--tg-bg-color,oklch(0.06_0.015_260))]' : 'bg-[var(--tg-bg-color,oklch(0.70_0.010_250))]';
  const borderColor = isDark ? 'border-[var(--tg-hint-color,oklch(0.25_0.10_195))]' : 'border-[var(--tg-hint-color,oklch(0.45_0.03_250))]';

  const isIncoming = transaction.type === 'deposit' || transaction.type === 'referral_commission' || transaction.type === 'refund';
  const Icon = isIncoming ? ArrowDownRight : ArrowUpRight;
  const amountColor = isIncoming ? 'text-neon-cyan' : 'text-foreground';

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`${cardBg} ${borderColor} border rounded-lg p-4`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1">
          <div className={`p-2 rounded-full ${isIncoming ? 'bg-neon-cyan/10' : 'bg-muted'}`}>
            <Icon className={`h-4 w-4 ${isIncoming ? 'text-neon-cyan' : 'text-muted-foreground'}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-mono text-sm mb-1">
              {transaction.description || t(`type_${transaction.type}` as string)}
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
              {transaction.created_at && (
                <span>{new Date(transaction.created_at).toLocaleDateString()}</span>
              )}
              <StatusBadge status={transaction.status as TransactionStatus} t={t} />
            </div>
          </div>
        </div>
        <div className={`text-lg font-mono font-semibold ${amountColor} whitespace-nowrap`}>
          {isIncoming ? '+' : '-'}
          {formatCurrency(Math.abs(transaction.amount || 0))}
        </div>
      </div>
    </motion.div>
  );
}

// Status Badge Component
function StatusBadge({ status, t }: { status: TransactionStatus; t: (key: string) => string }) {
  const config = {
    pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
    completed: { icon: CheckCircle2, color: 'text-neon-cyan', bg: 'bg-neon-cyan/10' },
    failed: { icon: XCircle, color: 'text-destructive', bg: 'bg-destructive/10' },
    cancelled: { icon: X, color: 'text-muted-foreground', bg: 'bg-muted' },
  };

  const { icon: Icon, color, bg } = config[status] || config.pending;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded ${bg} ${color}`}>
      <Icon className="h-3 w-3" />
      <span>{t(`status_${status}`)}</span>
    </span>
  );
}

// Withdraw Bottom Sheet Component
function WithdrawSheet({
  isOpen,
  onClose,
  balance,
  colorScheme,
  haptic,
  t,
  formatCurrency,
}: {
  isOpen: boolean;
  onClose: () => void;
  balance: number;
  colorScheme: 'light' | 'dark';
  haptic: (style: 'light' | 'medium' | 'heavy') => void;
  t: (key: string) => string;
  formatCurrency: (amount: number) => string;
}) {
  const [amount, setAmount] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('');
  const queryClient = useQueryClient();

  const withdrawMutation = useMutation({
    mutationFn: async (data: { amount: number; method: string }) => {
      const { data: result } = await walletApi.requestWithdrawal(data);
      return result;
    },
    onSuccess: () => {
      haptic('heavy');
      queryClient.invalidateQueries({ queryKey: ['wallet'] });
      queryClient.invalidateQueries({ queryKey: ['wallet-transactions'] });
      onClose();
      setAmount('');
      setPaymentMethod('');
    },
    onError: (error: unknown) => {
      haptic('heavy');
      const axiosError = error as { response?: { data?: { detail?: string } } };
      alert(axiosError.response?.data?.detail || t('withdrawError'));
    },
  });

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const amountNum = parseFloat(amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      alert(t('invalidAmount'));
      return;
    }
    if (amountNum > balance) {
      alert(t('insufficientBalance'));
      return;
    }
    if (!paymentMethod.trim()) {
      alert(t('paymentMethodRequired'));
      return;
    }
    haptic('medium');
    withdrawMutation.mutate({ amount: amountNum, method: paymentMethod });
  };

  const isDark = colorScheme === 'dark';
  const bgColor = isDark ? 'bg-[var(--tg-bg-color,oklch(0.03_0.01_260))]' : 'bg-[var(--tg-bg-color,oklch(0.68_0.012_250))]';

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-40"
          />

          {/* Bottom Sheet */}
          <motion.div
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className={`fixed bottom-0 left-0 right-0 ${bgColor} rounded-t-2xl p-6 z-50 max-w-screen-sm mx-auto`}
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-display">{t('withdrawFunds')}</h3>
              <button
                onClick={onClose}
                className="p-2 hover:bg-muted rounded-lg transition-colors"
                aria-label={t('close')}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Amount Input */}
              <div>
                <label className="block text-sm font-mono text-muted-foreground mb-2">
                  {t('amount')}
                </label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  max={balance}
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  className="w-full px-4 py-3 bg-muted border border-border rounded-lg font-mono text-lg focus:outline-none focus:ring-2 focus:ring-neon-cyan"
                />
                <div className="text-xs text-muted-foreground font-mono mt-1">
                  {t('available')}: {formatCurrency(balance)}
                </div>
              </div>

              {/* Payment Method Input */}
              <div>
                <label className="block text-sm font-mono text-muted-foreground mb-2">
                  {t('paymentMethod')}
                </label>
                <input
                  type="text"
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  placeholder={t('paymentMethodPlaceholder')}
                  className="w-full px-4 py-3 bg-muted border border-border rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-neon-cyan"
                />
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={withdrawMutation.isPending}
                className="w-full py-3 px-4 bg-neon-cyan text-black font-mono rounded-lg hover:bg-neon-cyan/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
              >
                {withdrawMutation.isPending ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t('processing')}
                  </span>
                ) : (
                  t('submitWithdrawal')
                )}
              </button>
            </form>

            <p className="text-xs text-muted-foreground font-mono mt-4 text-center">
              {t('withdrawalNote')}
            </p>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

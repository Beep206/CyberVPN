'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, WalletCards, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { WithdrawalDecisionModal } from '@/features/commerce/components/withdrawal-decision-modal';
import { CommercePageShell } from '@/features/commerce/components/commerce-page-shell';
import { StatusChip } from '@/features/commerce/components/status-chip';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  formatDateTime,
  humanizeToken,
  shortId,
} from '@/features/commerce/lib/formatting';
import { adminWalletApi } from '@/lib/api/wallet';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

interface PendingWithdrawalRecord {
  id: string;
  amount: number;
  currency: string;
  method: string;
  status: string;
  created_at: string;
}

export function WithdrawalsConsole() {
  const t = useTranslations('Commerce');
  const queryClient = useQueryClient();
  const [selectedWithdrawal, setSelectedWithdrawal] = useState<PendingWithdrawalRecord | null>(null);
  const [decisionMode, setDecisionMode] = useState<'approve' | 'reject'>('approve');
  const [feedback, setFeedback] = useState<string | null>(null);

  const withdrawalsQuery = useQuery({
    queryKey: ['commerce', 'withdrawals', 'pending'],
    queryFn: async () => {
      const response = await adminWalletApi.getPendingWithdrawals();
      return response.data;
    },
    staleTime: 30_000,
  });

  const approveMutation = useMutation({
    mutationFn: ({
      withdrawalId,
      payload,
    }: {
      withdrawalId: string;
      payload: Parameters<typeof adminWalletApi.approveWithdrawal>[1];
    }) => adminWalletApi.approveWithdrawal(withdrawalId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'withdrawals', 'pending'] });
      setSelectedWithdrawal(null);
      setFeedback(t('withdrawals.approveSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({
      withdrawalId,
      payload,
    }: {
      withdrawalId: string;
      payload: Parameters<typeof adminWalletApi.rejectWithdrawal>[1];
    }) => adminWalletApi.rejectWithdrawal(withdrawalId, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'withdrawals', 'pending'] });
      setSelectedWithdrawal(null);
      setFeedback(t('withdrawals.rejectSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const withdrawals = withdrawalsQuery.data ?? [];
  const pendingVolume = withdrawals.reduce((sum, withdrawal) => sum + withdrawal.amount, 0);
  const oldestCreatedAt = withdrawals.length
    ? withdrawals.reduce((oldest, current) =>
        new Date(current.created_at).getTime() < new Date(oldest.created_at).getTime()
          ? current
          : oldest,
      ).created_at
    : null;

  function openDecision(withdrawal: PendingWithdrawalRecord, mode: 'approve' | 'reject') {
    setSelectedWithdrawal(withdrawal);
    setDecisionMode(mode);
    setFeedback(null);
  }

  return (
    <>
      <CommercePageShell
        eyebrow={t('withdrawals.eyebrow')}
        title={t('withdrawals.title')}
        description={t('withdrawals.description')}
        icon={WalletCards}
        metrics={[
          {
            label: t('withdrawals.metrics.count'),
            value: formatCompactNumber(withdrawals.length),
            hint: t('withdrawals.metrics.countHint'),
            tone: 'warning',
          },
          {
            label: t('withdrawals.metrics.volume'),
            value: formatCurrencyAmount(pendingVolume, withdrawals[0]?.currency ?? 'USD'),
            hint: t('withdrawals.metrics.volumeHint'),
            tone: 'danger',
          },
          {
            label: t('withdrawals.metrics.oldest'),
            value: oldestCreatedAt ? formatDateTime(oldestCreatedAt) : '--',
            hint: t('withdrawals.metrics.oldestHint'),
            tone: 'neutral',
          },
          {
            label: t('withdrawals.metrics.methods'),
            value: formatCompactNumber(new Set(withdrawals.map((item) => item.method)).size),
            hint: t('withdrawals.metrics.methodsHint'),
            tone: 'info',
          },
        ]}
      >
        <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          {feedback ? (
            <div className="mb-4 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
              {feedback}
            </div>
          ) : null}

          {withdrawalsQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : withdrawals.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-10 text-center text-sm font-mono text-muted-foreground">
              {t('withdrawals.empty')}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.id')}</TableHead>
                  <TableHead>{t('common.amount')}</TableHead>
                  <TableHead>{t('common.method')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('common.createdAt')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {withdrawals.map((withdrawal) => (
                  <TableRow key={withdrawal.id}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          #{shortId(withdrawal.id)}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {withdrawal.id}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      {formatCurrencyAmount(withdrawal.amount, withdrawal.currency)}
                    </TableCell>
                    <TableCell>{humanizeToken(withdrawal.method)}</TableCell>
                    <TableCell>
                      <StatusChip
                        label={humanizeToken(withdrawal.status)}
                        tone="warning"
                      />
                    </TableCell>
                    <TableCell>{formatDateTime(withdrawal.created_at)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          magnetic={false}
                          onClick={() => openDecision(withdrawal, 'approve')}
                        >
                          <Check className="mr-2 h-4 w-4" />
                          {t('withdrawals.approve')}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="destructive"
                          magnetic={false}
                          onClick={() => openDecision(withdrawal, 'reject')}
                        >
                          <X className="mr-2 h-4 w-4" />
                          {t('withdrawals.reject')}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </CommercePageShell>

      <WithdrawalDecisionModal
        isOpen={Boolean(selectedWithdrawal)}
        mode={decisionMode}
        withdrawal={selectedWithdrawal}
        isSubmitting={approveMutation.isPending || rejectMutation.isPending}
        onClose={() => setSelectedWithdrawal(null)}
        onSubmit={async (payload) => {
          if (!selectedWithdrawal) return;

          if (decisionMode === 'approve') {
            await approveMutation.mutateAsync({
              withdrawalId: selectedWithdrawal.id,
              payload,
            });
            return;
          }

          await rejectMutation.mutateAsync({
            withdrawalId: selectedWithdrawal.id,
            payload,
          });
        }}
      />
    </>
  );
}

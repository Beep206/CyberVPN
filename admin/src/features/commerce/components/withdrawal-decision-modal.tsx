'use client';

import { useState, type FormEvent } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Modal } from '@/shared/ui/modal';
import { formatCurrencyAmount, shortId } from '@/features/commerce/lib/formatting';

interface WithdrawalDecisionModalProps {
  isOpen: boolean;
  mode: 'approve' | 'reject';
  isSubmitting?: boolean;
  withdrawal?: {
    id: string;
    amount: number;
    currency: string;
    method: string;
  } | null;
  onClose: () => void;
  onSubmit: (payload: { admin_note?: string }) => Promise<void> | void;
}

export function WithdrawalDecisionModal({
  isOpen,
  mode,
  isSubmitting = false,
  withdrawal,
  onClose,
  onSubmit,
}: WithdrawalDecisionModalProps) {
  const t = useTranslations('Commerce');

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        mode === 'approve'
          ? t('withdrawals.approveTitle')
          : t('withdrawals.rejectTitle')
      }
    >
      <WithdrawalDecisionModalForm
        key={`${mode}:${withdrawal?.id ?? 'none'}`}
        mode={mode}
        isSubmitting={isSubmitting}
        withdrawal={withdrawal}
        onClose={onClose}
        onSubmit={onSubmit}
      />
    </Modal>
  );
}

function WithdrawalDecisionModalForm({
  mode,
  isSubmitting = false,
  withdrawal,
  onClose,
  onSubmit,
}: Omit<WithdrawalDecisionModalProps, 'isOpen'>) {
  const t = useTranslations('Commerce');
  const [note, setNote] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({ admin_note: note.trim() || undefined });
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
        {withdrawal ? (
          <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
            <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              #{shortId(withdrawal.id)}
            </p>
            <p className="mt-2 text-2xl font-display tracking-[0.12em] text-white">
              {formatCurrencyAmount(withdrawal.amount, withdrawal.currency)}
            </p>
            <p className="mt-2 text-sm font-mono text-muted-foreground">
              {t('common.method')}: {withdrawal.method}
            </p>
          </div>
        ) : null}

        <label className="block space-y-2">
          <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {t('common.adminNote')}
          </span>
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            rows={5}
            placeholder={t('withdrawals.notePlaceholder')}
            className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          />
        </label>

        <div className="flex flex-wrap items-center justify-end gap-3">
          <Button type="button" variant="ghost" magnetic={false} onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button
            type="submit"
            magnetic={false}
            disabled={isSubmitting}
            variant={mode === 'approve' ? 'default' : 'destructive'}
          >
            {isSubmitting ? t('common.saving') : t(`withdrawals.${mode}`)}
          </Button>
        </div>
      </form>
  );
}

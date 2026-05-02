'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Gift, Plus } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { growthApi } from '@/lib/api/growth';
import { plansApi } from '@/lib/api/plans';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import {
  formatCompactNumber,
  formatDateTime,
  getErrorMessage,
  shortId,
} from '@/features/growth/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

const initialForm = {
  owner_user_id: '',
  plan_id: '',
  count: '1',
  recipient_hint: '',
  gift_message: '',
  reason_code: 'admin_manual_gift',
  admin_note: '',
};

export function GiftCodesConsole() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [form, setForm] = useState(initialForm);
  const [ownerFilter, setOwnerFilter] = useState('');
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastIssuedCode, setLastIssuedCode] = useState<string | null>(null);
  const [lastIssuedBatchId, setLastIssuedBatchId] = useState<string | null>(null);

  const giftCodesQuery = useQuery({
    queryKey: ['growth', 'gift-codes', ownerFilter],
    queryFn: async () => {
      const response = await growthApi.listGiftCodes({
        owner_user_id: ownerFilter.trim() || undefined,
        offset: 0,
        limit: 100,
      });
      return response.data;
    },
    staleTime: 30_000,
  });

  const plansQuery = useQuery({
    queryKey: ['growth', 'plans', 'gift-codes'],
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data.filter((plan) => plan.is_active);
    },
    staleTime: 60_000,
  });

  const issueMutation = useMutation({
    mutationFn: async () => {
      const count = Number.parseInt(form.count, 10);
      if (count > 1) {
        const response = await growthApi.issueGiftCodeBatch({
          owner_user_id: form.owner_user_id.trim(),
          plan_id: form.plan_id,
          count,
          recipient_hint: form.recipient_hint.trim() || null,
          gift_message: form.gift_message.trim() || null,
          reason_code: form.reason_code.trim() || null,
          admin_note: form.admin_note.trim() || null,
        });
        return {
          type: 'batch' as const,
          batch_id: response.data.batch_id,
          issued_count: response.data.issued_count,
          gift_codes: response.data.gift_codes,
        };
      }

      const response = await growthApi.issueGiftCode({
        owner_user_id: form.owner_user_id.trim(),
        plan_id: form.plan_id,
        recipient_hint: form.recipient_hint.trim() || null,
        gift_message: form.gift_message.trim() || null,
        reason_code: form.reason_code.trim() || null,
        admin_note: form.admin_note.trim() || null,
      });
      return {
        type: 'single' as const,
        batch_id: response.data.gift_code.batch_id ?? null,
        issued_count: 1,
        gift_codes: [response.data.gift_code],
      };
    },
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['growth', 'gift-codes'] });
      const firstIssuedCode = response.gift_codes[0];
      setLastIssuedCode(firstIssuedCode?.raw_code ?? firstIssuedCode?.masked_code ?? null);
      setLastIssuedBatchId(response.batch_id);
      setForm(initialForm);
      setErrorMessage(null);
      setIsCreateOpen(false);
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const giftCodes = giftCodesQuery.data?.items ?? [];
  const totalGiftCodes = giftCodesQuery.data?.total ?? 0;
  const redeemedCount = giftCodes.filter((gift) => gift.status === 'redeemed').length;
  const activeCount = giftCodes.filter((gift) => gift.status === 'active').length;
  const adminIssuedCount = giftCodes.filter((gift) => gift.issuer_type === 'admin').length;
  const plans = plansQuery.data ?? [];

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await issueMutation.mutateAsync();
  }

  return (
    <GrowthPageShell
      eyebrow={t('giftCodes.eyebrow')}
      title={t('giftCodes.title')}
      description={t('giftCodes.description')}
      icon={Gift}
      actions={
        <Button magnetic={false} onClick={() => setIsCreateOpen((current) => !current)}>
          <Plus className="mr-2 h-4 w-4" />
          {isCreateOpen ? t('common.close') : t('giftCodes.issueAction')}
        </Button>
      }
      metrics={[
        {
          label: t('giftCodes.metrics.total'),
          value: formatCompactNumber(totalGiftCodes, locale),
          hint: t('giftCodes.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('giftCodes.metrics.active'),
          value: formatCompactNumber(activeCount, locale),
          hint: t('giftCodes.metrics.activeHint'),
          tone: 'success',
        },
        {
          label: t('giftCodes.metrics.redeemed'),
          value: formatCompactNumber(redeemedCount, locale),
          hint: t('giftCodes.metrics.redeemedHint'),
          tone: 'warning',
        },
        {
          label: t('giftCodes.metrics.lastIssued'),
          value: lastIssuedBatchId ? shortId(lastIssuedBatchId, 12) : lastIssuedCode ? shortId(lastIssuedCode, 12) : '--',
          hint: t('giftCodes.metrics.lastIssuedHint'),
          tone: adminIssuedCount > 0 ? 'neutral' : 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <div className="space-y-6 xl:col-span-5">
          {isCreateOpen ? (
            <form
              onSubmit={handleSubmit}
              className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur"
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                    {t('giftCodes.issuePanelTitle')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('giftCodes.issuePanelDescription')}
                  </p>
                </div>
                <GrowthStatusChip label={t('giftCodes.liveInventory')} tone="success" />
              </div>

              {errorMessage ? (
                <div className="mt-5 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
                  {errorMessage}
                </div>
              ) : null}

              <div className="mt-5 grid gap-4">
                <label className="space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('giftCodes.fields.ownerUserId')}
                  </span>
                  <input
                    required
                    value={form.owner_user_id}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, owner_user_id: event.target.value }))
                    }
                    className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                  />
                </label>

                <label className="space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('giftCodes.fields.planId')}
                  </span>
                  <select
                    required
                    value={form.plan_id}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, plan_id: event.target.value }))
                    }
                    className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                  >
                    <option value="">{t('giftCodes.fields.planPlaceholder')}</option>
                    {plans.map((plan) => (
                      <option key={plan.uuid} value={plan.uuid}>
                        {`${plan.display_name} · ${plan.duration_days}d`}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('giftCodes.fields.count')}
                  </span>
                  <input
                    required
                    min={1}
                    max={100}
                    type="number"
                    value={form.count}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, count: event.target.value }))
                    }
                    className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                  />
                </label>

                <label className="space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('giftCodes.fields.recipientHint')}
                  </span>
                  <input
                    value={form.recipient_hint}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, recipient_hint: event.target.value }))
                    }
                    className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                  />
                </label>

                <label className="space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('giftCodes.fields.giftMessage')}
                  </span>
                  <textarea
                    rows={3}
                    value={form.gift_message}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, gift_message: event.target.value }))
                    }
                    className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                  />
                </label>

                <div className="grid gap-4 md:grid-cols-2">
                  <label className="space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('giftCodes.fields.reasonCode')}
                    </span>
                    <input
                      value={form.reason_code}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, reason_code: event.target.value }))
                      }
                      className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('giftCodes.fields.adminNote')}
                    </span>
                    <input
                      value={form.admin_note}
                      onChange={(event) =>
                        setForm((current) => ({ ...current, admin_note: event.target.value }))
                      }
                      className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                    />
                  </label>
                </div>
              </div>

              <div className="mt-5 flex flex-wrap gap-3">
                <Button type="submit" magnetic={false} disabled={issueMutation.isPending}>
                  {issueMutation.isPending ? t('giftCodes.issuing') : t('giftCodes.issueAction')}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  magnetic={false}
                  onClick={() => {
                    setForm(initialForm);
                    setErrorMessage(null);
                    setIsCreateOpen(false);
                  }}
                >
                  {t('common.cancel')}
                </Button>
              </div>
            </form>
          ) : null}

          <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('giftCodes.filtersTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('giftCodes.filtersDescription')}
            </p>

            <div className="mt-4 grid gap-4">
              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('giftCodes.fields.ownerFilter')}
                </span>
                <input
                  value={ownerFilter}
                  onChange={(event) => setOwnerFilter(event.target.value)}
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                />
              </label>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('giftCodes.inventoryTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('giftCodes.inventoryDescription')}
              </p>
            </div>
            <GrowthStatusChip
              label={giftCodesQuery.isFetching ? t('giftCodes.syncing') : t('giftCodes.liveInventory')}
              tone={giftCodesQuery.isFetching ? 'warning' : 'success'}
            />
          </div>

          <div className="mt-5 overflow-hidden rounded-2xl border border-grid-line/20">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('giftCodes.table.code')}</TableHead>
                  <TableHead>{t('giftCodes.table.owner')}</TableHead>
                  <TableHead>{t('giftCodes.table.plan')}</TableHead>
                  <TableHead>{t('giftCodes.table.recipient')}</TableHead>
                  <TableHead>{t('giftCodes.table.status')}</TableHead>
                  <TableHead>{t('giftCodes.table.redeemed')}</TableHead>
                  <TableHead>{t('giftCodes.table.created')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {giftCodes.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7}>
                      <GrowthEmptyState label={t('giftCodes.empty')} />
                    </TableCell>
                  </TableRow>
                ) : (
                  giftCodes.map((giftCode) => (
                    <TableRow key={giftCode.id}>
                      <TableCell className="font-mono text-neon-cyan">
                        {giftCode.raw_code ?? giftCode.masked_code}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {giftCode.owner_user_id ? shortId(giftCode.owner_user_id) : '--'}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-white/85">
                        {giftCode.plan_family && giftCode.duration_days
                          ? `${giftCode.plan_family} · ${giftCode.duration_days}d`
                          : '--'}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {giftCode.recipient_hint || '--'}
                      </TableCell>
                      <TableCell>
                        <GrowthStatusChip label={giftCode.status} tone={giftCode.status === 'redeemed' ? 'warning' : 'success'} />
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {formatDateTime(giftCode.redeemed_at, locale)}
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {formatDateTime(giftCode.created_at, locale)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </div>
    </GrowthPageShell>
  );
}

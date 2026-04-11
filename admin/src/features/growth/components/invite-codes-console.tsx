'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { TicketPlus } from 'lucide-react';
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
  user_id: '',
  free_days: '7',
  count: '1',
  plan_id: '',
};

export function InviteCodesConsole() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const [form, setForm] = useState(initialForm);
  const [generatedCodes, setGeneratedCodes] = useState<
    Awaited<ReturnType<typeof growthApi.createInviteCodes>>['data']
  >([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const plansQuery = useQuery({
    queryKey: ['growth', 'plans', 'invite-codes'],
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data;
    },
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: growthApi.createInviteCodes,
    onSuccess: (response) => {
      setGeneratedCodes(response.data);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const plans = plansQuery.data ?? [];

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    await createMutation.mutateAsync({
      user_id: form.user_id.trim(),
      free_days: Number(form.free_days || 0),
      count: Number(form.count || 1),
      plan_id: form.plan_id || null,
    });
  }

  return (
    <GrowthPageShell
      eyebrow={t('inviteCodes.eyebrow')}
      title={t('inviteCodes.title')}
      description={t('inviteCodes.description')}
      icon={TicketPlus}
      metrics={[
        {
          label: t('inviteCodes.metrics.lastBatch'),
          value: formatCompactNumber(generatedCodes.length, locale),
          hint: t('inviteCodes.metrics.lastBatchHint'),
          tone: generatedCodes.length > 0 ? 'success' : 'neutral',
        },
        {
          label: t('inviteCodes.metrics.planCatalog'),
          value: formatCompactNumber(plans.length, locale),
          hint: t('inviteCodes.metrics.planCatalogHint'),
          tone: 'info',
        },
        {
          label: t('inviteCodes.metrics.mode'),
          value: t('inviteCodes.metrics.modeValue'),
          hint: t('inviteCodes.metrics.modeHint'),
          tone: 'warning',
        },
        {
          label: t('inviteCodes.metrics.lastCode'),
          value: generatedCodes[0]?.id ? shortId(generatedCodes[0].id) : '--',
          hint: t('inviteCodes.metrics.lastCodeHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5"
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('inviteCodes.formTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('inviteCodes.formDescription')}
              </p>
            </div>
            <GrowthStatusChip
              label={t('inviteCodes.createOnly')}
              tone="warning"
            />
          </div>

          {errorMessage ? (
            <div className="mt-5 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
              {errorMessage}
            </div>
          ) : null}

          <div className="mt-5 grid gap-4">
            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('inviteCodes.fields.userId')}
              </span>
              <input
                required
                value={form.user_id}
                onChange={(event) =>
                  setForm((current) => ({ ...current, user_id: event.target.value }))
                }
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
              />
            </label>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('inviteCodes.fields.freeDays')}
                </span>
                <input
                  required
                  type="number"
                  min="1"
                  value={form.free_days}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, free_days: event.target.value }))
                  }
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('inviteCodes.fields.count')}
                </span>
                <input
                  required
                  type="number"
                  min="1"
                  max="100"
                  value={form.count}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, count: event.target.value }))
                  }
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                />
              </label>
            </div>

            <label className="space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('inviteCodes.fields.planId')}
              </span>
              <select
                value={form.plan_id}
                onChange={(event) =>
                  setForm((current) => ({ ...current, plan_id: event.target.value }))
                }
                className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
              >
                <option value="">{t('inviteCodes.fields.planPlaceholder')}</option>
                {plans.map((plan) => (
                  <option key={plan.uuid} value={plan.uuid}>
                    {plan.name}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mt-5 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
            <p className="text-sm font-mono leading-6 text-muted-foreground">
              {t('inviteCodes.backendNote')}
            </p>
          </div>

          <div className="mt-5 flex flex-wrap gap-3">
            <Button
              type="submit"
              magnetic={false}
              disabled={createMutation.isPending}
            >
              {t('inviteCodes.createAction')}
            </Button>
            <Button
              type="button"
              variant="ghost"
              magnetic={false}
              onClick={() => {
                setForm(initialForm);
                setGeneratedCodes([]);
                setErrorMessage(null);
              }}
            >
              {t('common.reset')}
            </Button>
          </div>
        </form>

        <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('inviteCodes.generatedTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('inviteCodes.generatedDescription')}
              </p>
            </div>
            {generatedCodes.length ? (
              <GrowthStatusChip
                label={t('inviteCodes.generatedCount', { count: generatedCodes.length })}
                tone="success"
              />
            ) : null}
          </div>

          <div className="mt-5">
            {generatedCodes.length === 0 ? (
              <GrowthEmptyState label={t('inviteCodes.generatedEmpty')} />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('inviteCodes.table.code')}</TableHead>
                    <TableHead>{t('inviteCodes.table.freeDays')}</TableHead>
                    <TableHead>{t('inviteCodes.table.used')}</TableHead>
                    <TableHead>{t('inviteCodes.table.expires')}</TableHead>
                    <TableHead>{t('inviteCodes.table.created')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {generatedCodes.map((invite) => (
                    <TableRow key={invite.id}>
                      <TableCell>
                        <div className="space-y-1">
                          <p className="font-display uppercase tracking-[0.14em] text-white">
                            {invite.code}
                          </p>
                          <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                            #{shortId(invite.id)}
                          </p>
                        </div>
                      </TableCell>
                      <TableCell>{invite.free_days}</TableCell>
                      <TableCell>
                        <GrowthStatusChip
                          label={invite.is_used ? t('common.used') : t('common.unused')}
                          tone={invite.is_used ? 'warning' : 'success'}
                        />
                      </TableCell>
                      <TableCell>{formatDateTime(invite.expires_at, locale)}</TableCell>
                      <TableCell>{formatDateTime(invite.created_at, locale)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </div>
      </div>
    </GrowthPageShell>
  );
}

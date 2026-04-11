'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Gift, PencilLine, Plus, Search, ShieldBan } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import type {
  AdminCreatePromoRequest,
  AdminListPromosResponse,
  AdminUpdatePromoRequest,
} from '@/lib/api/growth';
import { growthApi } from '@/lib/api/growth';
import { plansApi } from '@/lib/api/plans';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  formatDateTime,
  getErrorMessage,
  shortId,
  toIsoDateTime,
  toLocalDateTimeInputValue,
} from '@/features/growth/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';
import { AdminActionDialog } from '@/shared/ui/admin-action-dialog';

type PromoRecord = AdminListPromosResponse[number];

const initialCreateForm = {
  code: '',
  discount_type: 'percent',
  discount_value: '15',
  max_uses: '',
  currency: 'USD',
  min_amount: '',
  expires_at: '',
  description: '',
  is_single_use: false,
  plan_ids: [] as string[],
};

const initialUpdateForm = {
  discount_value: '',
  max_uses: '',
  expires_at: '',
  description: '',
  is_active: true,
};

function buildCreatePayload(
  form: typeof initialCreateForm,
): AdminCreatePromoRequest {
  return {
    code: form.code.trim(),
    discount_type: form.discount_type,
    discount_value: Number(form.discount_value || 0),
    max_uses: form.max_uses ? Number(form.max_uses) : null,
    is_single_use: form.is_single_use,
    plan_ids: form.plan_ids.length ? form.plan_ids : null,
    min_amount: form.min_amount ? Number(form.min_amount) : null,
    expires_at: toIsoDateTime(form.expires_at) ?? null,
    description: form.description.trim() || null,
    currency: form.currency.trim().toUpperCase() || 'USD',
  };
}

function buildUpdatePayload(
  form: typeof initialUpdateForm,
): AdminUpdatePromoRequest {
  return {
    discount_value: form.discount_value ? Number(form.discount_value) : null,
    max_uses: form.max_uses ? Number(form.max_uses) : null,
    expires_at: form.expires_at ? toIsoDateTime(form.expires_at) ?? null : null,
    description: form.description.trim() || null,
    is_active: form.is_active,
  };
}

export function PromoCodesConsole() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState(initialCreateForm);
  const [selectedPromoId, setSelectedPromoId] = useState<string | null>(null);
  const [editingPromo, setEditingPromo] = useState<PromoRecord | null>(null);
  const [promoToDeactivate, setPromoToDeactivate] = useState<PromoRecord | null>(null);
  const [updateForm, setUpdateForm] = useState(initialUpdateForm);

  const promosQuery = useQuery({
    queryKey: ['growth', 'promo-codes'],
    queryFn: async () => {
      const response = await growthApi.listPromos({ offset: 0, limit: 100 });
      return response.data;
    },
    staleTime: 30_000,
  });

  const plansQuery = useQuery({
    queryKey: ['growth', 'plans', 'promo-editor'],
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data;
    },
    staleTime: 60_000,
  });

  const promoDetailQuery = useQuery({
    queryKey: ['growth', 'promo-codes', 'detail', selectedPromoId],
    queryFn: async () => {
      if (!selectedPromoId) {
        return null;
      }

      const response = await growthApi.getPromo(selectedPromoId);
      return response.data;
    },
    enabled: Boolean(selectedPromoId),
    staleTime: 15_000,
  });

  const createMutation = useMutation({
    mutationFn: growthApi.createPromo,
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['growth', 'promo-codes'] });
      setCreateForm(initialCreateForm);
      setIsCreateOpen(false);
      setSelectedPromoId(response.data.id);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      promoId,
      payload,
    }: {
      promoId: string;
      payload: AdminUpdatePromoRequest;
    }) => growthApi.updatePromo(promoId, payload),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['growth', 'promo-codes'] });
      await queryClient.invalidateQueries({
        queryKey: ['growth', 'promo-codes', 'detail', response.data.id],
      });
      setSelectedPromoId(response.data.id);
      setEditingPromo(null);
      setUpdateForm(initialUpdateForm);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (promoId: string) => growthApi.deactivatePromo(promoId),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['growth', 'promo-codes'] });
      await queryClient.invalidateQueries({
        queryKey: ['growth', 'promo-codes', 'detail', response.data.id],
      });
      setSelectedPromoId(response.data.id);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const promos = promosQuery.data ?? [];
  const plans = plansQuery.data ?? [];
  const referenceNow = promosQuery.dataUpdatedAt || 0;
  const activePromos = promos.filter((promo) => promo.is_active).length;
  const exhaustedPromos = promos.filter(
    (promo) => promo.max_uses !== null && promo.current_uses >= promo.max_uses,
  ).length;
  const expiringPromos = promos.filter((promo) => {
    if (!promo.expires_at) {
      return false;
    }

    const expiresAt = new Date(promo.expires_at).getTime();
    return (
      expiresAt >= referenceNow
      && expiresAt <= referenceNow + 7 * 24 * 60 * 60 * 1000
    );
  }).length;

  function handlePlanSelection(nextPlanId: string) {
    setCreateForm((current) => ({
      ...current,
      plan_ids: current.plan_ids.includes(nextPlanId)
        ? current.plan_ids.filter((planId) => planId !== nextPlanId)
        : [...current.plan_ids, nextPlanId],
    }));
  }

  function beginEdit(promo: PromoRecord) {
    setEditingPromo(promo);
    setUpdateForm({
      discount_value: String(promo.discount_value),
      max_uses: promo.max_uses === null ? '' : String(promo.max_uses),
      expires_at: toLocalDateTimeInputValue(promo.expires_at),
      description: '',
      is_active: promo.is_active,
    });
  }

  async function handleCreateSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await createMutation.mutateAsync(buildCreatePayload(createForm));
  }

  async function handleUpdateSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingPromo) {
      return;
    }

    await updateMutation.mutateAsync({
      promoId: editingPromo.id,
      payload: buildUpdatePayload(updateForm),
    });
  }

  return (
    <GrowthPageShell
      eyebrow={t('promoCodes.eyebrow')}
      title={t('promoCodes.title')}
      description={t('promoCodes.description')}
      icon={Gift}
      actions={
        <Button
          magnetic={false}
          onClick={() => setIsCreateOpen((current) => !current)}
        >
          <Plus className="mr-2 h-4 w-4" />
          {isCreateOpen ? t('common.close') : t('promoCodes.createAction')}
        </Button>
      }
      metrics={[
        {
          label: t('promoCodes.metrics.total'),
          value: formatCompactNumber(promos.length, locale),
          hint: t('promoCodes.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('promoCodes.metrics.active'),
          value: formatCompactNumber(activePromos, locale),
          hint: t('promoCodes.metrics.activeHint'),
          tone: 'success',
        },
        {
          label: t('promoCodes.metrics.exhausted'),
          value: formatCompactNumber(exhaustedPromos, locale),
          hint: t('promoCodes.metrics.exhaustedHint'),
          tone: exhaustedPromos > 0 ? 'danger' : 'neutral',
        },
        {
          label: t('promoCodes.metrics.expiring'),
          value: formatCompactNumber(expiringPromos, locale),
          hint: t('promoCodes.metrics.expiringHint'),
          tone: expiringPromos > 0 ? 'warning' : 'neutral',
        },
      ]}
    >
      <div className="space-y-6">
        {errorMessage ? (
          <div className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
            {errorMessage}
          </div>
        ) : null}

        {isCreateOpen ? (
          <form
            onSubmit={handleCreateSubmit}
            className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
                <Plus className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('promoCodes.createPanelTitle')}
                </h2>
                <p className="mt-1 text-sm font-mono text-muted-foreground">
                  {t('promoCodes.createPanelDescription')}
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-4 lg:grid-cols-2">
              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('promoCodes.fields.code')}
                </span>
                <input
                  required
                  value={createForm.code}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, code: event.target.value.toUpperCase() }))
                  }
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('promoCodes.fields.discountType')}
                </span>
                <select
                  value={createForm.discount_type}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, discount_type: event.target.value }))
                  }
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                >
                  <option value="percent">percent</option>
                  <option value="fixed">fixed</option>
                </select>
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('promoCodes.fields.discountValue')}
                </span>
                <input
                  required
                  type="number"
                  min="0"
                  step="0.01"
                  value={createForm.discount_value}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, discount_value: event.target.value }))
                  }
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('promoCodes.fields.currency')}
                </span>
                <input
                  value={createForm.currency}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, currency: event.target.value.toUpperCase() }))
                  }
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('promoCodes.fields.maxUses')}
                </span>
                <input
                  type="number"
                  min="1"
                  value={createForm.max_uses}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, max_uses: event.target.value }))
                  }
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('promoCodes.fields.minAmount')}
                </span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={createForm.min_amount}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, min_amount: event.target.value }))
                  }
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('promoCodes.fields.expiresAt')}
                </span>
                <input
                  type="datetime-local"
                  value={createForm.expires_at}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, expires_at: event.target.value }))
                  }
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                />
              </label>

              <label className="space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('promoCodes.fields.description')}
                </span>
                <input
                  value={createForm.description}
                  onChange={(event) =>
                    setCreateForm((current) => ({ ...current, description: event.target.value }))
                  }
                  className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                />
              </label>
            </div>

            <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('promoCodes.fields.planScope')}
                  </p>
                  <GrowthStatusChip
                    label={t('promoCodes.writeOnlyHint')}
                    tone="warning"
                  />
                </div>
                <div className="mt-4 grid gap-2">
                  {plans.length ? (
                    plans.map((plan) => (
                      <label
                        key={plan.uuid}
                        className="flex items-center justify-between gap-3 rounded-xl border border-grid-line/20 bg-terminal-surface/30 px-3 py-2"
                      >
                        <span className="text-sm font-mono text-white">
                          {plan.name}
                        </span>
                        <input
                          type="checkbox"
                          checked={createForm.plan_ids.includes(plan.uuid)}
                          onChange={() => handlePlanSelection(plan.uuid)}
                          className="h-4 w-4 rounded border-grid-line/30 bg-terminal-bg/40"
                        />
                      </label>
                    ))
                  ) : (
                    <GrowthEmptyState label={t('promoCodes.noPlans')} />
                  )}
                </div>
              </div>

              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={createForm.is_single_use}
                    onChange={(event) =>
                      setCreateForm((current) => ({ ...current, is_single_use: event.target.checked }))
                    }
                    className="h-4 w-4 rounded border-grid-line/30 bg-terminal-bg/40"
                  />
                  <span className="text-sm font-mono text-white">
                    {t('promoCodes.fields.isSingleUse')}
                  </span>
                </label>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {t('promoCodes.singleUseHint')}
                </p>
                <div className="mt-5 flex flex-wrap gap-3">
                  <Button
                    type="submit"
                    magnetic={false}
                    disabled={createMutation.isPending}
                  >
                    {t('promoCodes.createAction')}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    magnetic={false}
                    onClick={() => {
                      setCreateForm(initialCreateForm);
                      setIsCreateOpen(false);
                    }}
                  >
                    {t('common.cancel')}
                  </Button>
                </div>
              </div>
            </div>
          </form>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-12">
          <div className="xl:col-span-8">
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              {promosQuery.isLoading ? (
                <div className="grid gap-3">
                  {Array.from({ length: 5 }).map((_, index) => (
                    <div
                      key={index}
                      className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                    />
                  ))}
                </div>
              ) : promos.length === 0 ? (
                <GrowthEmptyState label={t('promoCodes.empty')} />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('promoCodes.table.code')}</TableHead>
                      <TableHead>{t('promoCodes.table.discount')}</TableHead>
                      <TableHead>{t('promoCodes.table.usage')}</TableHead>
                      <TableHead>{t('promoCodes.table.expires')}</TableHead>
                      <TableHead>{t('promoCodes.table.status')}</TableHead>
                      <TableHead>{t('common.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {promos.map((promo) => (
                      <TableRow key={promo.id}>
                        <TableCell>
                          <div className="space-y-1">
                            <p className="font-display uppercase tracking-[0.14em] text-white">
                              {promo.code}
                            </p>
                            <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                              #{shortId(promo.id)}
                            </p>
                          </div>
                        </TableCell>
                        <TableCell>
                          {promo.discount_type === 'percent'
                            ? `${promo.discount_value}%`
                            : formatCurrencyAmount(promo.discount_value, promo.currency, locale)}
                        </TableCell>
                        <TableCell>
                          {promo.current_uses} / {promo.max_uses ?? '∞'}
                        </TableCell>
                        <TableCell>{formatDateTime(promo.expires_at, locale)}</TableCell>
                        <TableCell>
                          <GrowthStatusChip
                            label={promo.is_active ? t('common.active') : t('common.inactive')}
                            tone={promo.is_active ? 'success' : 'warning'}
                          />
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              magnetic={false}
                              onClick={() => setSelectedPromoId(promo.id)}
                            >
                              <Search className="mr-2 h-4 w-4" />
                              {t('promoCodes.inspectAction')}
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              magnetic={false}
                              onClick={() => beginEdit(promo)}
                            >
                              <PencilLine className="mr-2 h-4 w-4" />
                              {t('common.edit')}
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              magnetic={false}
                              onClick={() => setPromoToDeactivate(promo)}
                            >
                              <ShieldBan className="mr-2 h-4 w-4" />
                              {t('promoCodes.deactivateAction')}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </div>

          <div className="space-y-6 xl:col-span-4">
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                    {t('promoCodes.inspectPanelTitle')}
                  </h2>
                  <p className="mt-1 text-sm font-mono text-muted-foreground">
                    {t('promoCodes.inspectPanelDescription')}
                  </p>
                </div>
                {selectedPromoId ? (
                  <GrowthStatusChip label={selectedPromoId.slice(0, 8)} tone="info" />
                ) : null}
              </div>

              <div className="mt-5">
                {!selectedPromoId ? (
                  <GrowthEmptyState label={t('promoCodes.inspectEmpty')} />
                ) : promoDetailQuery.isLoading ? (
                  <div className="h-40 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
                ) : promoDetailQuery.data ? (
                  <div className="space-y-3">
                    {[
                      [t('promoCodes.inspect.code'), promoDetailQuery.data.code],
                      [t('promoCodes.inspect.discountType'), promoDetailQuery.data.discount_type],
                      [t('promoCodes.inspect.discountValue'), String(promoDetailQuery.data.discount_value)],
                      [t('promoCodes.inspect.currency'), promoDetailQuery.data.currency],
                      [
                        t('promoCodes.inspect.usage'),
                        `${promoDetailQuery.data.current_uses} / ${promoDetailQuery.data.max_uses ?? '∞'}`,
                      ],
                      [
                        t('promoCodes.inspect.createdAt'),
                        formatDateTime(promoDetailQuery.data.created_at, locale),
                      ],
                      [
                        t('promoCodes.inspect.expiresAt'),
                        formatDateTime(promoDetailQuery.data.expires_at, locale),
                      ],
                    ].map(([label, value]) => (
                      <div
                        key={label}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3"
                      >
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {label}
                        </p>
                        <p className="mt-2 text-sm font-mono text-white">{value}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <GrowthEmptyState label={t('promoCodes.inspectUnavailable')} />
                )}
              </div>
            </div>

            {editingPromo ? (
              <form
                onSubmit={handleUpdateSubmit}
                className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur"
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                      {t('promoCodes.editPanelTitle')}
                    </h2>
                    <p className="mt-1 text-sm font-mono text-muted-foreground">
                      {editingPromo.code}
                    </p>
                  </div>
                  <GrowthStatusChip
                    label={editingPromo.is_active ? t('common.active') : t('common.inactive')}
                    tone={editingPromo.is_active ? 'success' : 'warning'}
                  />
                </div>

                <div className="mt-5 grid gap-4">
                  <label className="space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('promoCodes.fields.discountValue')}
                    </span>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={updateForm.discount_value}
                      onChange={(event) =>
                        setUpdateForm((current) => ({ ...current, discount_value: event.target.value }))
                      }
                      className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('promoCodes.fields.maxUses')}
                    </span>
                    <input
                      type="number"
                      min="1"
                      value={updateForm.max_uses}
                      onChange={(event) =>
                        setUpdateForm((current) => ({ ...current, max_uses: event.target.value }))
                      }
                      className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('promoCodes.fields.expiresAt')}
                    </span>
                    <input
                      type="datetime-local"
                      value={updateForm.expires_at}
                      onChange={(event) =>
                        setUpdateForm((current) => ({ ...current, expires_at: event.target.value }))
                      }
                      className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                    />
                  </label>

                  <label className="space-y-2">
                    <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('promoCodes.fields.description')}
                    </span>
                    <input
                      value={updateForm.description}
                      onChange={(event) =>
                        setUpdateForm((current) => ({ ...current, description: event.target.value }))
                      }
                      className="w-full rounded-xl border border-grid-line/20 bg-terminal-bg/50 px-4 py-3 font-mono text-sm text-white outline-none transition-colors focus:border-neon-cyan/40"
                    />
                  </label>

                  <label className="flex items-center gap-3 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
                    <input
                      type="checkbox"
                      checked={updateForm.is_active}
                      onChange={(event) =>
                        setUpdateForm((current) => ({ ...current, is_active: event.target.checked }))
                      }
                      className="h-4 w-4 rounded border-grid-line/30 bg-terminal-bg/40"
                    />
                    <span className="text-sm font-mono text-white">
                      {t('promoCodes.fields.isActive')}
                    </span>
                  </label>
                </div>

                <div className="mt-5 flex flex-wrap gap-3">
                  <Button
                    type="submit"
                    magnetic={false}
                    disabled={updateMutation.isPending}
                  >
                    {t('common.save')}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    magnetic={false}
                    onClick={() => {
                      setEditingPromo(null);
                      setUpdateForm(initialUpdateForm);
                    }}
                  >
                    {t('common.cancel')}
                  </Button>
                </div>
              </form>
            ) : null}
          </div>
        </div>
      </div>

      <AdminActionDialog
        isOpen={Boolean(promoToDeactivate)}
        isPending={deactivateMutation.isPending}
        title={t('promoCodes.deactivateTitle')}
        description={t('promoCodes.deactivateConfirm')}
        confirmLabel={t('promoCodes.deactivateAction')}
        cancelLabel={t('common.cancel')}
        subjectLabel={t('promoCodes.fields.code')}
        subject={promoToDeactivate?.code}
        onClose={() => setPromoToDeactivate(null)}
        onConfirm={async () => {
          if (!promoToDeactivate) {
            return;
          }
          await deactivateMutation.mutateAsync(promoToDeactivate.id);
          setPromoToDeactivate(null);
        }}
      />
    </GrowthPageShell>
  );
}

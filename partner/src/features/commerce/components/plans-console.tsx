'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Landmark, PencilLine, Plus, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { plansApi, type CreatePlanRequest, type PlanRecord, type UpdatePlanRequest } from '@/lib/api/plans';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  humanizeToken,
} from '@/features/commerce/lib/formatting';
import { CommercePageShell } from '@/features/commerce/components/commerce-page-shell';
import { PlanEditorModal } from '@/features/commerce/components/plan-editor-modal';
import { StatusChip } from '@/features/commerce/components/status-chip';
import { AdminActionDialog } from '@/shared/ui/admin-action-dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

export function PlansConsole() {
  const t = useTranslations('Commerce');
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<PlanRecord | null>(null);
  const [planToDelete, setPlanToDelete] = useState<PlanRecord | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const plansQuery = useQuery({
    queryKey: ['commerce', 'plans', 'admin'],
    queryFn: async () => {
      const response = await plansApi.listAdmin({ include_inactive: true });
      return response.data.sort((left, right) => left.sort_order - right.sort_order);
    },
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreatePlanRequest) => plansApi.create(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'plans'] });
      setIsCreateOpen(false);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ uuid, payload }: { uuid: string; payload: UpdatePlanRequest }) =>
      plansApi.update(uuid, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'plans'] });
      setEditingPlan(null);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (uuid: string) => plansApi.remove(uuid),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'plans'] });
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const plans = plansQuery.data ?? [];
  const activePlans = plans.filter((plan) => plan.is_active).length;
  const hiddenPlans = plans.filter((plan) => plan.catalog_visibility === 'hidden').length;
  const planFamilies = new Set(plans.map((plan) => plan.plan_code)).size;

  return (
    <>
      <CommercePageShell
        eyebrow={t('plans.eyebrow')}
        title={t('plans.title')}
        description={t('plans.description')}
        icon={Landmark}
        actions={
          <Button magnetic={false} onClick={() => setIsCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('plans.createAction')}
          </Button>
        }
        metrics={[
          {
            label: t('plans.metrics.total'),
            value: formatCompactNumber(plans.length),
            hint: t('plans.metrics.totalHint'),
            tone: 'info',
          },
          {
            label: t('plans.metrics.active'),
            value: formatCompactNumber(activePlans),
            hint: t('plans.metrics.activeHint'),
            tone: 'success',
          },
          {
            label: t('plans.metrics.families'),
            value: formatCompactNumber(planFamilies),
            hint: t('plans.metrics.familiesHint'),
            tone: 'neutral',
          },
          {
            label: t('plans.metrics.hidden'),
            value: formatCompactNumber(hiddenPlans),
            hint: t('plans.metrics.hiddenHint'),
            tone: 'warning',
          },
        ]}
      >
        <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          {errorMessage ? (
            <div className="mb-4 rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">
              {errorMessage}
            </div>
          ) : null}

          {plansQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : plans.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
              {t('plans.empty')}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.name')}</TableHead>
                  <TableHead>{t('plans.fields.visibility')}</TableHead>
                  <TableHead>{t('common.durationDays')}</TableHead>
                  <TableHead>{t('plans.fields.devicesIncluded')}</TableHead>
                  <TableHead>{t('plans.fields.priceUsd')}</TableHead>
                  <TableHead>{t('plans.fields.connectionModes')}</TableHead>
                  <TableHead>{t('plans.fields.inviteBundle')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plans.map((plan) => (
                  <TableRow key={plan.uuid}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {plan.display_name}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {plan.plan_code} / {plan.name}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{humanizeToken(plan.catalog_visibility)}</TableCell>
                    <TableCell>{plan.duration_days}</TableCell>
                    <TableCell>{plan.devices_included}</TableCell>
                    <TableCell>{formatCurrencyAmount(plan.price_usd, 'USD')}</TableCell>
                    <TableCell className="max-w-[18rem]">
                      <span className="text-sm font-mono text-muted-foreground">
                        {plan.connection_modes.join(', ')}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm font-mono text-muted-foreground">
                        {plan.invite_bundle.count}/{plan.invite_bundle.friend_days}/{plan.invite_bundle.expiry_days}
                      </span>
                    </TableCell>
                    <TableCell>
                      <StatusChip
                        label={plan.is_active ? t('common.active') : t('common.inactive')}
                        tone={plan.is_active ? 'success' : 'warning'}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          magnetic={false}
                          onClick={() => setEditingPlan(plan)}
                        >
                          <PencilLine className="mr-2 h-4 w-4" />
                          {t('common.edit')}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          magnetic={false}
                          disabled={deleteMutation.isPending}
                          onClick={() => setPlanToDelete(plan)}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          {t('common.delete')}
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

      <PlanEditorModal
        isOpen={isCreateOpen}
        mode="create"
        isSubmitting={createMutation.isPending}
        onClose={() => setIsCreateOpen(false)}
        onSubmit={async (payload) => {
          await createMutation.mutateAsync(payload as CreatePlanRequest);
        }}
      />

      <PlanEditorModal
        isOpen={Boolean(editingPlan)}
        mode="edit"
        initialPlan={editingPlan}
        isSubmitting={updateMutation.isPending}
        onClose={() => setEditingPlan(null)}
        onSubmit={async (payload) => {
          if (!editingPlan) return;
          await updateMutation.mutateAsync({ uuid: editingPlan.uuid, payload });
        }}
      />

      <AdminActionDialog
        isOpen={Boolean(planToDelete)}
        isPending={deleteMutation.isPending}
        title={t('plans.deleteTitle')}
        description={t('plans.deleteConfirm')}
        confirmLabel={t('common.delete')}
        cancelLabel={t('common.cancel')}
        subjectLabel={t('common.name')}
        subject={planToDelete?.name}
        onClose={() => setPlanToDelete(null)}
        onConfirm={async () => {
          if (!planToDelete) {
            return;
          }
          await deleteMutation.mutateAsync(planToDelete.uuid);
          setPlanToDelete(null);
        }}
      />
    </>
  );
}

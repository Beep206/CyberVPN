'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Landmark, PencilLine, Plus, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { plansApi } from '@/lib/api/plans';
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

interface PlanRecord {
  uuid: string;
  name: string;
  price: number;
  currency: string;
  durationDays: number;
  dataLimitGb?: number | null;
  maxDevices?: number | null;
  features?: string[] | null;
  isActive: boolean;
}

export function PlansConsole() {
  const t = useTranslations('Commerce');
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<PlanRecord | null>(null);
  const [planToDelete, setPlanToDelete] = useState<PlanRecord | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const plansQuery = useQuery({
    queryKey: ['commerce', 'plans'],
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data;
    },
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: plansApi.create,
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
    mutationFn: ({ uuid, payload }: { uuid: string; payload: Parameters<typeof plansApi.update>[1] }) =>
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
  const activePlans = plans.filter((plan) => plan.isActive).length;
  const averagePrice =
    plans.length > 0
      ? plans.reduce((sum, plan) => sum + plan.price, 0) / plans.length
      : undefined;

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
            label: t('plans.metrics.averagePrice'),
            value: formatCurrencyAmount(averagePrice, plans[0]?.currency ?? 'USD'),
            hint: t('plans.metrics.averagePriceHint'),
            tone: 'neutral',
          },
          {
            label: t('plans.metrics.maxDuration'),
            value: `${Math.max(0, ...plans.map((plan) => plan.durationDays))}d`,
            hint: t('plans.metrics.maxDurationHint'),
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
                  <TableHead>{t('common.price')}</TableHead>
                  <TableHead>{t('common.durationDays')}</TableHead>
                  <TableHead>{t('common.dataLimitGb')}</TableHead>
                  <TableHead>{t('common.maxDevices')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('common.features')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {plans.map((plan) => (
                  <TableRow key={plan.uuid}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {plan.name}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          #{plan.uuid.slice(0, 8)}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{formatCurrencyAmount(plan.price, plan.currency)}</TableCell>
                    <TableCell>{plan.durationDays}</TableCell>
                    <TableCell>{plan.dataLimitGb ?? '∞'}</TableCell>
                    <TableCell>{plan.maxDevices ?? '∞'}</TableCell>
                    <TableCell>
                      <StatusChip
                        label={plan.isActive ? t('common.active') : t('common.inactive')}
                        tone={plan.isActive ? 'success' : 'warning'}
                      />
                    </TableCell>
                    <TableCell>
                      <span className="text-sm font-mono text-muted-foreground">
                        {plan.features?.length
                          ? humanizeToken(plan.features.join(', '))
                          : t('common.emptyShort')}
                      </span>
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
          await createMutation.mutateAsync(payload);
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

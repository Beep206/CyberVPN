'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Cuboid, PencilLine, Plus } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { addonsApi, type AddonRecord, type CreateAddonRequest, type UpdateAddonRequest } from '@/lib/api/addons';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  humanizeToken,
} from '@/features/commerce/lib/formatting';
import { AddonEditorModal } from '@/features/commerce/components/addon-editor-modal';
import { CommercePageShell } from '@/features/commerce/components/commerce-page-shell';
import { StatusChip } from '@/features/commerce/components/status-chip';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

export function AddonsConsole() {
  const t = useTranslations('Commerce');
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingAddon, setEditingAddon] = useState<AddonRecord | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const addonsQuery = useQuery({
    queryKey: ['commerce', 'addons'],
    queryFn: async () => {
      const response = await addonsApi.listAdmin({ include_inactive: true });
      return response.data;
    },
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateAddonRequest) => addonsApi.create(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'addons'] });
      setIsCreateOpen(false);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ uuid, payload }: { uuid: string; payload: UpdateAddonRequest }) =>
      addonsApi.update(uuid, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'addons'] });
      setEditingAddon(null);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const addons = addonsQuery.data ?? [];
  const activeAddons = addons.filter((addon) => addon.is_active).length;
  const locationRequired = addons.filter((addon) => addon.requires_location).length;
  const stackable = addons.filter((addon) => addon.is_stackable).length;

  return (
    <>
      <CommercePageShell
        eyebrow={t('addons.eyebrow')}
        title={t('addons.title')}
        description={t('addons.description')}
        icon={Cuboid}
        actions={
          <Button magnetic={false} onClick={() => setIsCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('addons.createAction')}
          </Button>
        }
        metrics={[
          {
            label: t('addons.metrics.total'),
            value: formatCompactNumber(addons.length),
            hint: t('addons.metrics.totalHint'),
            tone: 'info',
          },
          {
            label: t('addons.metrics.active'),
            value: formatCompactNumber(activeAddons),
            hint: t('addons.metrics.activeHint'),
            tone: 'success',
          },
          {
            label: t('addons.metrics.stackable'),
            value: formatCompactNumber(stackable),
            hint: t('addons.metrics.stackableHint'),
            tone: 'neutral',
          },
          {
            label: t('addons.metrics.locationRequired'),
            value: formatCompactNumber(locationRequired),
            hint: t('addons.metrics.locationRequiredHint'),
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

          {addonsQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : addons.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
              {t('addons.empty')}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.name')}</TableHead>
                  <TableHead>{t('addons.fields.priceUsd')}</TableHead>
                  <TableHead>{t('addons.fields.quantityStep')}</TableHead>
                  <TableHead>{t('addons.fields.saleChannels')}</TableHead>
                  <TableHead>{t('addons.fields.deltaEntitlements')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {addons.map((addon) => (
                  <TableRow key={addon.uuid}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {addon.display_name}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {addon.code}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{formatCurrencyAmount(addon.price_usd, 'USD')}</TableCell>
                    <TableCell>{addon.quantity_step}</TableCell>
                    <TableCell className="max-w-[18rem]">
                      <span className="text-sm font-mono text-muted-foreground">
                        {addon.sale_channels.join(', ')}
                      </span>
                    </TableCell>
                    <TableCell className="max-w-[16rem]">
                      <span className="text-sm font-mono text-muted-foreground">
                        {humanizeToken(JSON.stringify(addon.delta_entitlements))}
                      </span>
                    </TableCell>
                    <TableCell>
                      <StatusChip
                        label={addon.is_active ? t('common.active') : t('common.inactive')}
                        tone={addon.is_active ? 'success' : 'warning'}
                      />
                    </TableCell>
                    <TableCell>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        magnetic={false}
                        onClick={() => setEditingAddon(addon)}
                      >
                        <PencilLine className="mr-2 h-4 w-4" />
                        {t('common.edit')}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </CommercePageShell>

      <AddonEditorModal
        isOpen={isCreateOpen}
        mode="create"
        isSubmitting={createMutation.isPending}
        onClose={() => setIsCreateOpen(false)}
        onSubmit={async (payload) => {
          await createMutation.mutateAsync(payload as CreateAddonRequest);
        }}
      />

      <AddonEditorModal
        isOpen={Boolean(editingAddon)}
        mode="edit"
        initialAddon={editingAddon}
        isSubmitting={updateMutation.isPending}
        onClose={() => setEditingAddon(null)}
        onSubmit={async (payload) => {
          if (!editingAddon) return;
          await updateMutation.mutateAsync({ uuid: editingAddon.uuid, payload });
        }}
      />
    </>
  );
}

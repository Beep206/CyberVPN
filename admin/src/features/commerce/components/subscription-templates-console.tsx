'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Package2, PencilLine, Plus, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { subscriptionsApi } from '@/lib/api/subscriptions';
import { CommercePageShell } from '@/features/commerce/components/commerce-page-shell';
import { StatusChip } from '@/features/commerce/components/status-chip';
import { SubscriptionTemplateEditorModal } from '@/features/commerce/components/subscription-template-editor-modal';
import { AdminActionDialog } from '@/shared/ui/admin-action-dialog';
import {
  formatCompactNumber,
  humanizeToken,
} from '@/features/commerce/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

interface SubscriptionTemplateRecord {
  uuid: string;
  name: string;
  templateType: string;
  hostUuid?: string | null;
  inboundTag?: string | null;
  flow?: string | null;
  configData?: Record<string, unknown> | null;
}

export function SubscriptionTemplatesConsole() {
  const t = useTranslations('Commerce');
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<SubscriptionTemplateRecord | null>(null);
  const [templateToDelete, setTemplateToDelete] = useState<SubscriptionTemplateRecord | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const templatesQuery = useQuery({
    queryKey: ['commerce', 'subscription-templates'],
    queryFn: async () => {
      const response = await subscriptionsApi.list();
      return response.data.templates ?? [];
    },
    staleTime: 60_000,
  });

  const createMutation = useMutation({
    mutationFn: subscriptionsApi.create,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'subscription-templates'] });
      setIsCreateOpen(false);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      uuid,
      payload,
    }: {
      uuid: string;
      payload: Parameters<typeof subscriptionsApi.update>[1];
    }) => subscriptionsApi.update(uuid, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'subscription-templates'] });
      setEditingTemplate(null);
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (uuid: string) => subscriptionsApi.remove(uuid),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'subscription-templates'] });
      setErrorMessage(null);
    },
    onError: (error) => {
      setErrorMessage(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const templates = templatesQuery.data ?? [];
  const flowEnabled = templates.filter((item) => Boolean(item.flow)).length;

  return (
    <>
      <CommercePageShell
        eyebrow={t('subscriptionTemplates.eyebrow')}
        title={t('subscriptionTemplates.title')}
        description={t('subscriptionTemplates.description')}
        icon={Package2}
        actions={
          <Button magnetic={false} onClick={() => setIsCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('subscriptionTemplates.createAction')}
          </Button>
        }
        metrics={[
          {
            label: t('subscriptionTemplates.metrics.total'),
            value: formatCompactNumber(templates.length),
            hint: t('subscriptionTemplates.metrics.totalHint'),
            tone: 'info',
          },
          {
            label: t('subscriptionTemplates.metrics.withFlow'),
            value: formatCompactNumber(flowEnabled),
            hint: t('subscriptionTemplates.metrics.withFlowHint'),
            tone: 'success',
          },
          {
            label: t('subscriptionTemplates.metrics.hostBound'),
            value: formatCompactNumber(templates.filter((item) => item.hostUuid).length),
            hint: t('subscriptionTemplates.metrics.hostBoundHint'),
            tone: 'neutral',
          },
          {
            label: t('subscriptionTemplates.metrics.jsonConfig'),
            value: formatCompactNumber(
              templates.filter((item) => item.configData && Object.keys(item.configData).length > 0)
                .length,
            ),
            hint: t('subscriptionTemplates.metrics.jsonConfigHint'),
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

          {templatesQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : templates.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
              {t('subscriptionTemplates.empty')}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.name')}</TableHead>
                  <TableHead>{t('common.templateType')}</TableHead>
                  <TableHead>{t('common.hostUuid')}</TableHead>
                  <TableHead>{t('common.inboundTag')}</TableHead>
                  <TableHead>{t('common.flow')}</TableHead>
                  <TableHead>{t('common.configData')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {templates.map((template) => (
                  <TableRow key={template.uuid}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {template.name}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          #{template.uuid.slice(0, 8)}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{template.templateType}</TableCell>
                    <TableCell>{template.hostUuid ?? t('common.emptyShort')}</TableCell>
                    <TableCell>{template.inboundTag ?? t('common.emptyShort')}</TableCell>
                    <TableCell>
                      {template.flow ? (
                        <StatusChip label={template.flow} tone="info" />
                      ) : (
                        t('common.emptyShort')
                      )}
                    </TableCell>
                    <TableCell>
                      {template.configData ? (
                        <StatusChip
                          label={humanizeToken(Object.keys(template.configData).join(', '))}
                          tone="success"
                        />
                      ) : (
                        t('common.emptyShort')
                      )}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          magnetic={false}
                          onClick={() => setEditingTemplate(template)}
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
                          onClick={() => setTemplateToDelete(template)}
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

      <SubscriptionTemplateEditorModal
        isOpen={isCreateOpen}
        mode="create"
        isSubmitting={createMutation.isPending}
        onClose={() => setIsCreateOpen(false)}
        onSubmit={async (payload) => {
          await createMutation.mutateAsync(payload);
        }}
      />

      <SubscriptionTemplateEditorModal
        isOpen={Boolean(editingTemplate)}
        mode="edit"
        initialTemplate={editingTemplate}
        isSubmitting={updateMutation.isPending}
        onClose={() => setEditingTemplate(null)}
        onSubmit={async (payload) => {
          if (!editingTemplate) return;
          await updateMutation.mutateAsync({ uuid: editingTemplate.uuid, payload });
        }}
      />

      <AdminActionDialog
        isOpen={Boolean(templateToDelete)}
        isPending={deleteMutation.isPending}
        title={t('subscriptionTemplates.deleteTitle')}
        description={t('subscriptionTemplates.deleteConfirm')}
        confirmLabel={t('common.delete')}
        cancelLabel={t('common.cancel')}
        subjectLabel={t('common.name')}
        subject={templateToDelete?.name}
        onClose={() => setTemplateToDelete(null)}
        onConfirm={async () => {
          if (!templateToDelete) {
            return;
          }
          await deleteMutation.mutateAsync(templateToDelete.uuid);
          setTemplateToDelete(null);
        }}
      />
    </>
  );
}

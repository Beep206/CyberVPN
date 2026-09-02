'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Package2, PencilLine, Plus, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { subscriptionsApi } from '@/lib/api/subscriptions';
import { CommercePageShell } from '@/features/commerce/components/commerce-page-shell';
import { StatusChip } from '@/features/commerce/components/status-chip';
import { AdminActionDialog } from '@/shared/ui/admin-action-dialog';
import { formatCompactNumber } from '@/features/commerce/lib/formatting';
import { Modal } from '@/shared/ui/modal';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/organisms/table';

type SubscriptionTemplateRecord = NonNullable<
  Awaited<ReturnType<typeof subscriptionsApi.list>>['data']['templates']
>[number];
type SubscriptionTemplateUpdate = Parameters<typeof subscriptionsApi.update>[1];

interface EditorState {
  name: string;
  templateJson: string;
  encodedTemplateYaml: string;
}

interface Feedback {
  message: string;
  tone: 'error' | 'info' | 'success';
}

function isJsonRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function toEditorState(template: SubscriptionTemplateRecord): EditorState {
  return {
    name: template.name,
    templateJson: template.templateJson ? JSON.stringify(template.templateJson, null, 2) : '',
    encodedTemplateYaml: template.encodedTemplateYaml ?? '',
  };
}

function buildUpdatePayload(editor: EditorState): SubscriptionTemplateUpdate {
  let templateJson: Record<string, unknown> | null = null;
  if (editor.templateJson.trim()) {
    const parsed: unknown = JSON.parse(editor.templateJson);
    if (!isJsonRecord(parsed)) throw new Error('template-json-must-be-an-object');
    templateJson = parsed;
  }
  return {
    name: editor.name.trim(),
    templateJson,
    encodedTemplateYaml: editor.encodedTemplateYaml.trim() || null,
  };
}

export function SubscriptionTemplatesConsole() {
  const t = useTranslations('Commerce');
  const queryClient = useQueryClient();
  const [editingTemplate, setEditingTemplate] = useState<SubscriptionTemplateRecord | null>(null);
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [templateToDelete, setTemplateToDelete] = useState<SubscriptionTemplateRecord | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const templatesQuery = useQuery({
    queryKey: ['commerce', 'subscription-templates'],
    queryFn: async () => (await subscriptionsApi.list()).data.templates ?? [],
    staleTime: 60_000,
    retry: false,
  });

  const updateMutation = useMutation({
    mutationFn: ({ uuid, payload }: { uuid: string; payload: SubscriptionTemplateUpdate }) =>
      subscriptionsApi.update(uuid, payload),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'subscription-templates'] });
      setEditingTemplate(null);
      setEditor(null);
      setFeedback(response.status === 202
        ? { message: t('subscriptionTemplates.updatePending'), tone: 'info' }
        : { message: t('subscriptionTemplates.updateSuccess'), tone: 'success' });
    },
    onError: () => setValidationError(t('common.actionFailed')),
  });

  const deleteMutation = useMutation({
    mutationFn: (uuid: string) => subscriptionsApi.remove(uuid),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['commerce', 'subscription-templates'] });
      setTemplateToDelete(null);
      setFeedback(null);
    },
    onError: (error) => setFeedback({
      message: error instanceof Error ? error.message : t('common.actionFailed'),
      tone: 'error',
    }),
  });

  const templates = templatesQuery.data ?? [];

  function beginEdit(template: SubscriptionTemplateRecord) {
    setEditingTemplate(template);
    setEditor(toEditorState(template));
    setValidationError(null);
    setFeedback(null);
  }

  async function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationError(null);
    if (!editingTemplate || !editor || !editor.name.trim()) {
      setValidationError(t('common.validation.nameRequired'));
      return;
    }
    let payload: SubscriptionTemplateUpdate;
    try {
      payload = buildUpdatePayload(editor);
    } catch (error) {
      setValidationError(error instanceof SyntaxError
        ? t('common.validation.configJsonInvalid')
        : t('subscriptionTemplates.validation.jsonObjectRequired'));
      return;
    }
    await updateMutation.mutateAsync({ uuid: editingTemplate.uuid, payload }).catch(() => undefined);
  }

  return (
    <>
      <CommercePageShell
        eyebrow={t('subscriptionTemplates.eyebrow')}
        title={t('subscriptionTemplates.title')}
        description={t('subscriptionTemplates.description')}
        icon={Package2}
        actions={(
          <Button magnetic={false} disabled title={t('subscriptionTemplates.createUnavailable')}>
            <Plus className="mr-2 h-4 w-4" />
            {t('subscriptionTemplates.createAction')}
          </Button>
        )}
        metrics={[
          { label: t('subscriptionTemplates.metrics.total'), value: formatCompactNumber(templates.length), hint: t('subscriptionTemplates.metrics.totalHint'), tone: 'info' },
          { label: t('subscriptionTemplates.metrics.jsonConfig'), value: formatCompactNumber(templates.filter((item) => item.templateJson).length), hint: t('subscriptionTemplates.metrics.jsonConfigHint'), tone: 'success' },
          { label: t('subscriptionTemplates.metrics.yamlConfig'), value: formatCompactNumber(templates.filter((item) => item.encodedTemplateYaml).length), hint: t('subscriptionTemplates.metrics.yamlConfigHint'), tone: 'neutral' },
          { label: t('subscriptionTemplates.metrics.tagged'), value: formatCompactNumber(templates.filter((item) => item.tags.length > 0).length), hint: t('subscriptionTemplates.metrics.taggedHint'), tone: 'warning' },
        ]}
      >
        <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="mb-4 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-muted-foreground">{t('subscriptionTemplates.createUnavailable')}</div>
          {feedback ? <div role={feedback.tone === 'error' ? 'alert' : 'status'} className="mb-4 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">{feedback.message}</div> : null}

          {templatesQuery.isLoading ? (
            <div role="status" aria-label={t('common.loading')} className="grid gap-3">
              {Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />)}
            </div>
          ) : templatesQuery.isError ? (
            <div role="alert" className="rounded-2xl border border-neon-pink/25 bg-neon-pink/10 p-5 text-sm font-mono text-neon-pink">
              <p>{t('subscriptionTemplates.loadFailed')}</p>
              <Button type="button" variant="ghost" magnetic={false} onClick={() => void templatesQuery.refetch()}>{t('common.retry')}</Button>
            </div>
          ) : templates.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">{t('subscriptionTemplates.empty')}</div>
          ) : (
            <Table>
              <TableHeader><TableRow>
                <TableHead>{t('common.name')}</TableHead>
                <TableHead>{t('common.templateType')}</TableHead>
                <TableHead>{t('subscriptionTemplates.fields.tags')}</TableHead>
                <TableHead>{t('subscriptionTemplates.fields.templateJson')}</TableHead>
                <TableHead>{t('subscriptionTemplates.fields.encodedTemplateYaml')}</TableHead>
                <TableHead>{t('common.actions')}</TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {templates.map((template) => (
                  <TableRow key={template.uuid}>
                    <TableCell><div className="space-y-1"><p className="font-display uppercase tracking-[0.14em] text-white">{template.name}</p><p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">#{template.uuid.slice(0, 8)}</p></div></TableCell>
                    <TableCell>{template.templateType}</TableCell>
                    <TableCell>{template.tags.length ? template.tags.join(', ') : t('common.emptyShort')}</TableCell>
                    <TableCell>{template.templateJson ? <StatusChip label={t('subscriptionTemplates.configured')} tone="success" /> : t('common.emptyShort')}</TableCell>
                    <TableCell>{template.encodedTemplateYaml ? <StatusChip label={t('subscriptionTemplates.configured')} tone="info" /> : t('common.emptyShort')}</TableCell>
                    <TableCell><div className="flex flex-wrap gap-2">
                      <Button type="button" size="sm" variant="ghost" magnetic={false} onClick={() => beginEdit(template)}><PencilLine className="mr-2 h-4 w-4" />{t('common.edit')}</Button>
                      <Button type="button" size="sm" variant="ghost" magnetic={false} disabled={deleteMutation.isPending} onClick={() => setTemplateToDelete(template)}><Trash2 className="mr-2 h-4 w-4" />{t('common.delete')}</Button>
                    </div></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </CommercePageShell>

      <Modal isOpen={Boolean(editingTemplate && editor)} onClose={() => { setEditingTemplate(null); setEditor(null); setValidationError(null); }} title={t('subscriptionTemplates.editTitle')}>
        {editingTemplate && editor ? (
          <form className="space-y-5" onSubmit={submitEdit}>
            <label className="block space-y-2"><span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">{t('common.name')}</span><Input value={editor.name} onChange={(event) => setEditor((current) => current ? ({ ...current, name: event.target.value }) : current)} /></label>
            <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-muted-foreground">{t('common.templateType')}: {editingTemplate.templateType}</div>
            <label className="block space-y-2"><span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">{t('subscriptionTemplates.fields.templateJson')}</span><textarea rows={10} value={editor.templateJson} onChange={(event) => setEditor((current) => current ? ({ ...current, templateJson: event.target.value }) : current)} className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm" /></label>
            <label className="block space-y-2"><span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">{t('subscriptionTemplates.fields.encodedTemplateYaml')}</span><textarea rows={6} value={editor.encodedTemplateYaml} onChange={(event) => setEditor((current) => current ? ({ ...current, encodedTemplateYaml: event.target.value }) : current)} className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm" /></label>
            {validationError ? <div role="alert" className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink">{validationError}</div> : null}
            <div className="flex flex-wrap items-center justify-end gap-3"><Button type="button" variant="ghost" magnetic={false} onClick={() => { setEditingTemplate(null); setEditor(null); setValidationError(null); }}>{t('common.cancel')}</Button><Button type="submit" magnetic={false} disabled={updateMutation.isPending}>{updateMutation.isPending ? t('common.saving') : t('common.save')}</Button></div>
          </form>
        ) : null}
      </Modal>

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
        onConfirm={async () => { if (templateToDelete) await deleteMutation.mutateAsync(templateToDelete.uuid); }}
      />
    </>
  );
}

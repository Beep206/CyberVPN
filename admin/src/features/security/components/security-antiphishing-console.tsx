'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Eye,
  EyeOff,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { securityApi } from '@/lib/api/security';
import { SecurityEmptyState } from '@/features/security/components/security-empty-state';
import { SecurityPageShell } from '@/features/security/components/security-page-shell';
import { SecurityStatusChip } from '@/features/security/components/security-status-chip';
import {
  getErrorMessage,
  maskSensitiveCode,
} from '@/features/security/lib/formatting';
import { AdminActionDialog } from '@/shared/ui/admin-action-dialog';

export function SecurityAntiPhishingConsole() {
  const t = useTranslations('AdminSecurity');
  const queryClient = useQueryClient();
  const [draftCode, setDraftCode] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showCode, setShowCode] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const codeQuery = useQuery({
    queryKey: ['security', 'anti-phishing'],
    queryFn: async () => {
      const response = await securityApi.getAntiphishingCode();
      return response.data;
    },
    staleTime: 15_000,
  });

  const saveMutation = useMutation({
    mutationFn: (code: string) => securityApi.setAntiphishingCode({ code }),
    onSuccess: async (response) => {
      queryClient.setQueryData(['security', 'anti-phishing'], response.data);
      await queryClient.invalidateQueries({ queryKey: ['security', 'anti-phishing'] });
      setDraftCode('');
      setIsDirty(false);
      setFeedback(t('antiPhishing.saveSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => securityApi.deleteAntiphishingCode(),
    onSuccess: async (response) => {
      queryClient.setQueryData(['security', 'anti-phishing'], { code: null });
      await queryClient.invalidateQueries({ queryKey: ['security', 'anti-phishing'] });
      setDraftCode('');
      setIsDirty(false);
      setFeedback(response.data.message || t('antiPhishing.deleteSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const currentCode = codeQuery.data?.code ?? null;
  const codeLength = currentCode?.length ?? 0;
  const effectiveDraftCode = isDirty ? draftCode : currentCode ?? '';

  return (
    <SecurityPageShell
      eyebrow={t('antiPhishing.eyebrow')}
      title={t('antiPhishing.title')}
      description={t('antiPhishing.description')}
      icon={ShieldCheck}
      metrics={[
        {
          label: t('antiPhishing.metrics.status'),
          value: currentCode ? t('common.enabled') : t('common.disabled'),
          hint: t('antiPhishing.metrics.statusHint'),
          tone: currentCode ? 'success' : 'warning',
        },
        {
          label: t('antiPhishing.metrics.length'),
          value: String(codeLength),
          hint: t('antiPhishing.metrics.lengthHint'),
          tone: codeLength >= 4 ? 'info' : 'neutral',
        },
        {
          label: t('antiPhishing.metrics.preview'),
          value: currentCode ? maskSensitiveCode(currentCode) : '--',
          hint: t('antiPhishing.metrics.previewHint'),
          tone: 'neutral',
        },
        {
          label: t('antiPhishing.metrics.delivery'),
          value: currentCode ? t('common.protected') : t('common.pending'),
          hint: t('antiPhishing.metrics.deliveryHint'),
          tone: currentCode ? 'success' : 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('antiPhishing.currentTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('antiPhishing.currentDescription')}
          </p>

          {feedback ? (
            <div className="mt-5 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
              {feedback}
            </div>
          ) : null}

          <div className="mt-5">
            {codeQuery.isLoading ? (
              <SecurityEmptyState label={t('common.loading')} />
            ) : currentCode ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <div>
                    <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {t('antiPhishing.currentCode')}
                    </p>
                    <p className="mt-3 font-mono text-lg tracking-[0.18em] text-white">
                      {showCode ? currentCode : maskSensitiveCode(currentCode)}
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <SecurityStatusChip
                      label={t('common.enabled')}
                      tone="success"
                    />
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      magnetic={false}
                      onClick={() => setShowCode((current) => !current)}
                    >
                      {showCode ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>

                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-sm font-mono leading-6 text-muted-foreground">
                    {t('antiPhishing.explainer')}
                  </p>
                </div>
              </div>
            ) : (
              <SecurityEmptyState label={t('antiPhishing.empty')} />
            )}
          </div>
        </section>

        <section className="space-y-6 xl:col-span-5">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('antiPhishing.editorTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('antiPhishing.editorDescription')}
            </p>

            <div className="mt-5 space-y-4">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('antiPhishing.fieldLabel')}
                </span>
                <Input
                  value={effectiveDraftCode}
                  onChange={(event) => {
                    setDraftCode(event.target.value);
                    setIsDirty(true);
                  }}
                  placeholder={t('antiPhishing.placeholder')}
                />
              </label>

              <Button
                type="button"
                magnetic={false}
                disabled={saveMutation.isPending}
                onClick={() => {
                  const nextCode = effectiveDraftCode.trim();

                  if (!nextCode) {
                    setFeedback(t('common.validation.antiPhishingRequired'));
                    return;
                  }
                  if (nextCode.length > 50) {
                    setFeedback(t('common.validation.antiPhishingTooLong'));
                    return;
                  }
                  saveMutation.mutate(nextCode);
                }}
              >
                {t('common.save')}
              </Button>
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('antiPhishing.deleteTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('antiPhishing.deleteDescription')}
            </p>

            <Button
              type="button"
              magnetic={false}
              variant="ghost"
              className="mt-5"
              disabled={deleteMutation.isPending || !currentCode}
              onClick={() => setDeleteDialogOpen(true)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              {t('common.delete')}
            </Button>
          </article>
        </section>
      </div>

      <AdminActionDialog
        isOpen={deleteDialogOpen}
        isPending={deleteMutation.isPending}
        title={t('antiPhishing.deleteTitle')}
        description={t('antiPhishing.deleteConfirm')}
        confirmLabel={t('common.delete')}
        cancelLabel={t('common.cancel')}
        subjectLabel={t('antiPhishing.currentCode')}
        subject={currentCode ? maskSensitiveCode(currentCode) : '--'}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={async () => {
          await deleteMutation.mutateAsync();
          setDeleteDialogOpen(false);
        }}
      />
    </SecurityPageShell>
  );
}

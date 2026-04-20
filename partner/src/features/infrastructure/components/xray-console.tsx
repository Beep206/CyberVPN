'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Save, ShieldCheck } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { xrayApi } from '@/lib/api/infrastructure';
import { JsonPreview } from '@/features/infrastructure/components/json-preview';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { parseJsonObject, stringifyJson } from '@/features/infrastructure/lib/formatting';

export function XrayConsole() {
  const t = useTranslations('Infrastructure');
  const queryClient = useQueryClient();
  const [draftText, setDraftText] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

  const xrayQuery = useQuery({
    queryKey: ['infrastructure', 'xray'],
    queryFn: async () => {
      const response = await xrayApi.getConfig();
      return response.data;
    },
    staleTime: 30_000,
  });

  const updateMutation = useMutation({
    mutationFn: xrayApi.updateConfig,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'xray'] });
      setDraftText('');
      setFeedback(t('xray.updateSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const effectiveDraft = draftText || stringifyJson(xrayQuery.data);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    const parsed = parseJsonObject(effectiveDraft);
    await updateMutation.mutateAsync({
      log: typeof parsed.log === 'object' && parsed.log !== null ? parsed.log as Record<string, unknown> : undefined,
      inbounds: Array.isArray(parsed.inbounds) ? parsed.inbounds as Record<string, unknown>[] : undefined,
      outbounds: Array.isArray(parsed.outbounds) ? parsed.outbounds as Record<string, unknown>[] : undefined,
      routing: typeof parsed.routing === 'object' && parsed.routing !== null ? parsed.routing as Record<string, unknown> : undefined,
      dns: typeof parsed.dns === 'object' && parsed.dns !== null ? parsed.dns as Record<string, unknown> : undefined,
      policy: typeof parsed.policy === 'object' && parsed.policy !== null ? parsed.policy as Record<string, unknown> : undefined,
    });
  }

  return (
    <InfrastructurePageShell
      eyebrow={t('xray.eyebrow')}
      title={t('xray.title')}
      description={t('xray.description')}
      icon={ShieldCheck}
      metrics={[
        {
          label: t('xray.metrics.inbounds'),
          value: String(xrayQuery.data?.inbounds?.length ?? 0),
          hint: t('xray.metrics.inboundsHint'),
          tone: 'info',
        },
        {
          label: t('xray.metrics.outbounds'),
          value: String(xrayQuery.data?.outbounds?.length ?? 0),
          hint: t('xray.metrics.outboundsHint'),
          tone: 'success',
        },
        {
          label: t('xray.metrics.routes'),
          value: String(Array.isArray(xrayQuery.data?.routing?.rules) ? xrayQuery.data?.routing?.rules.length : 0),
          hint: t('xray.metrics.routesHint'),
          tone: 'warning',
        },
        {
          label: t('xray.metrics.logKeys'),
          value: String(Object.keys(xrayQuery.data?.log ?? {}).length),
          hint: t('xray.metrics.logKeysHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('xray.editorTitle')}
          </h2>
          {feedback ? (
            <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
              {feedback}
            </div>
          ) : null}
          <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
            <textarea
              value={effectiveDraft}
              onChange={(event) => setDraftText(event.target.value)}
              rows={24}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 font-mono text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
            <div className="flex flex-wrap gap-3">
              <Button type="submit" magnetic={false} disabled={updateMutation.isPending}>
                <Save className="mr-2 h-4 w-4" />
                {t('xray.saveAction')}
              </Button>
              <Button
                type="button"
                variant="ghost"
                magnetic={false}
                onClick={() => setDraftText('')}
              >
                {t('common.reset')}
              </Button>
            </div>
          </form>
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('xray.snapshotTitle')}
          </h2>
          <div className="mt-5">
            <JsonPreview value={xrayQuery.data ?? {}} />
          </div>
        </section>
      </div>
    </InfrastructurePageShell>
  );
}

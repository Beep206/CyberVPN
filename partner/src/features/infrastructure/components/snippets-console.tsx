'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileCode2, Plus } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { snippetsApi } from '@/lib/api/infrastructure';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import { formatCompactNumber, shortId } from '@/features/infrastructure/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

interface SnippetFormState {
  name: string;
  snippet_type: string;
  content: string;
  order: string;
  is_active: boolean;
}

const EMPTY_FORM: SnippetFormState = {
  name: '',
  snippet_type: 'header',
  content: '',
  order: '',
  is_active: true,
};

export function SnippetsConsole() {
  const t = useTranslations('Infrastructure');
  const queryClient = useQueryClient();
  const [form, setForm] = useState<SnippetFormState>(EMPTY_FORM);
  const [feedback, setFeedback] = useState<string | null>(null);

  const snippetsQuery = useQuery({
    queryKey: ['infrastructure', 'snippets'],
    queryFn: async () => {
      const response = await snippetsApi.list();
      return response.data;
    },
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: snippetsApi.create,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'snippets'] });
      setForm(EMPTY_FORM);
      setFeedback(t('snippets.createSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const snippets = snippetsQuery.data ?? [];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    if (!form.name.trim() || !form.snippet_type.trim() || !form.content.trim()) {
      setFeedback(t('common.validation.snippetFormInvalid'));
      return;
    }

    await createMutation.mutateAsync({
      name: form.name.trim(),
      snippet_type: form.snippet_type.trim(),
      content: form.content,
      order: form.order ? Number(form.order) : undefined,
      is_active: form.is_active,
    });
  }

  return (
    <InfrastructurePageShell
      eyebrow={t('snippets.eyebrow')}
      title={t('snippets.title')}
      description={t('snippets.description')}
      icon={FileCode2}
      metrics={[
        {
          label: t('snippets.metrics.total'),
          value: formatCompactNumber(snippets.length),
          hint: t('snippets.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('snippets.metrics.active'),
          value: formatCompactNumber(snippets.filter((snippet) => snippet.isActive).length),
          hint: t('snippets.metrics.activeHint'),
          tone: 'success',
        },
        {
          label: t('snippets.metrics.types'),
          value: formatCompactNumber(new Set(snippets.map((snippet) => snippet.snippetType)).size),
          hint: t('snippets.metrics.typesHint'),
          tone: 'warning',
        },
        {
          label: t('snippets.metrics.ordered'),
          value: formatCompactNumber(snippets.filter((snippet) => snippet.order !== null).length),
          hint: t('snippets.metrics.orderedHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          {snippets.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.name')}</TableHead>
                  <TableHead>{t('common.type')}</TableHead>
                  <TableHead>{t('common.order')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {snippets.map((snippet) => (
                  <TableRow key={snippet.uuid}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {snippet.name}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          #{shortId(snippet.uuid)}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{snippet.snippetType}</TableCell>
                    <TableCell>{snippet.order ?? '--'}</TableCell>
                    <TableCell>
                      <InfrastructureStatusChip
                        label={snippet.isActive ? t('common.active') : t('common.disabled')}
                        tone={snippet.isActive ? 'success' : 'warning'}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <InfrastructureEmptyState label={t('snippets.empty')} />
          )}
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('snippets.createTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('snippets.createDescription')}
              </p>
            </div>
            <Plus className="h-5 w-5 text-neon-cyan" />
          </div>

          {feedback ? (
            <div className="mt-5 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
              {feedback}
            </div>
          ) : null}

          <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.name')}
              </span>
              <Input
                value={form.name}
                onChange={(event) =>
                  setForm((current) => ({ ...current, name: event.target.value }))
                }
                placeholder="CDN Headers"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.type')}
              </span>
              <Input
                value={form.snippet_type}
                onChange={(event) =>
                  setForm((current) => ({ ...current, snippet_type: event.target.value }))
                }
                placeholder="header"
              />
            </label>
            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.order')}
              </span>
              <Input
                type="number"
                min="0"
                value={form.order}
                onChange={(event) =>
                  setForm((current) => ({ ...current, order: event.target.value }))
                }
                placeholder={t('common.optional')}
              />
            </label>
            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.content')}
              </span>
              <textarea
                value={form.content}
                onChange={(event) =>
                  setForm((current) => ({ ...current, content: event.target.value }))
                }
                rows={10}
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) =>
                  setForm((current) => ({ ...current, is_active: event.target.checked }))
                }
              />
              <span className="text-sm font-mono text-foreground">{t('common.active')}</span>
            </label>
            <Button type="submit" magnetic={false} disabled={createMutation.isPending}>
              {t('snippets.createAction')}
            </Button>
          </form>
        </section>
      </div>
    </InfrastructurePageShell>
  );
}

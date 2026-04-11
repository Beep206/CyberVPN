'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Group, Plus } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { squadsApi } from '@/lib/api/infrastructure';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import { formatCompactNumber, parseCsvList, shortId } from '@/features/infrastructure/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

interface SquadFormState {
  name: string;
  squad_type: 'internal' | 'external';
  inbounds: string;
  max_members: string;
  description: string;
  is_active: boolean;
}

const EMPTY_FORM: SquadFormState = {
  name: '',
  squad_type: 'internal',
  inbounds: '',
  max_members: '',
  description: '',
  is_active: true,
};

export function SquadsConsole() {
  const t = useTranslations('Infrastructure');
  const queryClient = useQueryClient();
  const [form, setForm] = useState<SquadFormState>(EMPTY_FORM);
  const [feedback, setFeedback] = useState<string | null>(null);

  const internalQuery = useQuery({
    queryKey: ['infrastructure', 'squads', 'internal'],
    queryFn: async () => {
      const response = await squadsApi.listInternal();
      return response.data;
    },
    staleTime: 30_000,
  });

  const externalQuery = useQuery({
    queryKey: ['infrastructure', 'squads', 'external'],
    queryFn: async () => {
      const response = await squadsApi.listExternal();
      return response.data;
    },
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: squadsApi.create,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'squads'] });
      setForm(EMPTY_FORM);
      setFeedback(t('squads.createSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const internalSquads = internalQuery.data ?? [];
  const externalSquads = externalQuery.data ?? [];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    if (!form.name.trim()) {
      setFeedback(t('common.validation.nameRequired'));
      return;
    }

    await createMutation.mutateAsync({
      name: form.name.trim(),
      squad_type: form.squad_type,
      description: form.description.trim() || undefined,
      is_active: form.is_active,
      max_members: form.max_members ? Number(form.max_members) : undefined,
      inbounds: form.squad_type === 'internal' ? parseCsvList(form.inbounds) : undefined,
    });
  }

  return (
    <InfrastructurePageShell
      eyebrow={t('squads.eyebrow')}
      title={t('squads.title')}
      description={t('squads.description')}
      icon={Group}
      metrics={[
        {
          label: t('squads.metrics.internal'),
          value: formatCompactNumber(internalSquads.length),
          hint: t('squads.metrics.internalHint'),
          tone: 'info',
        },
        {
          label: t('squads.metrics.external'),
          value: formatCompactNumber(externalSquads.length),
          hint: t('squads.metrics.externalHint'),
          tone: 'success',
        },
        {
          label: t('squads.metrics.members'),
          value: formatCompactNumber(
            [...internalSquads, ...externalSquads].reduce(
              (sum, squad) => sum + (squad.memberCount ?? 0),
              0,
            ),
          ),
          hint: t('squads.metrics.membersHint'),
          tone: 'warning',
        },
        {
          label: t('squads.metrics.active'),
          value: formatCompactNumber(
            [...internalSquads, ...externalSquads].filter((squad) => squad.isActive).length,
          ),
          hint: t('squads.metrics.activeHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="space-y-6 xl:col-span-7">
          {[{
            title: t('squads.internalTitle'),
            rows: internalSquads,
          }, {
            title: t('squads.externalTitle'),
            rows: externalSquads,
          }].map((section) => (
            <article
              key={section.title}
              className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur"
            >
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {section.title}
              </h2>
              <div className="mt-5">
                {section.rows.length ? (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t('common.name')}</TableHead>
                        <TableHead>{t('common.members')}</TableHead>
                        <TableHead>{t('common.status')}</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {section.rows.map((squad) => (
                        <TableRow key={squad.uuid}>
                          <TableCell>
                            <div className="space-y-1">
                              <p className="font-display uppercase tracking-[0.14em] text-white">
                                {squad.name}
                              </p>
                              <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                                #{shortId(squad.uuid)}
                              </p>
                            </div>
                          </TableCell>
                          <TableCell>{squad.memberCount ?? 0}</TableCell>
                          <TableCell>
                            <InfrastructureStatusChip
                              label={squad.isActive ? t('common.active') : t('common.disabled')}
                              tone={squad.isActive ? 'success' : 'warning'}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <InfrastructureEmptyState label={t('squads.empty')} />
                )}
              </div>
            </article>
          ))}
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('squads.createTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('squads.createDescription')}
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
                placeholder="premium-users"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.type')}
              </span>
              <select
                value={form.squad_type}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    squad_type: event.target.value as SquadFormState['squad_type'],
                  }))
                }
                className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              >
                <option value="internal">internal</option>
                <option value="external">external</option>
              </select>
            </label>

            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.maxMembers')}
              </span>
              <Input
                type="number"
                min="1"
                value={form.max_members}
                onChange={(event) =>
                  setForm((current) => ({ ...current, max_members: event.target.value }))
                }
                placeholder={t('common.optional')}
              />
            </label>

            {form.squad_type === 'internal' ? (
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.inbounds')}
                </span>
                <Input
                  value={form.inbounds}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, inbounds: event.target.value }))
                  }
                  placeholder="uuid-1, uuid-2"
                />
              </label>
            ) : null}

            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.description')}
              </span>
              <Input
                value={form.description}
                onChange={(event) =>
                  setForm((current) => ({ ...current, description: event.target.value }))
                }
                placeholder={t('common.optional')}
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
              {t('squads.createAction')}
            </Button>
          </form>
        </section>
      </div>
    </InfrastructurePageShell>
  );
}

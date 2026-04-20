'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileStack, Plus } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { configProfilesApi } from '@/lib/api/infrastructure';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import { formatCompactNumber, shortId } from '@/features/infrastructure/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

interface ConfigProfileFormState {
  name: string;
  profile_type: string;
  content: string;
  description: string;
  is_default: boolean;
}

const EMPTY_FORM: ConfigProfileFormState = {
  name: '',
  profile_type: 'clash',
  content: '',
  description: '',
  is_default: false,
};

export function ConfigProfilesConsole() {
  const t = useTranslations('Infrastructure');
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ConfigProfileFormState>(EMPTY_FORM);
  const [feedback, setFeedback] = useState<string | null>(null);

  const profilesQuery = useQuery({
    queryKey: ['infrastructure', 'config-profiles'],
    queryFn: async () => {
      const response = await configProfilesApi.list();
      return response.data;
    },
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: configProfilesApi.create,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'config-profiles'] });
      setForm(EMPTY_FORM);
      setFeedback(t('configProfiles.createSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const profiles = profilesQuery.data ?? [];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    if (!form.name.trim() || !form.profile_type.trim() || !form.content.trim()) {
      setFeedback(t('common.validation.profileFormInvalid'));
      return;
    }

    await createMutation.mutateAsync({
      name: form.name.trim(),
      profile_type: form.profile_type.trim(),
      content: form.content,
      description: form.description.trim() || undefined,
      is_default: form.is_default,
    });
  }

  return (
    <InfrastructurePageShell
      eyebrow={t('configProfiles.eyebrow')}
      title={t('configProfiles.title')}
      description={t('configProfiles.description')}
      icon={FileStack}
      metrics={[
        {
          label: t('configProfiles.metrics.total'),
          value: formatCompactNumber(profiles.length),
          hint: t('configProfiles.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('configProfiles.metrics.defaults'),
          value: formatCompactNumber(profiles.filter((profile) => profile.isDefault).length),
          hint: t('configProfiles.metrics.defaultsHint'),
          tone: 'success',
        },
        {
          label: t('configProfiles.metrics.types'),
          value: formatCompactNumber(new Set(profiles.map((profile) => profile.profileType)).size),
          hint: t('configProfiles.metrics.typesHint'),
          tone: 'warning',
        },
        {
          label: t('configProfiles.metrics.described'),
          value: formatCompactNumber(profiles.filter((profile) => profile.description).length),
          hint: t('configProfiles.metrics.describedHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          {profilesQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : profiles.length === 0 ? (
            <InfrastructureEmptyState label={t('configProfiles.empty')} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.name')}</TableHead>
                  <TableHead>{t('common.type')}</TableHead>
                  <TableHead>{t('common.default')}</TableHead>
                  <TableHead>{t('common.description')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {profiles.map((profile) => (
                  <TableRow key={profile.uuid}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {profile.name}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          #{shortId(profile.uuid)}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{profile.profileType}</TableCell>
                    <TableCell>
                      {profile.isDefault ? (
                        <InfrastructureStatusChip label={t('common.default')} tone="success" />
                      ) : (
                        <InfrastructureStatusChip label={t('common.optionalShort')} tone="neutral" />
                      )}
                    </TableCell>
                    <TableCell>{profile.description ?? t('common.emptyShort')}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('configProfiles.createTitle')}
              </h2>
              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                {t('configProfiles.createDescription')}
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
                placeholder="Mobile Optimized"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.type')}
              </span>
              <Input
                value={form.profile_type}
                onChange={(event) =>
                  setForm((current) => ({ ...current, profile_type: event.target.value }))
                }
                placeholder="clash"
              />
            </label>

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
                placeholder="# Clash config content here"
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              />
            </label>

            <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
              <input
                type="checkbox"
                checked={form.is_default}
                onChange={(event) =>
                  setForm((current) => ({ ...current, is_default: event.target.checked }))
                }
              />
              <span className="text-sm font-mono text-foreground">{t('common.default')}</span>
            </label>

            <Button type="submit" magnetic={false} disabled={createMutation.isPending}>
              {createMutation.isPending ? t('common.saving') : t('configProfiles.createAction')}
            </Button>
          </form>
        </section>
      </div>
    </InfrastructurePageShell>
  );
}

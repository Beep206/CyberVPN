'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, Settings2, ShieldCheck } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { governanceApi } from '@/lib/api/governance';
import { GovernanceEmptyState } from '@/features/governance/components/governance-empty-state';
import { GovernanceJsonPreview } from '@/features/governance/components/governance-json-preview';
import { GovernancePageShell } from '@/features/governance/components/governance-page-shell';
import { GovernanceStatusChip } from '@/features/governance/components/governance-status-chip';
import {
  GOVERNANCE_ROLE_PERMISSION_MATRIX,
  getErrorMessage,
  humanizeToken,
  matchesSearch,
  settingFamily,
  summarizeJsonValue,
} from '@/features/governance/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

function defaultSettingValue() {
  return JSON.stringify({ enabled: true }, null, 2);
}

function parseJsonInput(value: string) {
  return JSON.parse(value);
}

export function PolicyConsole() {
  const t = useTranslations('Governance');
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [selectedSettingId, setSelectedSettingId] = useState<number | null>(null);
  const [editorMode, setEditorMode] = useState<'create' | 'update'>('create');
  const [editorKey, setEditorKey] = useState('');
  const [editorValue, setEditorValue] = useState(defaultSettingValue());
  const [editorDescription, setEditorDescription] = useState('');
  const [editorIsPublic, setEditorIsPublic] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const settingsQuery = useQuery({
    queryKey: ['governance', 'settings'],
    queryFn: async () => {
      const response = await governanceApi.getSettings();
      return response.data;
    },
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: (payload: {
      key: string;
      value: unknown;
      description: string | null;
      is_public: boolean;
    }) => governanceApi.createSetting(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['governance', 'settings'] });
      resetEditor();
      setFeedback(t('policy.createSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const updateMutation = useMutation({
    mutationFn: (payload: {
      id: number;
      value: unknown;
      description: string | null;
      is_public: boolean;
    }) =>
      governanceApi.updateSetting(payload.id, {
        value: payload.value,
        description: payload.description,
        is_public: payload.is_public,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['governance', 'settings'] });
      setFeedback(t('policy.updateSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const settings = settingsQuery.data ?? [];
  const filteredSettings = settings.filter((setting) =>
    matchesSearch(
      [setting.key, setting.description, setting.value, setting.isPublic],
      search,
    ),
  );
  const selectedSetting =
    filteredSettings.find((setting) => setting.id === selectedSettingId) ??
    filteredSettings[0] ??
    null;
  const publicCount = settings.filter((setting) => setting.isPublic).length;
  const describedCount = settings.filter((setting) => Boolean(setting.description)).length;
  const familyCount = new Set(settings.map((setting) => settingFamily(setting.key))).size;

  function resetEditor() {
    setEditorMode('create');
    setSelectedSettingId(null);
    setEditorKey('');
    setEditorValue(defaultSettingValue());
    setEditorDescription('');
    setEditorIsPublic(false);
  }

  function loadSettingIntoEditor(setting: (typeof settings)[number]) {
    setEditorMode('update');
    setSelectedSettingId(setting.id);
    setEditorKey(setting.key);
    setEditorValue(JSON.stringify(setting.value, null, 2));
    setEditorDescription(setting.description ?? '');
    setEditorIsPublic(setting.isPublic);
  }

  function submitEditor() {
    if (editorMode === 'create' && !editorKey.trim()) {
      setFeedback(t('common.validation.keyRequired'));
      return;
    }

    if (!editorValue.trim()) {
      setFeedback(t('common.validation.valueRequired'));
      return;
    }

    let parsedValue: unknown;

    try {
      parsedValue = parseJsonInput(editorValue);
    } catch {
      setFeedback(t('common.validation.jsonInvalid'));
      return;
    }

    if (editorMode === 'create') {
      createMutation.mutate({
        key: editorKey.trim(),
        value: parsedValue,
        description: editorDescription.trim() || null,
        is_public: editorIsPublic,
      });
      return;
    }

    if (!selectedSettingId) {
      setFeedback(t('policy.selectionRequired'));
      return;
    }

    updateMutation.mutate({
      id: selectedSettingId,
      value: parsedValue,
      description: editorDescription.trim() || null,
      is_public: editorIsPublic,
    });
  }

  return (
    <GovernancePageShell
      eyebrow={t('policy.eyebrow')}
      title={t('policy.title')}
      description={t('policy.description')}
      icon={Settings2}
      actions={
        <>
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={t('policy.searchPlaceholder')}
            className="w-[15rem]"
          />
          <Button
            type="button"
            variant="ghost"
            magnetic={false}
            onClick={() => {
              void queryClient.invalidateQueries({ queryKey: ['governance', 'settings'] });
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('common.refresh')}
          </Button>
        </>
      }
      metrics={[
        {
          label: t('policy.metrics.total'),
          value: String(settings.length),
          hint: t('policy.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('policy.metrics.public'),
          value: String(publicCount),
          hint: t('policy.metrics.publicHint'),
          tone: 'warning',
        },
        {
          label: t('policy.metrics.described'),
          value: String(describedCount),
          hint: t('policy.metrics.describedHint'),
          tone: 'success',
        },
        {
          label: t('policy.metrics.families'),
          value: String(familyCount),
          hint: t('policy.metrics.familiesHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="space-y-6 xl:col-span-7">
          {feedback ? (
            <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
              {feedback}
            </div>
          ) : null}

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('policy.registryTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('policy.registryDescription')}
            </p>

            <div className="mt-5">
              {settingsQuery.isLoading ? (
                <div className="grid gap-3">
                  {Array.from({ length: 5 }).map((_, index) => (
                    <div
                      key={index}
                      className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                    />
                  ))}
                </div>
              ) : filteredSettings.length === 0 ? (
                <GovernanceEmptyState label={t('policy.empty')} />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('common.key')}</TableHead>
                      <TableHead>{t('common.value')}</TableHead>
                      <TableHead>{t('common.status')}</TableHead>
                      <TableHead>{t('common.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredSettings.map((setting) => {
                      const isSelected = selectedSetting?.id === setting.id;

                      return (
                        <TableRow
                          key={setting.id}
                          className={isSelected ? 'border-l-2 border-l-neon-cyan bg-neon-cyan/5' : undefined}
                          onClick={() => setSelectedSettingId(setting.id)}
                        >
                          <TableCell>
                            <div className="space-y-1">
                              <p className="font-display uppercase tracking-[0.14em] text-white">
                                {setting.key}
                              </p>
                              <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                                {setting.description ?? t('common.none')}
                              </p>
                            </div>
                          </TableCell>
                          <TableCell className="max-w-[18rem]">
                            <span className="text-xs text-muted-foreground">
                              {summarizeJsonValue(setting.value)}
                            </span>
                          </TableCell>
                          <TableCell>
                            <GovernanceStatusChip
                              label={setting.isPublic ? t('common.public') : t('common.private')}
                              tone={setting.isPublic ? 'warning' : 'info'}
                            />
                          </TableCell>
                          <TableCell>
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              magnetic={false}
                              onClick={(event) => {
                                event.stopPropagation();
                                loadSettingIntoEditor(setting);
                              }}
                            >
                              {t('common.edit')}
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-cyan">
                <ShieldCheck className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.roleMatrixTitle')}
                </h2>
                <p className="mt-1 text-sm font-mono text-muted-foreground">
                  {t('policy.roleMatrixDescription')}
                </p>
              </div>
            </div>

            <div className="mt-5 grid gap-3">
              {GOVERNANCE_ROLE_PERMISSION_MATRIX.map((entry) => (
                <div
                  key={entry.role}
                  className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {entry.role}
                    </p>
                    <GovernanceStatusChip
                      label={String(entry.permissions.length)}
                      tone="info"
                    />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {entry.permissions.map((permission) => (
                      <GovernanceStatusChip
                        key={`${entry.role}-${permission}`}
                        label={humanizeToken(permission)}
                        tone="neutral"
                      />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="space-y-6 xl:col-span-5">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                  {t('policy.editorTitle')}
                </h2>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {t(`policy.editorDescription.${editorMode}`)}
                </p>
              </div>
              {editorMode === 'update' ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  magnetic={false}
                  onClick={() => resetEditor()}
                >
                  {t('policy.resetEditor')}
                </Button>
              ) : null}
            </div>

            <div className="mt-5 space-y-4">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.key')}
                </span>
                <Input
                  value={editorKey}
                  disabled={editorMode === 'update'}
                  onChange={(event) => setEditorKey(event.target.value)}
                  placeholder={t('policy.keyPlaceholder')}
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.description')}
                </span>
                <Input
                  value={editorDescription}
                  onChange={(event) => setEditorDescription(event.target.value)}
                  placeholder={t('policy.descriptionPlaceholder')}
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.value')}
                </span>
                <textarea
                  value={editorValue}
                  onChange={(event) => setEditorValue(event.target.value)}
                  placeholder={t('policy.valuePlaceholder')}
                  className="min-h-48 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm text-foreground outline-none"
                />
              </label>

              <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
                <input
                  type="checkbox"
                  checked={editorIsPublic}
                  onChange={(event) => setEditorIsPublic(event.target.checked)}
                  className="h-4 w-4 rounded border border-input bg-transparent"
                />
                <span className="text-sm font-mono text-foreground">
                  {t('policy.publicToggle')}
                </span>
              </label>

              <Button
                type="button"
                magnetic={false}
                disabled={createMutation.isPending || updateMutation.isPending}
                onClick={() => submitEditor()}
              >
                {editorMode === 'create' ? t('common.create') : t('common.update')}
              </Button>
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('policy.detailTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('policy.detailDescription')}
            </p>

            {selectedSetting ? (
              <div className="mt-5 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <GovernanceStatusChip
                    label={selectedSetting.isPublic ? t('common.public') : t('common.private')}
                    tone={selectedSetting.isPublic ? 'warning' : 'info'}
                  />
                  <GovernanceStatusChip
                    label={settingFamily(selectedSetting.key)}
                    tone="neutral"
                  />
                </div>
                <GovernanceJsonPreview value={selectedSetting.value} maxHeightClassName="max-h-[20rem]" />
              </div>
            ) : (
              <div className="mt-5">
                <GovernanceEmptyState label={t('policy.empty')} />
              </div>
            )}
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('policy.gapTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('policy.gapDescription')}
            </p>
          </article>
        </section>
      </div>
    </GovernancePageShell>
  );
}

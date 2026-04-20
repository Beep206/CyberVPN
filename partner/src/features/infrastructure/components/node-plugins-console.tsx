'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Blocks, CopyPlus, Play, Plus, Save, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { nodePluginsApi } from '@/lib/api/infrastructure';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import { JsonPreview } from '@/features/infrastructure/components/json-preview';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import {
  formatCompactNumber,
  humanizeToken,
  parseJsonObject,
  shortId,
  stringifyJson,
} from '@/features/infrastructure/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

export function NodePluginsConsole() {
  const t = useTranslations('Infrastructure');
  const queryClient = useQueryClient();
  const [newPluginName, setNewPluginName] = useState('');
  const [selectedPluginId, setSelectedPluginId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [pluginConfigText, setPluginConfigText] = useState('{}');
  const [commandText, setCommandText] = useState('{\n  "kind": "reload"\n}');
  const [targetNodesText, setTargetNodesText] = useState('{\n  "nodeUuids": []\n}');
  const [feedback, setFeedback] = useState<string | null>(null);

  const pluginsQuery = useQuery({
    queryKey: ['infrastructure', 'node-plugins'],
    queryFn: async () => {
      const response = await nodePluginsApi.list();
      return response.data;
    },
    staleTime: 30_000,
  });

  const torrentStatsQuery = useQuery({
    queryKey: ['infrastructure', 'node-plugins', 'torrent-stats'],
    queryFn: async () => {
      const response = await nodePluginsApi.getTorrentStats();
      return response.data;
    },
    staleTime: 30_000,
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: nodePluginsApi.create,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'node-plugins'] });
      setNewPluginName('');
      setFeedback(t('nodePlugins.createSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ uuid, payload }: { uuid: string; payload: Parameters<typeof nodePluginsApi.update>[1] }) =>
      nodePluginsApi.update(uuid, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'node-plugins'] });
      setFeedback(t('nodePlugins.updateSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (uuid: string) => nodePluginsApi.remove(uuid),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'node-plugins'] });
      setSelectedPluginId(null);
      setEditName('');
      setPluginConfigText('{}');
      setFeedback(t('nodePlugins.deleteSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const cloneMutation = useMutation({
    mutationFn: (cloneFromUuid: string) => nodePluginsApi.clone({ cloneFromUuid }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'node-plugins'] });
      setFeedback(t('nodePlugins.cloneSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const executeMutation = useMutation({
    mutationFn: nodePluginsApi.execute,
    onSuccess: () => {
      setFeedback(t('nodePlugins.executeSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const nodePlugins = pluginsQuery.data?.nodePlugins ?? [];
  const selectedPlugin =
    nodePlugins.find((plugin) => plugin.uuid === selectedPluginId) ?? null;
  const torrentStats = torrentStatsQuery.data?.stats;

  function selectPlugin(uuid: string) {
    const plugin = nodePlugins.find((item) => item.uuid === uuid);
    if (!plugin) return;

    setSelectedPluginId(plugin.uuid);
    setEditName(plugin.name);
    setPluginConfigText(stringifyJson(plugin.pluginConfig ?? {}));
    setFeedback(null);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    if (!newPluginName.trim()) {
      setFeedback(t('common.validation.nameRequired'));
      return;
    }

    await createMutation.mutateAsync({ name: newPluginName.trim() });
  }

  async function handleUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    if (!selectedPlugin) {
      setFeedback(t('nodePlugins.selectionRequired'));
      return;
    }

    await updateMutation.mutateAsync({
      uuid: selectedPlugin.uuid,
      payload: {
        name: editName.trim() || undefined,
        pluginConfig: parseJsonObject(pluginConfigText),
      },
    });
  }

  async function handleExecute(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    await executeMutation.mutateAsync({
      command: parseJsonObject(commandText),
      targetNodes: parseJsonObject(targetNodesText),
    });
  }

  return (
    <InfrastructurePageShell
      eyebrow={t('nodePlugins.eyebrow')}
      title={t('nodePlugins.title')}
      description={t('nodePlugins.description')}
      icon={Blocks}
      metrics={[
        {
          label: t('nodePlugins.metrics.total'),
          value: formatCompactNumber(nodePlugins.length),
          hint: t('nodePlugins.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('nodePlugins.metrics.reports'),
          value: formatCompactNumber(torrentStats?.totalReports),
          hint: t('nodePlugins.metrics.reportsHint'),
          tone: 'warning',
        },
        {
          label: t('nodePlugins.metrics.nodes'),
          value: formatCompactNumber(torrentStats?.distinctNodes),
          hint: t('nodePlugins.metrics.nodesHint'),
          tone: 'success',
        },
        {
          label: t('nodePlugins.metrics.users'),
          value: formatCompactNumber(torrentStats?.distinctUsers),
          hint: t('nodePlugins.metrics.usersHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          {pluginsQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : nodePlugins.length === 0 ? (
            <InfrastructureEmptyState label={t('nodePlugins.empty')} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.name')}</TableHead>
                  <TableHead>{t('common.order')}</TableHead>
                  <TableHead>{t('common.modules')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {nodePlugins.map((plugin) => (
                  <TableRow key={plugin.uuid}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {plugin.name}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          #{shortId(plugin.uuid)}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{plugin.viewPosition}</TableCell>
                    <TableCell>
                      <InfrastructureStatusChip
                        label={humanizeToken(
                          Object.keys(plugin.pluginConfig ?? {}).join(', ') ||
                            t('common.emptyShort'),
                        )}
                        tone="info"
                        className="max-w-[18rem] overflow-hidden text-ellipsis whitespace-nowrap"
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          magnetic={false}
                          onClick={() => selectPlugin(plugin.uuid)}
                        >
                          <Save className="mr-2 h-4 w-4" />
                          {t('common.edit')}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          magnetic={false}
                          disabled={cloneMutation.isPending}
                          onClick={() => cloneMutation.mutate(plugin.uuid)}
                        >
                          <CopyPlus className="mr-2 h-4 w-4" />
                          {t('common.clone')}
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          magnetic={false}
                          disabled={deleteMutation.isPending}
                          onClick={() => deleteMutation.mutate(plugin.uuid)}
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
        </section>

        <section className="space-y-6 xl:col-span-5">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('nodePlugins.createTitle')}
            </h2>
            <form className="mt-5 space-y-4" onSubmit={handleCreate}>
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.name')}
                </span>
                <Input
                  value={newPluginName}
                  onChange={(event) => setNewPluginName(event.target.value)}
                  placeholder="torrent-blocker"
                />
              </label>
              <Button type="submit" magnetic={false} disabled={createMutation.isPending}>
                <Plus className="mr-2 h-4 w-4" />
                {t('nodePlugins.createAction')}
              </Button>
            </form>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('nodePlugins.editTitle')}
            </h2>
            {feedback ? (
              <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
                {feedback}
              </div>
            ) : null}
            {selectedPlugin ? (
              <form className="mt-5 space-y-4" onSubmit={handleUpdate}>
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.name')}
                  </span>
                  <Input
                    value={editName}
                    onChange={(event) => setEditName(event.target.value)}
                  />
                </label>
                <label className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.pluginConfig')}
                  </span>
                  <textarea
                    value={pluginConfigText}
                    onChange={(event) => setPluginConfigText(event.target.value)}
                    rows={10}
                    className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  />
                </label>
                <Button type="submit" magnetic={false} disabled={updateMutation.isPending}>
                  {t('common.save')}
                </Button>
              </form>
            ) : (
              <InfrastructureEmptyState label={t('nodePlugins.selectionEmpty')} />
            )}
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('nodePlugins.executeTitle')}
            </h2>
            <form className="mt-5 space-y-4" onSubmit={handleExecute}>
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.command')}
                </span>
                <textarea
                  value={commandText}
                  onChange={(event) => setCommandText(event.target.value)}
                  rows={5}
                  className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </label>
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.targetNodes')}
                </span>
                <textarea
                  value={targetNodesText}
                  onChange={(event) => setTargetNodesText(event.target.value)}
                  rows={5}
                  className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </label>
              <Button type="submit" magnetic={false} disabled={executeMutation.isPending}>
                <Play className="mr-2 h-4 w-4" />
                {t('nodePlugins.executeAction')}
              </Button>
            </form>
          </article>

          {selectedPlugin ? (
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('nodePlugins.snapshotTitle')}
              </h2>
              <div className="mt-5">
                <JsonPreview value={selectedPlugin.pluginConfig ?? {}} maxHeightClassName="max-h-80" />
              </div>
            </article>
          ) : null}
        </section>
      </div>
    </InfrastructurePageShell>
  );
}

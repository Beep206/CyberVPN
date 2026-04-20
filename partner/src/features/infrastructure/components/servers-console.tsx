'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { HardDriveDownload, PencilLine, Plus, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { serversApi } from '@/lib/api/servers';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import {
  formatBytes,
  formatCompactNumber,
  humanizeToken,
  shortId,
} from '@/features/infrastructure/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

interface ServerFormState {
  name: string;
  address: string;
  port: string;
}

const EMPTY_FORM: ServerFormState = {
  name: '',
  address: '',
  port: '443',
};

function toneForServerStatus(status: string) {
  if (status === 'online') return 'success' as const;
  if (status === 'warning') return 'warning' as const;
  if (status === 'maintenance') return 'info' as const;
  return 'danger' as const;
}

export function ServersConsole() {
  const t = useTranslations('Infrastructure');
  const queryClient = useQueryClient();
  const [form, setForm] = useState<ServerFormState>(EMPTY_FORM);
  const [selectedServerId, setSelectedServerId] = useState<string | null>(null);
  const [mode, setMode] = useState<'create' | 'edit'>('create');
  const [feedback, setFeedback] = useState<string | null>(null);

  const serversQuery = useQuery({
    queryKey: ['infrastructure', 'servers'],
    queryFn: async () => {
      const response = await serversApi.list();
      return response.data;
    },
    staleTime: 30_000,
  });

  const serverStatsQuery = useQuery({
    queryKey: ['infrastructure', 'server-stats'],
    queryFn: async () => {
      const response = await serversApi.getStats();
      return response.data;
    },
    staleTime: 15_000,
  });

  const createMutation = useMutation({
    mutationFn: serversApi.create,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'servers'] });
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'server-stats'] });
      setForm(EMPTY_FORM);
      setMode('create');
      setSelectedServerId(null);
      setFeedback(t('servers.createSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ uuid, payload }: { uuid: string; payload: Parameters<typeof serversApi.update>[1] }) =>
      serversApi.update(uuid, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'servers'] });
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'server-stats'] });
      setFeedback(t('servers.updateSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (uuid: string) => serversApi.remove(uuid),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'servers'] });
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'server-stats'] });
      setForm(EMPTY_FORM);
      setMode('create');
      setSelectedServerId(null);
      setFeedback(t('servers.deleteSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const servers = serversQuery.data ?? [];
  const selectedServer = servers.find((server) => server.uuid === selectedServerId) ?? null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    const port = Number(form.port);
    if (!form.name.trim() || !form.address.trim() || !Number.isFinite(port) || port <= 0) {
      setFeedback(t('common.validation.serverFormInvalid'));
      return;
    }

    const payload = {
      name: form.name.trim(),
      address: form.address.trim(),
      port,
    };

    if (mode === 'edit' && selectedServer) {
      await updateMutation.mutateAsync({ uuid: selectedServer.uuid, payload });
      return;
    }

    await createMutation.mutateAsync(payload);
  }

  function handleEditSelection(serverId: string) {
    const server = servers.find((item) => item.uuid === serverId);
    if (!server) return;

    setSelectedServerId(server.uuid);
    setMode('edit');
    setFeedback(null);
    setForm({
      name: server.name,
      address: server.address,
      port: String(server.port),
    });
  }

  return (
    <InfrastructurePageShell
      eyebrow={t('servers.eyebrow')}
      title={t('servers.title')}
      description={t('servers.description')}
      icon={HardDriveDownload}
      actions={
        <Button
          magnetic={false}
          variant="ghost"
          onClick={() => {
            setMode('create');
            setSelectedServerId(null);
            setForm(EMPTY_FORM);
            setFeedback(null);
          }}
        >
          <Plus className="mr-2 h-4 w-4" />
          {t('servers.createAction')}
        </Button>
      }
      metrics={[
        {
          label: t('servers.metrics.total'),
          value: formatCompactNumber(serverStatsQuery.data?.total),
          hint: t('servers.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('servers.metrics.online'),
          value: formatCompactNumber(serverStatsQuery.data?.online),
          hint: t('servers.metrics.onlineHint'),
          tone: 'success',
        },
        {
          label: t('servers.metrics.warning'),
          value: formatCompactNumber(serverStatsQuery.data?.warning),
          hint: t('servers.metrics.warningHint'),
          tone: 'warning',
        },
        {
          label: t('servers.metrics.traffic'),
          value: formatBytes(
            servers.reduce((sum, server) => sum + server.traffic_used_bytes, 0),
          ),
          hint: t('servers.metrics.trafficHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
          {serversQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : servers.length === 0 ? (
            <InfrastructureEmptyState label={t('servers.empty')} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.name')}</TableHead>
                  <TableHead>{t('common.address')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('common.users')}</TableHead>
                  <TableHead>{t('common.traffic')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {servers.map((server) => (
                  <TableRow key={server.uuid}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {server.name}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          #{shortId(server.uuid)} / {server.country_code ?? '--'}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{server.address}:{server.port}</TableCell>
                    <TableCell>
                      <InfrastructureStatusChip
                        label={humanizeToken(server.status)}
                        tone={toneForServerStatus(server.status)}
                      />
                    </TableCell>
                    <TableCell>{server.users_online}</TableCell>
                    <TableCell>{formatBytes(server.traffic_used_bytes)}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          magnetic={false}
                          onClick={() => handleEditSelection(server.uuid)}
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
                          onClick={() => deleteMutation.mutate(server.uuid)}
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

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-4">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {mode === 'edit' ? t('servers.editTitle') : t('servers.createTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {mode === 'edit' ? t('servers.editDescription') : t('servers.createDescription')}
          </p>

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
                placeholder="Frankfurt DE-1"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.address')}
              </span>
              <Input
                value={form.address}
                onChange={(event) =>
                  setForm((current) => ({ ...current, address: event.target.value }))
                }
                placeholder="frankfurt-01.example.com"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('common.port')}
              </span>
              <Input
                type="number"
                min="1"
                max="65535"
                value={form.port}
                onChange={(event) =>
                  setForm((current) => ({ ...current, port: event.target.value }))
                }
              />
            </label>

            <div className="flex flex-wrap gap-3">
              <Button
                type="submit"
                magnetic={false}
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {mode === 'edit' ? t('common.save') : t('servers.createAction')}
              </Button>
              {mode === 'edit' ? (
                <Button
                  type="button"
                  variant="ghost"
                  magnetic={false}
                  onClick={() => {
                    setMode('create');
                    setSelectedServerId(null);
                    setForm(EMPTY_FORM);
                    setFeedback(null);
                  }}
                >
                  {t('common.cancel')}
                </Button>
              ) : null}
            </div>
          </form>

          {selectedServer ? (
            <div className="mt-6 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('servers.selectedServer')}
              </p>
              <p className="mt-2 text-lg font-display tracking-[0.14em] text-white">
                {selectedServer.name}
              </p>
              <p className="mt-2 text-sm font-mono text-muted-foreground">
                {selectedServer.vpn_protocol ?? '--'} / {selectedServer.xray_version ?? '--'}
              </p>
            </div>
          ) : null}
        </section>
      </div>
    </InfrastructurePageShell>
  );
}

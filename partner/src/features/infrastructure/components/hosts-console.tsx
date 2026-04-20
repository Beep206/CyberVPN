'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { GlobeLock, PencilLine, Plus, Trash2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { hostsApi } from '@/lib/api/infrastructure';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import {
  formatCompactNumber,
  parseCsvList,
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

interface HostFormState {
  name: string;
  address: string;
  port: string;
  sni: string;
  host_header: string;
  path: string;
  alpn: string;
  is_disabled: boolean;
}

const EMPTY_FORM: HostFormState = {
  name: '',
  address: '',
  port: '443',
  sni: '',
  host_header: '',
  path: '',
  alpn: '',
  is_disabled: false,
};

export function HostsConsole() {
  const t = useTranslations('Infrastructure');
  const queryClient = useQueryClient();
  const [form, setForm] = useState<HostFormState>(EMPTY_FORM);
  const [selectedHostId, setSelectedHostId] = useState<string | null>(null);
  const [mode, setMode] = useState<'create' | 'edit'>('create');
  const [feedback, setFeedback] = useState<string | null>(null);

  const hostsQuery = useQuery({
    queryKey: ['infrastructure', 'hosts'],
    queryFn: async () => {
      const response = await hostsApi.list();
      return response.data;
    },
    staleTime: 30_000,
  });

  const createMutation = useMutation({
    mutationFn: hostsApi.create,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'hosts'] });
      setForm(EMPTY_FORM);
      setMode('create');
      setSelectedHostId(null);
      setFeedback(t('hosts.createSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ uuid, payload }: { uuid: string; payload: Parameters<typeof hostsApi.update>[1] }) =>
      hostsApi.update(uuid, payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'hosts'] });
      setFeedback(t('hosts.updateSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (uuid: string) => hostsApi.remove(uuid),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'hosts'] });
      setForm(EMPTY_FORM);
      setMode('create');
      setSelectedHostId(null);
      setFeedback(t('hosts.deleteSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const hosts = hostsQuery.data ?? [];
  const selectedHost = hosts.find((host) => host.uuid === selectedHostId) ?? null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    const port = Number(form.port);
    if (!form.name.trim() || !form.address.trim() || !Number.isFinite(port) || port <= 0) {
      setFeedback(t('common.validation.hostFormInvalid'));
      return;
    }

    const payload = {
      name: form.name.trim(),
      address: form.address.trim(),
      port,
      sni: form.sni.trim() || undefined,
      host_header: form.host_header.trim() || undefined,
      path: form.path.trim() || undefined,
      alpn: parseCsvList(form.alpn),
      is_disabled: form.is_disabled,
    };

    if (mode === 'edit' && selectedHost) {
      await updateMutation.mutateAsync({ uuid: selectedHost.uuid, payload });
      return;
    }

    await createMutation.mutateAsync(payload);
  }

  function handleEditSelection(hostId: string) {
    const host = hosts.find((item) => item.uuid === hostId);
    if (!host) return;

    setSelectedHostId(host.uuid);
    setMode('edit');
    setFeedback(null);
    setForm({
      name: host.name,
      address: host.address,
      port: String(host.port),
      sni: host.sni ?? '',
      host_header: host.host_header ?? '',
      path: host.path ?? '',
      alpn: host.alpn?.join(', ') ?? '',
      is_disabled: host.is_disabled,
    });
  }

  return (
    <InfrastructurePageShell
      eyebrow={t('hosts.eyebrow')}
      title={t('hosts.title')}
      description={t('hosts.description')}
      icon={GlobeLock}
      actions={
        <Button
          magnetic={false}
          variant="ghost"
          onClick={() => {
            setMode('create');
            setSelectedHostId(null);
            setForm(EMPTY_FORM);
            setFeedback(null);
          }}
        >
          <Plus className="mr-2 h-4 w-4" />
          {t('hosts.createAction')}
        </Button>
      }
      metrics={[
        {
          label: t('hosts.metrics.total'),
          value: formatCompactNumber(hosts.length),
          hint: t('hosts.metrics.totalHint'),
          tone: 'info',
        },
        {
          label: t('hosts.metrics.disabled'),
          value: formatCompactNumber(hosts.filter((host) => host.is_disabled).length),
          hint: t('hosts.metrics.disabledHint'),
          tone: 'warning',
        },
        {
          label: t('hosts.metrics.withSni'),
          value: formatCompactNumber(hosts.filter((host) => host.sni).length),
          hint: t('hosts.metrics.withSniHint'),
          tone: 'success',
        },
        {
          label: t('hosts.metrics.withPath'),
          value: formatCompactNumber(hosts.filter((host) => host.path).length),
          hint: t('hosts.metrics.withPathHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-8">
          {hostsQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 5 }).map((_, index) => (
                <div
                  key={index}
                  className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : hosts.length === 0 ? (
            <InfrastructureEmptyState label={t('hosts.empty')} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.name')}</TableHead>
                  <TableHead>{t('common.address')}</TableHead>
                  <TableHead>{t('common.sni')}</TableHead>
                  <TableHead>{t('common.path')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {hosts.map((host) => (
                  <TableRow key={host.uuid}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {host.name}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          #{shortId(host.uuid)}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{host.address}:{host.port}</TableCell>
                    <TableCell>{host.sni ?? t('common.emptyShort')}</TableCell>
                    <TableCell>{host.path ?? t('common.emptyShort')}</TableCell>
                    <TableCell>
                      <InfrastructureStatusChip
                        label={host.is_disabled ? t('common.disabled') : t('common.active')}
                        tone={host.is_disabled ? 'warning' : 'success'}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          magnetic={false}
                          onClick={() => handleEditSelection(host.uuid)}
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
                          onClick={() => deleteMutation.mutate(host.uuid)}
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
            {mode === 'edit' ? t('hosts.editTitle') : t('hosts.createTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {mode === 'edit' ? t('hosts.editDescription') : t('hosts.createDescription')}
          </p>

          {feedback ? (
            <div className="mt-5 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
              {feedback}
            </div>
          ) : null}

          <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
            {[
              ['name', t('common.name'), 'edge-germany-primary'],
              ['address', t('common.address'), 'de-edge-01.example.com'],
              ['port', t('common.port'), '443'],
              ['sni', t('common.sni'), 'cloudflare.com'],
              ['host_header', t('common.hostHeader'), 'cloudflare.com'],
              ['path', t('common.path'), '/ws'],
              ['alpn', t('common.alpn'), 'h2, http/1.1'],
            ].map(([key, label, placeholder]) => (
              <label key={key} className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {label}
                </span>
                <Input
                  type={key === 'port' ? 'number' : 'text'}
                  min={key === 'port' ? '1' : undefined}
                  max={key === 'port' ? '65535' : undefined}
                  value={form[key as keyof HostFormState] as string | number}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      [key]: event.target.value,
                    }))
                  }
                  placeholder={placeholder}
                />
              </label>
            ))}

            <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
              <input
                type="checkbox"
                checked={form.is_disabled}
                onChange={(event) =>
                  setForm((current) => ({ ...current, is_disabled: event.target.checked }))
                }
              />
              <span className="text-sm font-mono text-foreground">{t('common.disabled')}</span>
            </label>

            <div className="flex flex-wrap gap-3">
              <Button
                type="submit"
                magnetic={false}
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {mode === 'edit' ? t('common.save') : t('hosts.createAction')}
              </Button>
              {mode === 'edit' ? (
                <Button
                  type="button"
                  variant="ghost"
                  magnetic={false}
                  onClick={() => {
                    setMode('create');
                    setSelectedHostId(null);
                    setForm(EMPTY_FORM);
                    setFeedback(null);
                  }}
                >
                  {t('common.cancel')}
                </Button>
              ) : null}
            </div>
          </form>

          {selectedHost ? (
            <div className="mt-6 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('hosts.selectedHost')}
              </p>
              <p className="mt-2 text-lg font-display tracking-[0.14em] text-white">
                {selectedHost.name}
              </p>
              <p className="mt-2 text-sm font-mono text-muted-foreground">
                {selectedHost.alpn?.join(', ') || t('common.emptyShort')}
              </p>
            </div>
          ) : null}
        </section>
      </div>
    </InfrastructurePageShell>
  );
}

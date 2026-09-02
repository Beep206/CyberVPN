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
import { formatCompactNumber, parseCsvList, shortId } from '@/features/infrastructure/lib/formatting';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/organisms/table';

type HostUpdate = Parameters<typeof hostsApi.update>[1];
type HostRecord = Awaited<ReturnType<typeof hostsApi.list>>['data'][number];

const ALPN_VALUES = ['h3', 'h2', 'http/1.1', 'h2,http/1.1', 'h3,h2,http/1.1', 'h3,h2'] as const;
const SECURITY_LAYER_VALUES = ['DEFAULT', 'TLS', 'NONE'] as const;
const MIHOMO_IP_VALUES = ['dual', 'ipv4', 'ipv6', 'ipv4-prefer', 'ipv6-prefer'] as const;
const SUBSCRIPTION_TYPE_VALUES = ['XRAY_JSON', 'XRAY_BASE64', 'MIHOMO', 'STASH', 'CLASH', 'SINGBOX'] as const;

interface HostFormState {
  remark: string;
  address: string;
  port: string;
  path: string;
  sni: string;
  host: string;
  alpn: string;
  fingerprint: string;
  configProfileUuid: string;
  configProfileInboundUuid: string;
  securityLayer: string;
  serverDescription: string;
  tags: string;
  pinnedPeerCertSha256: string;
  verifyPeerCertByName: string;
  vlessRouteId: string;
  mihomoIpVersion: string;
  nodes: string;
  xrayJsonTemplateUuid: string;
  excludeFromSubscriptionTypes: string;
  internalSquadsMode: string;
  internalSquads: string;
  xhttpExtraParams: string;
  muxParams: string;
  sockoptParams: string;
  finalMask: string;
  isDisabled: boolean;
  isHidden: boolean;
  overrideSniFromAddress: boolean;
  keepSniBlank: boolean;
  shuffleHost: boolean;
  mihomoX25519: boolean;
}

interface Feedback {
  message: string;
  tone: 'error' | 'info' | 'success';
}

function stringifyJson(value: unknown): string {
  return value == null ? '' : JSON.stringify(value, null, 2);
}

function toForm(host: HostRecord): HostFormState {
  return {
    remark: host.remark,
    address: host.address,
    port: String(host.port),
    path: host.path ?? '',
    sni: host.sni ?? '',
    host: host.host ?? '',
    alpn: host.alpn ?? '',
    fingerprint: host.fingerprint ?? '',
    configProfileUuid: host.inbound.configProfileUuid ?? '',
    configProfileInboundUuid: host.inbound.configProfileInboundUuid ?? '',
    securityLayer: host.securityLayer,
    serverDescription: host.serverDescription ?? '',
    tags: host.tags?.join(', ') ?? '',
    pinnedPeerCertSha256: host.pinnedPeerCertSha256 ?? '',
    verifyPeerCertByName: host.verifyPeerCertByName ?? '',
    vlessRouteId: host.vlessRouteId == null ? '' : String(host.vlessRouteId),
    mihomoIpVersion: host.mihomoIpVersion ?? '',
    nodes: host.nodes.join(', '),
    xrayJsonTemplateUuid: host.xrayJsonTemplateUuid ?? '',
    excludeFromSubscriptionTypes: host.excludeFromSubscriptionTypes.join(', '),
    internalSquadsMode: host.internalSquads.mode,
    internalSquads: host.internalSquads.squads.join(', '),
    xhttpExtraParams: stringifyJson(host.xhttpExtraParams),
    muxParams: stringifyJson(host.muxParams),
    sockoptParams: stringifyJson(host.sockoptParams),
    finalMask: stringifyJson(host.finalMask),
    isDisabled: host.isDisabled,
    isHidden: host.isHidden,
    overrideSniFromAddress: host.overrideSniFromAddress,
    keepSniBlank: host.keepSniBlank,
    shuffleHost: host.shuffleHost,
    mihomoX25519: host.mihomoX25519,
  };
}

function isAlpn(value: string): value is NonNullable<HostUpdate['alpn']> {
  return ALPN_VALUES.some((candidate) => candidate === value);
}

function isSecurityLayer(value: string): value is NonNullable<HostUpdate['securityLayer']> {
  return SECURITY_LAYER_VALUES.some((candidate) => candidate === value);
}

function isMihomoIpVersion(value: string): value is NonNullable<HostUpdate['mihomoIpVersion']> {
  return MIHOMO_IP_VALUES.some((candidate) => candidate === value);
}

function isSubscriptionType(value: string): value is NonNullable<HostUpdate['excludeFromSubscriptionTypes']>[number] {
  return SUBSCRIPTION_TYPE_VALUES.some((candidate) => candidate === value);
}

function parseJsonField(value: string): unknown | null {
  return value.trim() ? JSON.parse(value) : null;
}

function buildUpdatePayload(form: HostFormState): HostUpdate {
  const port = Number(form.port);
  const vlessRouteId = form.vlessRouteId.trim() ? Number(form.vlessRouteId) : null;
  const alpn = form.alpn === '' ? null : form.alpn;
  const mihomoIpVersion = form.mihomoIpVersion === '' ? null : form.mihomoIpVersion;

  if (!Number.isSafeInteger(port) || port < 1 || port > 65_535) throw new Error('invalid-port');
  if (vlessRouteId != null && (!Number.isInteger(vlessRouteId) || vlessRouteId < 0 || vlessRouteId > 65_535)) throw new Error('invalid-vless-route');
  if (alpn != null && !isAlpn(alpn)) throw new Error('invalid-alpn');
  if (!isSecurityLayer(form.securityLayer)) throw new Error('invalid-security-layer');
  if (mihomoIpVersion != null && !isMihomoIpVersion(mihomoIpVersion)) throw new Error('invalid-mihomo-ip-version');

  const configProfileUuid = form.configProfileUuid.trim();
  const configProfileInboundUuid = form.configProfileInboundUuid.trim();
  if (Boolean(configProfileUuid) !== Boolean(configProfileInboundUuid)) throw new Error('invalid-inbound');

  const excludedTypes = parseCsvList(form.excludeFromSubscriptionTypes);
  if (!excludedTypes.every(isSubscriptionType)) throw new Error('invalid-subscription-types');

  return {
    remark: form.remark.trim(),
    address: form.address.trim(),
    port,
    path: parseCsvList(form.path),
    sni: parseCsvList(form.sni),
    host: parseCsvList(form.host),
    alpn,
    fingerprint: parseCsvList(form.fingerprint),
    inbound: configProfileUuid && configProfileInboundUuid ? { configProfileUuid, configProfileInboundUuid } : undefined,
    securityLayer: form.securityLayer,
    serverDescription: form.serverDescription.trim() || null,
    tags: parseCsvList(form.tags),
    pinnedPeerCertSha256: parseCsvList(form.pinnedPeerCertSha256),
    verifyPeerCertByName: parseCsvList(form.verifyPeerCertByName),
    vlessRouteId,
    mihomoIpVersion,
    nodes: parseCsvList(form.nodes),
    xrayJsonTemplateUuid: form.xrayJsonTemplateUuid.trim() || null,
    excludeFromSubscriptionTypes: excludedTypes,
    internalSquads: { mode: form.internalSquadsMode, squads: parseCsvList(form.internalSquads) },
    xhttpExtraParams: parseJsonField(form.xhttpExtraParams),
    muxParams: parseJsonField(form.muxParams),
    sockoptParams: parseJsonField(form.sockoptParams),
    finalMask: parseJsonField(form.finalMask),
    isDisabled: form.isDisabled,
    isHidden: form.isHidden,
    overrideSniFromAddress: form.overrideSniFromAddress,
    keepSniBlank: form.keepSniBlank,
    shuffleHost: form.shuffleHost,
    mihomoX25519: form.mihomoX25519,
  };
}

export function HostsConsole() {
  const t = useTranslations('Infrastructure');
  const queryClient = useQueryClient();
  const [form, setForm] = useState<HostFormState | null>(null);
  const [selectedHostId, setSelectedHostId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const hostsQuery = useQuery({
    queryKey: ['infrastructure', 'hosts'],
    queryFn: async () => (await hostsApi.list()).data,
    staleTime: 30_000,
    retry: false,
  });

  const updateMutation = useMutation({
    mutationFn: ({ uuid, payload }: { uuid: string; payload: HostUpdate }) => hostsApi.update(uuid, payload),
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'hosts'] });
      setFeedback({
        message: response.status === 202 ? t('hosts.updatePending') : t('hosts.updateSuccess'),
        tone: response.status === 202 ? 'info' : 'success',
      });
    },
    onError: (error) => setFeedback({
      message: error instanceof Error ? error.message : t('common.actionFailed'),
      tone: 'error',
    }),
  });

  const deleteMutation = useMutation({
    mutationFn: (uuid: string) => hostsApi.remove(uuid),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'hosts'] });
      setForm(null);
      setSelectedHostId(null);
      setFeedback({ message: t('hosts.deleteSuccess'), tone: 'success' });
    },
    onError: (error) => setFeedback({
      message: error instanceof Error ? error.message : t('common.actionFailed'),
      tone: 'error',
    }),
  });

  const hosts = hostsQuery.data ?? [];
  const selectedHost = hosts.find((host) => host.uuid === selectedHostId) ?? null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    if (!selectedHost || !form || !form.remark.trim() || !form.address.trim()) {
      setFeedback({ message: t('common.validation.hostFormInvalid'), tone: 'error' });
      return;
    }
    let payload: HostUpdate;
    try {
      payload = buildUpdatePayload(form);
    } catch (error) {
      setFeedback({
        message: error instanceof SyntaxError ? t('hosts.validation.jsonInvalid') : t('common.validation.hostFormInvalid'),
        tone: 'error',
      });
      return;
    }
    await updateMutation.mutateAsync({ uuid: selectedHost.uuid, payload }).catch(() => undefined);
  }

  function handleEditSelection(host: HostRecord) {
    setSelectedHostId(host.uuid);
    setForm(toForm(host));
    setFeedback(null);
  }

  return (
    <InfrastructurePageShell
      eyebrow={t('hosts.eyebrow')}
      title={t('hosts.title')}
      description={t('hosts.description')}
      icon={GlobeLock}
      actions={(
        <Button magnetic={false} variant="ghost" disabled title={t('hosts.createUnavailable')}>
          <Plus className="mr-2 h-4 w-4" />
          {t('hosts.createAction')}
        </Button>
      )}
      metrics={[
        { label: t('hosts.metrics.total'), value: formatCompactNumber(hosts.length), hint: t('hosts.metrics.totalHint'), tone: 'info' },
        { label: t('hosts.metrics.disabled'), value: formatCompactNumber(hosts.filter((host) => host.isDisabled).length), hint: t('hosts.metrics.disabledHint'), tone: 'warning' },
        { label: t('hosts.metrics.withSni'), value: formatCompactNumber(hosts.filter((host) => host.sni).length), hint: t('hosts.metrics.withSniHint'), tone: 'success' },
        { label: t('hosts.metrics.withPath'), value: formatCompactNumber(hosts.filter((host) => host.path).length), hint: t('hosts.metrics.withPathHint'), tone: 'neutral' },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          {hostsQuery.isLoading ? (
            <div role="status" className="grid gap-3" aria-label={t('common.loading')}>
              {Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-16 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />)}
            </div>
          ) : hostsQuery.isError ? (
            <div role="alert" className="rounded-2xl border border-neon-pink/25 bg-neon-pink/10 p-5 text-sm font-mono text-neon-pink">
              <p>{t('hosts.loadFailed')}</p>
              <Button type="button" variant="ghost" magnetic={false} onClick={() => void hostsQuery.refetch()}>{t('common.retry')}</Button>
            </div>
          ) : hosts.length === 0 ? (
            <InfrastructureEmptyState label={t('hosts.empty')} />
          ) : (
            <Table>
              <TableHeader><TableRow>
                <TableHead>{t('common.name')}</TableHead><TableHead>{t('common.address')}</TableHead><TableHead>{t('common.sni')}</TableHead><TableHead>{t('common.path')}</TableHead><TableHead>{t('common.status')}</TableHead><TableHead>{t('common.actions')}</TableHead>
              </TableRow></TableHeader>
              <TableBody>
                {hosts.map((host) => (
                  <TableRow key={host.uuid}>
                    <TableCell><div className="space-y-1"><p className="font-display uppercase tracking-[0.14em] text-white">{host.remark}</p><p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">#{shortId(host.uuid)}</p></div></TableCell>
                    <TableCell>{host.address}:{host.port}</TableCell>
                    <TableCell>{host.sni ?? t('common.emptyShort')}</TableCell>
                    <TableCell>{host.path ?? t('common.emptyShort')}</TableCell>
                    <TableCell><InfrastructureStatusChip label={host.isDisabled ? t('common.disabled') : t('common.active')} tone={host.isDisabled ? 'warning' : 'success'} /></TableCell>
                    <TableCell><div className="flex flex-wrap gap-2">
                      <Button type="button" size="sm" variant="ghost" magnetic={false} onClick={() => handleEditSelection(host)}><PencilLine className="mr-2 h-4 w-4" />{t('common.edit')}</Button>
                      <Button type="button" size="sm" variant="ghost" magnetic={false} disabled={deleteMutation.isPending} onClick={() => deleteMutation.mutate(host.uuid)}><Trash2 className="mr-2 h-4 w-4" />{t('common.delete')}</Button>
                    </div></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">{selectedHost ? t('hosts.editTitle') : t('hosts.createUnavailableTitle')}</h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">{selectedHost ? t('hosts.editDescription') : t('hosts.createUnavailable')}</p>
          {feedback ? <div role={feedback.tone === 'error' ? 'alert' : 'status'} className="mt-5 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">{feedback.message}</div> : null}

          {selectedHost && form ? (
            <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
              {[
                ['remark', t('hosts.fields.remark'), 'edge-germany-primary'], ['address', t('common.address'), 'de-edge-01.example.com'], ['port', t('common.port'), '443'], ['path', t('common.path'), '/ws, /xhttp'], ['sni', t('common.sni'), 'cloudflare.com'], ['host', t('common.hostHeader'), 'cloudflare.com'], ['fingerprint', t('hosts.fields.fingerprint'), 'chrome'], ['configProfileUuid', t('hosts.fields.configProfileUuid'), t('common.optional')], ['configProfileInboundUuid', t('hosts.fields.configProfileInboundUuid'), t('common.optional')], ['serverDescription', t('hosts.fields.serverDescription'), t('common.optional')], ['tags', t('hosts.fields.tags'), 'EDGE, REALITY'], ['pinnedPeerCertSha256', t('hosts.fields.pinnedPeerCertSha256'), t('common.optional')], ['verifyPeerCertByName', t('hosts.fields.verifyPeerCertByName'), t('common.optional')], ['vlessRouteId', t('hosts.fields.vlessRouteId'), t('common.optional')], ['nodes', t('hosts.fields.nodes'), t('common.optional')], ['xrayJsonTemplateUuid', t('hosts.fields.xrayJsonTemplateUuid'), t('common.optional')], ['excludeFromSubscriptionTypes', t('hosts.fields.excludeFromSubscriptionTypes'), 'CLASH, MIHOMO'], ['internalSquads', t('hosts.fields.internalSquads'), t('common.optional')],
              ].map(([key, label, placeholder]) => (
                <label key={key} className="block space-y-2"><span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">{label}</span><Input type={key === 'port' || key === 'vlessRouteId' ? 'number' : 'text'} min={key === 'port' || key === 'vlessRouteId' ? '0' : undefined} max={key === 'port' || key === 'vlessRouteId' ? '65535' : undefined} value={form[key as keyof HostFormState] as string} onChange={(event) => setForm((current) => current ? ({ ...current, [key]: event.target.value }) : current)} placeholder={placeholder} /></label>
              ))}

              {[
                ['alpn', t('common.alpn'), ['', ...ALPN_VALUES]], ['securityLayer', t('hosts.fields.securityLayer'), SECURITY_LAYER_VALUES], ['mihomoIpVersion', t('hosts.fields.mihomoIpVersion'), ['', ...MIHOMO_IP_VALUES]], ['internalSquadsMode', t('hosts.fields.internalSquadsMode'), ['EXCLUDE', 'ALLOW_ONLY']],
              ].map(([key, label, values]) => (
                <label key={String(key)} className="block space-y-2"><span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">{String(label)}</span><select value={form[key as keyof HostFormState] as string} onChange={(event) => setForm((current) => current ? ({ ...current, [key as string]: event.target.value }) : current)} className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm">{(values as readonly string[]).map((value) => <option key={value || 'none'} value={value}>{value || t('common.emptyShort')}</option>)}</select></label>
              ))}

              {[
                ['xhttpExtraParams', t('hosts.fields.xhttpExtraParams')], ['muxParams', t('hosts.fields.muxParams')], ['sockoptParams', t('hosts.fields.sockoptParams')], ['finalMask', t('hosts.fields.finalMask')],
              ].map(([key, label]) => (
                <label key={key} className="block space-y-2"><span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">{label}</span><textarea rows={4} value={form[key as keyof HostFormState] as string} onChange={(event) => setForm((current) => current ? ({ ...current, [key]: event.target.value }) : current)} className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm" /></label>
              ))}

              <div className="grid gap-3 sm:grid-cols-2">
                {[
                  ['isDisabled', t('common.disabled')], ['isHidden', t('hosts.fields.isHidden')], ['overrideSniFromAddress', t('hosts.fields.overrideSniFromAddress')], ['keepSniBlank', t('hosts.fields.keepSniBlank')], ['shuffleHost', t('hosts.fields.shuffleHost')], ['mihomoX25519', t('hosts.fields.mihomoX25519')],
                ].map(([key, label]) => (
                  <label key={key} className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3"><input type="checkbox" checked={form[key as keyof HostFormState] as boolean} onChange={(event) => setForm((current) => current ? ({ ...current, [key]: event.target.checked }) : current)} /><span className="text-sm font-mono text-foreground">{label}</span></label>
                ))}
              </div>

              <div className="flex flex-wrap gap-3"><Button type="submit" magnetic={false} disabled={updateMutation.isPending}>{updateMutation.isPending ? t('common.saving') : t('common.save')}</Button><Button type="button" variant="ghost" magnetic={false} onClick={() => { setSelectedHostId(null); setForm(null); setFeedback(null); }}>{t('common.cancel')}</Button></div>
            </form>
          ) : null}
        </section>
      </div>
    </InfrastructurePageShell>
  );
}

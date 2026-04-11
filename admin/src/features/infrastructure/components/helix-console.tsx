'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Orbit, PauseCircle, Search, Send, Waypoints } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { helixApi } from '@/lib/api/infrastructure';
import { InfrastructureEmptyState } from '@/features/infrastructure/components/empty-state';
import { JsonPreview } from '@/features/infrastructure/components/json-preview';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import {
  formatCompactNumber,
  formatDateTime,
  humanizeToken,
  parseLineList,
} from '@/features/infrastructure/lib/formatting';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';

interface PublishFormState {
  rollout_id: string;
  batch_id: string;
  channel: string;
  manifest_version: string;
  target_node_ids: string;
  pause_on_rollback_spike: boolean;
  revoke_on_manifest_error: boolean;
}

const EMPTY_PUBLISH_FORM: PublishFormState = {
  rollout_id: 'rollout-',
  batch_id: '',
  channel: 'stable',
  manifest_version: '',
  target_node_ids: '',
  pause_on_rollback_spike: true,
  revoke_on_manifest_error: true,
};

export function HelixConsole() {
  const t = useTranslations('Infrastructure');
  const queryClient = useQueryClient();
  const [publishForm, setPublishForm] = useState<PublishFormState>(EMPTY_PUBLISH_FORM);
  const [lookupInput, setLookupInput] = useState('');
  const [activeRolloutId, setActiveRolloutId] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

  const nodesQuery = useQuery({
    queryKey: ['infrastructure', 'helix', 'nodes'],
    queryFn: async () => {
      const response = await helixApi.listNodes();
      return response.data;
    },
    staleTime: 30_000,
    retry: false,
  });

  const transportProfilesQuery = useQuery({
    queryKey: ['infrastructure', 'helix', 'transport-profiles'],
    queryFn: async () => {
      const response = await helixApi.listTransportProfiles();
      return response.data;
    },
    staleTime: 30_000,
    retry: false,
  });

  const rolloutStateQuery = useQuery({
    queryKey: ['infrastructure', 'helix', 'rollout', activeRolloutId],
    queryFn: async () => {
      const response = await helixApi.getRolloutStatus(activeRolloutId);
      return response.data;
    },
    enabled: Boolean(activeRolloutId),
    retry: false,
  });

  const canaryQuery = useQuery({
    queryKey: ['infrastructure', 'helix', 'canary', activeRolloutId],
    queryFn: async () => {
      const response = await helixApi.getCanaryEvidence(activeRolloutId);
      return response.data;
    },
    enabled: Boolean(activeRolloutId),
    retry: false,
  });

  const assignmentQuery = useQuery({
    queryKey: ['infrastructure', 'helix', 'assignment', selectedNodeId],
    queryFn: async () => {
      const response = await helixApi.previewNodeAssignment(selectedNodeId);
      return response.data;
    },
    enabled: Boolean(selectedNodeId),
    retry: false,
  });

  const publishMutation = useMutation({
    mutationFn: helixApi.publishRollout,
    onSuccess: async (response) => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'helix', 'nodes'] });
      setActiveRolloutId(response.data.rollout_id);
      setLookupInput(response.data.rollout_id);
      setFeedback(t('helix.publishSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const pauseMutation = useMutation({
    mutationFn: (rolloutId: string) => helixApi.pauseRollout(rolloutId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'helix', 'rollout', activeRolloutId] });
      setFeedback(t('helix.pauseSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (manifestVersionId: string) => helixApi.revokeManifest(manifestVersionId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['infrastructure', 'helix', 'rollout', activeRolloutId] });
      setFeedback(t('helix.revokeSuccess'));
    },
    onError: (error) => {
      setFeedback(error instanceof Error ? error.message : t('common.actionFailed'));
    },
  });

  const nodes = nodesQuery.data ?? [];
  const transportProfiles = transportProfilesQuery.data ?? [];

  async function handlePublish(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);

    if (
      !publishForm.rollout_id.trim() ||
      !publishForm.batch_id.trim() ||
      !publishForm.manifest_version.trim()
    ) {
      setFeedback(t('common.validation.helixPublishInvalid'));
      return;
    }

    const targetNodeIds = parseLineList(publishForm.target_node_ids);
    if (targetNodeIds.length === 0) {
      setFeedback(t('common.validation.helixTargetsRequired'));
      return;
    }

    await publishMutation.mutateAsync({
      rollout_id: publishForm.rollout_id.trim(),
      batch_id: publishForm.batch_id.trim(),
      channel: publishForm.channel,
      manifest_version: publishForm.manifest_version.trim(),
      target_node_ids: targetNodeIds,
      pause_on_rollback_spike: publishForm.pause_on_rollback_spike,
      revoke_on_manifest_error: publishForm.revoke_on_manifest_error,
    });
  }

  return (
    <InfrastructurePageShell
      eyebrow={t('helix.eyebrow')}
      title={t('helix.title')}
      description={t('helix.description')}
      icon={Waypoints}
      metrics={[
        {
          label: t('helix.metrics.nodes'),
          value: formatCompactNumber(nodes.length),
          hint: t('helix.metrics.nodesHint'),
          tone: 'info',
        },
        {
          label: t('helix.metrics.profiles'),
          value: formatCompactNumber(transportProfiles.length),
          hint: t('helix.metrics.profilesHint'),
          tone: 'success',
        },
        {
          label: t('helix.metrics.activeRollouts'),
          value: formatCompactNumber(nodes.filter((node) => node.active_rollout_id).length),
          hint: t('helix.metrics.activeRolloutsHint'),
          tone: 'warning',
        },
        {
          label: t('helix.metrics.channels'),
          value: formatCompactNumber(new Set(nodes.map((node) => node.rollout_channel)).size),
          hint: t('helix.metrics.channelsHint'),
          tone: 'neutral',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          {nodes.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.node')}</TableHead>
                  <TableHead>{t('common.channel')}</TableHead>
                  <TableHead>{t('common.transport')}</TableHead>
                  <TableHead>{t('common.heartbeat')}</TableHead>
                  <TableHead>{t('common.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {nodes.map((node) => (
                  <TableRow key={node.service_node_id}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {node.node_name}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {node.service_node_id}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{node.rollout_channel}</TableCell>
                    <TableCell>
                      <InfrastructureStatusChip
                        label={node.transport_enabled ? t('common.enabled') : t('common.disabled')}
                        tone={node.transport_enabled ? 'success' : 'warning'}
                      />
                    </TableCell>
                    <TableCell>{formatDateTime(node.last_heartbeat_at)}</TableCell>
                    <TableCell>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        magnetic={false}
                        onClick={() => setSelectedNodeId(node.service_node_id)}
                      >
                        {t('helix.assignmentAction')}
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <InfrastructureEmptyState label={t('helix.empty')} />
          )}
        </section>

        <section className="space-y-6 xl:col-span-5">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('helix.publishTitle')}
            </h2>
            {feedback ? (
              <div className="mt-4 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
                {feedback}
              </div>
            ) : null}
            <form className="mt-5 space-y-4" onSubmit={handlePublish}>
              {[
                ['rollout_id', t('common.rolloutId'), 'rollout-stable-apr10'],
                ['batch_id', t('common.batchId'), 'batch-2026-04-10'],
                ['manifest_version', t('common.manifestVersion'), 'manifest-v2026-04-10-1'],
              ].map(([key, label, placeholder]) => (
                <label key={key} className="block space-y-2">
                  <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {label}
                  </span>
                  <Input
                    value={publishForm[key as keyof PublishFormState] as string}
                    onChange={(event) =>
                      setPublishForm((current) => ({
                        ...current,
                        [key]: event.target.value,
                      }))
                    }
                    placeholder={placeholder}
                  />
                </label>
              ))}

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.channel')}
                </span>
                <select
                  value={publishForm.channel}
                  onChange={(event) =>
                    setPublishForm((current) => ({ ...current, channel: event.target.value }))
                  }
                  className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                >
                  <option value="lab">lab</option>
                  <option value="canary">canary</option>
                  <option value="stable">stable</option>
                </select>
              </label>

              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.targetNodeIds')}
                </span>
                <textarea
                  value={publishForm.target_node_ids}
                  onChange={(event) =>
                    setPublishForm((current) => ({
                      ...current,
                      target_node_ids: event.target.value,
                    }))
                  }
                  rows={5}
                  placeholder="service-node-1&#10;service-node-2"
                  className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </label>

              <div className="grid gap-3 md:grid-cols-2">
                <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={publishForm.pause_on_rollback_spike}
                    onChange={(event) =>
                      setPublishForm((current) => ({
                        ...current,
                        pause_on_rollback_spike: event.target.checked,
                      }))
                    }
                  />
                  <span className="text-sm font-mono text-foreground">{t('common.pauseOnRollback')}</span>
                </label>
                <label className="flex items-center gap-3 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
                  <input
                    type="checkbox"
                    checked={publishForm.revoke_on_manifest_error}
                    onChange={(event) =>
                      setPublishForm((current) => ({
                        ...current,
                        revoke_on_manifest_error: event.target.checked,
                      }))
                    }
                  />
                  <span className="text-sm font-mono text-foreground">{t('common.revokeOnError')}</span>
                </label>
              </div>

              <Button type="submit" magnetic={false} disabled={publishMutation.isPending}>
                <Send className="mr-2 h-4 w-4" />
                {t('helix.publishAction')}
              </Button>
            </form>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('helix.lookupTitle')}
            </h2>
            <div className="mt-5 flex gap-3">
              <Input
                value={lookupInput}
                onChange={(event) => setLookupInput(event.target.value)}
                placeholder="rollout-stable-apr10"
              />
              <Button
                type="button"
                magnetic={false}
                onClick={() => setActiveRolloutId(lookupInput.trim())}
              >
                <Search className="mr-2 h-4 w-4" />
                {t('helix.lookupAction')}
              </Button>
            </div>

            {rolloutStateQuery.data ? (
              <div className="mt-5 space-y-4">
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {rolloutStateQuery.data.rollout_id}
                    </p>
                    <InfrastructureStatusChip
                      label={humanizeToken(rolloutStateQuery.data.desired_state)}
                      tone="info"
                    />
                  </div>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('helix.lookupSummary', {
                      target: rolloutStateQuery.data.current_batch.target_nodes,
                      completed: rolloutStateQuery.data.current_batch.completed_nodes,
                      failed: rolloutStateQuery.data.current_batch.failed_nodes,
                    })}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-3">
                    <Button
                      type="button"
                      magnetic={false}
                      disabled={pauseMutation.isPending}
                      onClick={() => pauseMutation.mutate(rolloutStateQuery.data.rollout_id)}
                    >
                      <PauseCircle className="mr-2 h-4 w-4" />
                      {t('helix.pauseAction')}
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      magnetic={false}
                      disabled={revokeMutation.isPending}
                      onClick={() =>
                        revokeMutation.mutate(
                          rolloutStateQuery.data.current_batch.manifest_version,
                        )
                      }
                    >
                      <Orbit className="mr-2 h-4 w-4" />
                      {t('helix.revokeAction')}
                    </Button>
                  </div>
                </div>

                {canaryQuery.data ? (
                  <JsonPreview value={canaryQuery.data} maxHeightClassName="max-h-72" />
                ) : null}
              </div>
            ) : null}
          </article>

          {selectedNodeId ? (
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('helix.assignmentTitle')}
              </h2>
              <div className="mt-5">
                {assignmentQuery.data ? (
                  <JsonPreview value={assignmentQuery.data} maxHeightClassName="max-h-80" />
                ) : (
                  <InfrastructureEmptyState label={t('helix.assignmentEmpty')} />
                )}
              </div>
            </article>
          ) : null}
        </section>

        <section className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-12">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('helix.transportProfilesTitle')}
          </h2>
          {transportProfiles.length ? (
            <Table className="mt-5">
              <TableHeader>
                <TableRow>
                  <TableHead>{t('common.profile')}</TableHead>
                  <TableHead>{t('common.channel')}</TableHead>
                  <TableHead>{t('common.status')}</TableHead>
                  <TableHead>{t('common.fallbackCore')}</TableHead>
                  <TableHead>{t('common.updatedAt')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transportProfiles.map((profile) => (
                  <TableRow key={profile.transport_profile_id}>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-display uppercase tracking-[0.14em] text-white">
                          {profile.transport_profile_id}
                        </p>
                        <p className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {profile.profile_family} v{profile.profile_version}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>{profile.channel}</TableCell>
                    <TableCell>
                      <InfrastructureStatusChip
                        label={humanizeToken(profile.status)}
                        tone={profile.status === 'active' ? 'success' : 'info'}
                      />
                    </TableCell>
                    <TableCell>{profile.fallback_core}</TableCell>
                    <TableCell>{formatDateTime(profile.updated_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="mt-5">
              <InfrastructureEmptyState label={t('helix.transportProfilesEmpty')} />
            </div>
          )}
        </section>
      </div>
    </InfrastructurePageShell>
  );
}

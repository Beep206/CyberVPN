'use client';

import { useRef, useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Braces,
  Cable,
  CheckCircle2,
  CircleAlert,
  FileJson2,
  ListTree,
  MapPinned,
  Pencil,
  RefreshCw,
  RotateCw,
  SlidersHorizontal,
  Tags,
  Trash2,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { InfrastructurePageShell } from '@/features/infrastructure/components/infrastructure-page-shell';
import { InfrastructureStatusChip } from '@/features/infrastructure/components/infrastructure-status-chip';
import {
  createOperatorIdempotencyKey,
  REMNAWAVE_MUTABLE_TAG_RESOURCES,
  REMNAWAVE_TAG_RESOURCES,
  remnawaveOperatorApi,
  type NodeIntegration,
  type OperatorMutationOutcome,
  type OperatorMutationReceipt,
  type RemnawaveMutableTagResource,
  type RemnawaveTagResource,
} from '@/lib/api/remnawave-operator';
import { adminRemnawaveStatusApi } from '@/lib/api/remnawave-status';
import { hasAdminPermission } from '@/shared/lib/admin-rbac';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/shared/ui/organisms/table';
import { useAuthStore } from '@/stores/auth-store';

export const REMNAWAVE_OPERATOR_SECTION_KEYS = [
  'tags',
  'geoCheck',
  'integrations',
  'sharedLists',
  'snippets',
] as const;

export type OperatorSection = (typeof REMNAWAVE_OPERATOR_SECTION_KEYS)[number];
type OperatorCapability =
  | 'tags'
  | 'geo_check'
  | 'node_integrations'
  | 'shared_lists'
  | 'root_snippets';

interface SectionDefinition {
  key: OperatorSection;
  capability: OperatorCapability;
  icon: typeof Tags;
}

const SECTIONS: readonly SectionDefinition[] = [
  { key: 'tags', capability: 'tags', icon: Tags },
  { key: 'geoCheck', capability: 'geo_check', icon: MapPinned },
  { key: 'integrations', capability: 'node_integrations', icon: Cable },
  { key: 'sharedLists', capability: 'shared_lists', icon: ListTree },
  { key: 'snippets', capability: 'root_snippets', icon: FileJson2 },
] as const;

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TAG_PATTERN = /^[A-Z0-9_:]{1,36}$/;
const SHARED_LIST_NAME_PATTERN = /^[A-Za-z0-9_-]+(?:\/[A-Za-z0-9_-]+)*$/;
const SNIPPET_NAME_PATTERN = /^[A-Za-z0-9_ -]+(?:\/[A-Za-z0-9_ -]+)*$/;
const MAX_JSON_CHARACTERS = 512 * 1024;
export const GEO_CHECK_MAX_POLL_ATTEMPTS = 30;

const panelClass = 'rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/70 p-5 md:p-6';
const fieldLabelClass = 'block text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground';
const textareaClass = 'mt-2 flex w-full rounded-md border border-input bg-transparent px-3 py-2 font-mono text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50';

interface FeedbackState {
  kind: 'committed' | 'reconciliation' | 'error';
  receipt?: OperatorMutationReceipt;
  message?: string;
}

function getHttpStatus(error: unknown): number | null {
  if (typeof error !== 'object' || error === null || !('response' in error)) return null;
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === 'number' ? response.status : null;
}

function parseJsonObject(value: string): Record<string, unknown> | null {
  if (value.length > MAX_JSON_CHARACTERS) return null;
  try {
    const parsed: unknown = JSON.parse(value);
    return typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)
      ? parsed as Record<string, unknown>
      : null;
  } catch {
    return null;
  }
}

function parseJsonArray(value: string): Array<Record<string, unknown>> | null {
  if (value.length > MAX_JSON_CHARACTERS) return null;
  try {
    const parsed: unknown = JSON.parse(value);
    if (!Array.isArray(parsed)) return null;
    if (!parsed.every((item) => typeof item === 'object' && item !== null && !Array.isArray(item))) {
      return null;
    }
    return parsed as Array<Record<string, unknown>>;
  } catch {
    return null;
  }
}

function stringifyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function feedbackFromOutcome<T>(
  outcome: OperatorMutationOutcome<T>,
  committedMessage?: string,
): FeedbackState {
  if (outcome.kind === 'reconciliation') {
    return { kind: 'reconciliation', receipt: outcome.receipt };
  }
  return { kind: 'committed', message: committedMessage };
}

function discardCommittedResource<T>(
  outcome: OperatorMutationOutcome<T>,
): OperatorMutationOutcome<null> {
  return outcome.kind === 'reconciliation'
    ? outcome
    : { kind: 'committed', resource: null };
}

function MutationFeedback({
  feedback,
  successLabel,
}: {
  feedback: FeedbackState | null;
  successLabel: string;
}) {
  const t = useTranslations('Infrastructure.remnawaveOperator');
  if (!feedback) return null;

  const isError = feedback.kind === 'error';
  const isPendingReceipt = feedback.kind === 'reconciliation';
  const requiresReconciliation = feedback.receipt?.requires_reconciliation === true;
  return (
    <div
      role={isError ? 'alert' : 'status'}
      aria-live="polite"
      className={`rounded-xl border px-4 py-3 font-mono text-sm ${
        isError
          ? 'border-neon-pink/30 bg-neon-pink/5 text-neon-pink'
          : isPendingReceipt
            ? 'border-amber-400/30 bg-amber-400/5 text-amber-200'
            : 'border-matrix-green/30 bg-matrix-green/5 text-matrix-green'
      }`}
    >
      <div className="flex items-start gap-2">
        {isError || isPendingReceipt ? (
          <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        ) : (
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        )}
        <div>
          <p>
            {isError
              ? feedback.message ?? t('feedback.failed')
              : isPendingReceipt
                ? requiresReconciliation
                  ? t('feedback.reconciliation')
                  : t('feedback.accepted')
                : feedback.message ?? successLabel}
          </p>
          {feedback.receipt ? (
            <p className="mt-2 break-all text-xs text-muted-foreground">
              {t('feedback.receipt', { attemptId: feedback.receipt.attempt_id })}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function LoadFailure({ error, retry }: { error: unknown; retry: () => void }) {
  const t = useTranslations('Infrastructure.remnawaveOperator');
  const forbidden = getHttpStatus(error) === 403;
  return (
    <div role="alert" className="rounded-xl border border-neon-pink/30 bg-neon-pink/5 p-4">
      <p className="font-mono text-sm text-neon-pink">
        {forbidden ? t('errors.forbidden') : t('errors.loadFailed')}
      </p>
      {!forbidden ? (
        <Button type="button" variant="outline" className="mt-3" magnetic={false} onClick={retry}>
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
          {t('actions.retry')}
        </Button>
      ) : null}
    </div>
  );
}

function ReadOnlyNotice() {
  const t = useTranslations('Infrastructure.remnawaveOperator');
  return (
    <p role="status" className="rounded-xl border border-amber-400/25 bg-amber-400/5 px-4 py-3 font-mono text-xs leading-5 text-amber-200">
      {t('readOnly')}
    </p>
  );
}

function TagsConsole({ canWrite }: { canWrite: boolean }) {
  const t = useTranslations('Infrastructure.remnawaveOperator.tags');
  const queryClient = useQueryClient();
  const [resource, setResource] = useState<RemnawaveTagResource>('nodes');
  const [resourceUuid, setResourceUuid] = useState('');
  const [tagsText, setTagsText] = useState('');
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const mutable = REMNAWAVE_MUTABLE_TAG_RESOURCES.includes(
    resource as RemnawaveMutableTagResource,
  );

  const tagsQuery = useQuery({
    queryKey: ['infrastructure', 'remnawave-operator', 'tags', resource],
    queryFn: async () => (await remnawaveOperatorApi.getTags(resource)).data,
    retry: false,
    staleTime: 15_000,
  });

  const mutation = useMutation({
    retry: false,
    mutationFn: ({ uuid, tags }: { uuid: string; tags: string[] }) =>
      remnawaveOperatorApi.setTags(
        resource as RemnawaveMutableTagResource,
        { uuid, tags },
        createOperatorIdempotencyKey(),
      ),
    onSuccess: async (outcome) => {
      setFeedback(feedbackFromOutcome(outcome));
      await queryClient.invalidateQueries({
        queryKey: ['infrastructure', 'remnawave-operator', 'tags', resource],
      });
    },
    onError: () => setFeedback({ kind: 'error' }),
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    const tags = tagsText
      .split(',')
      .map((tag) => tag.trim())
      .filter(Boolean);
    if (
      !canWrite
      || !mutable
      || !UUID_PATTERN.test(resourceUuid)
      || tags.length > 10
      || new Set(tags).size !== tags.length
      || tags.some((tag) => !TAG_PATTERN.test(tag))
    ) {
      setFeedback({ kind: 'error', message: t('validation') });
      return;
    }
    mutation.mutate({ uuid: resourceUuid, tags });
  }

  return (
    <section aria-labelledby="remnawave-tags-title" className={panelClass}>
      <div className="flex items-start gap-3">
        <Tags className="mt-1 h-5 w-5 text-neon-cyan" aria-hidden="true" />
        <div>
          <h2 id="remnawave-tags-title" className="font-display text-xl text-white">{t('title')}</h2>
          <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">{t('description')}</p>
        </div>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <div>
          <label htmlFor="remnawave-tag-resource" className={fieldLabelClass}>{t('resource')}</label>
          <select
            id="remnawave-tag-resource"
            value={resource}
            onChange={(event) => {
              setResource(event.target.value as RemnawaveTagResource);
              setFeedback(null);
            }}
            className={`${textareaClass} min-h-11`}
          >
            {REMNAWAVE_TAG_RESOURCES.map((item) => (
              <option key={item} value={item}>{t(`resources.${item}`)}</option>
            ))}
          </select>

          <div className="mt-4 min-h-24 rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-4">
            {tagsQuery.isPending ? <p role="status" className="font-mono text-sm">{t('loading')}</p> : null}
            {tagsQuery.isError ? (
              <LoadFailure error={tagsQuery.error} retry={() => { void tagsQuery.refetch(); }} />
            ) : null}
            {tagsQuery.data ? (
              tagsQuery.data.tags.length > 0 ? (
                <ul className="flex flex-wrap gap-2" aria-label={t('inventory')}>
                  {tagsQuery.data.tags.map((tag) => (
                    <li key={tag} className="rounded-lg border border-neon-cyan/30 bg-neon-cyan/5 px-2 py-1 font-mono text-xs text-neon-cyan">{tag}</li>
                  ))}
                </ul>
              ) : <p className="font-mono text-sm text-muted-foreground">{t('empty')}</p>
            ) : null}
          </div>
        </div>

        <div>
          {!canWrite ? <ReadOnlyNotice /> : null}
          {canWrite && !mutable ? (
            <p role="status" className="rounded-xl border border-amber-400/25 bg-amber-400/5 px-4 py-3 font-mono text-xs text-amber-200">{t('inventoryOnly')}</p>
          ) : null}
          <form className="mt-4 space-y-4" onSubmit={submit}>
            <label className={fieldLabelClass} htmlFor="remnawave-tag-uuid">
              {t('uuid')}
              <Input id="remnawave-tag-uuid" className="mt-2" value={resourceUuid} onChange={(event) => setResourceUuid(event.target.value)} disabled={!canWrite || !mutable} />
            </label>
            <label className={fieldLabelClass} htmlFor="remnawave-tag-values">
              {t('values')}
              <Input id="remnawave-tag-values" className="mt-2" value={tagsText} onChange={(event) => setTagsText(event.target.value)} disabled={!canWrite || !mutable} aria-describedby="remnawave-tag-help" />
            </label>
            <p id="remnawave-tag-help" className="font-mono text-xs text-muted-foreground">{t('help')}</p>
            <MutationFeedback feedback={feedback} successLabel={t('saved')} />
            <Button type="submit" magnetic={false} disabled={!canWrite || !mutable || mutation.isPending}>
              {mutation.isPending ? t('saving') : t('save')}
            </Button>
          </form>
        </div>
      </div>
    </section>
  );
}

function GeoCheckConsole({ canWrite }: { canWrite: boolean }) {
  const t = useTranslations('Infrastructure.remnawaveOperator.geoCheck');
  const [nodeUuid, setNodeUuid] = useState('');
  const [sourceKind, setSourceKind] = useState<'none' | 'ip' | 'interface'>('none');
  const [sourceValue, setSourceValue] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [pollAttempts, setPollAttempts] = useState(0);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const startMutation = useMutation({
    retry: false,
    mutationFn: () => remnawaveOperatorApi.startGeoCheck(
      nodeUuid,
      sourceKind === 'none' ? {} : { [sourceKind]: sourceValue.trim() },
      createOperatorIdempotencyKey(),
    ),
    onSuccess: (outcome) => {
      setFeedback(feedbackFromOutcome(outcome));
      if (outcome.kind === 'committed') setJobId(outcome.resource.jobId);
    },
    onError: () => setFeedback({ kind: 'error' }),
  });

  const resultQuery = useQuery({
    queryKey: ['infrastructure', 'remnawave-operator', 'geocheck', jobId],
    queryFn: async () => {
      const response = await remnawaveOperatorApi.getGeoCheck(jobId ?? '');
      setPollAttempts((current) => current + 1);
      return response.data;
    },
    enabled: jobId !== null && pollAttempts < GEO_CHECK_MAX_POLL_ATTEMPTS,
    retry: false,
    refetchInterval: (query) => {
      const data = query.state.data;
      return pollAttempts >= GEO_CHECK_MAX_POLL_ATTEMPTS
        || (data && (data.isCompleted || data.isFailed))
        ? false
        : 2_000;
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    setJobId(null);
    setPollAttempts(0);
    if (!canWrite || !UUID_PATTERN.test(nodeUuid) || (sourceKind !== 'none' && !sourceValue.trim())) {
      setFeedback({ kind: 'error', message: t('validation') });
      return;
    }
    startMutation.mutate();
  }

  const result = resultQuery.data?.result;
  const pollLimitReached = pollAttempts >= GEO_CHECK_MAX_POLL_ATTEMPTS
    && !resultQuery.data?.isCompleted
    && !resultQuery.data?.isFailed;
  return (
    <section aria-labelledby="remnawave-geocheck-title" className={panelClass}>
      <div className="flex items-start gap-3">
        <MapPinned className="mt-1 h-5 w-5 text-neon-cyan" aria-hidden="true" />
        <div>
          <h2 id="remnawave-geocheck-title" className="font-display text-xl text-white">{t('title')}</h2>
          <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">{t('description')}</p>
        </div>
      </div>
      {!canWrite ? <div className="mt-5"><ReadOnlyNotice /></div> : null}
      <form className="mt-5 grid gap-4 md:grid-cols-2" onSubmit={submit}>
        <label className={fieldLabelClass} htmlFor="remnawave-geocheck-node">
          {t('nodeUuid')}
          <Input id="remnawave-geocheck-node" className="mt-2" value={nodeUuid} onChange={(event) => setNodeUuid(event.target.value)} disabled={!canWrite} />
        </label>
        <label className={fieldLabelClass} htmlFor="remnawave-geocheck-source-kind">
          {t('source')}
          <select id="remnawave-geocheck-source-kind" className={`${textareaClass} min-h-11`} value={sourceKind} onChange={(event) => { setSourceKind(event.target.value as typeof sourceKind); setSourceValue(''); }} disabled={!canWrite}>
            <option value="none">{t('sources.none')}</option>
            <option value="ip">{t('sources.ip')}</option>
            <option value="interface">{t('sources.interface')}</option>
          </select>
        </label>
        {sourceKind !== 'none' ? (
          <label className={`${fieldLabelClass} md:col-span-2`} htmlFor="remnawave-geocheck-source">
            {sourceKind === 'ip' ? t('ip') : t('interface')}
            <Input id="remnawave-geocheck-source" className="mt-2" value={sourceValue} onChange={(event) => setSourceValue(event.target.value)} disabled={!canWrite} />
          </label>
        ) : null}
        <div className="md:col-span-2"><MutationFeedback feedback={feedback} successLabel={t('queued')} /></div>
        <Button type="submit" magnetic={false} disabled={!canWrite || startMutation.isPending}>
          {startMutation.isPending ? t('queueing') : t('run')}
        </Button>
      </form>

      {jobId ? (
        <div className="mt-5 rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-4" aria-live="polite">
          <p className="break-all font-mono text-xs text-muted-foreground">{t('job', { jobId })}</p>
          {resultQuery.isPending ? <p role="status" className="mt-3 font-mono text-sm">{t('polling')}</p> : null}
          {resultQuery.isError ? <div className="mt-3"><LoadFailure error={resultQuery.error} retry={() => { void resultQuery.refetch(); }} /></div> : null}
          {pollLimitReached ? (
            <div role="status" className="mt-3 rounded-xl border border-amber-400/25 bg-amber-400/5 p-3 font-mono text-sm text-amber-200">
              <p>{t('pollLimitReached')}</p>
              <Button type="button" variant="outline" className="mt-3" magnetic={false} onClick={() => setPollAttempts(0)}>
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('continuePolling')}
              </Button>
            </div>
          ) : null}
          {resultQuery.data?.isFailed ? <p role="alert" className="mt-3 font-mono text-sm text-neon-pink">{t('failed')}</p> : null}
          {resultQuery.data?.isCompleted && result ? (
            <div className="mt-4 space-y-4">
              <InfrastructureStatusChip label={result.success ? t('success') : t('failed')} tone={result.success ? 'success' : 'danger'} />
              {result.message ? <p className="font-mono text-sm text-muted-foreground">{result.message}</p> : null}
              {result.image ? (
                // SVG is kept in an image browsing context; it is never injected as document markup.
                // eslint-disable-next-line @next/next/no-img-element
                <img src={`data:${result.image.media_type};${result.image.encoding},${result.image.data}`} alt={t('reportImage')} className="max-h-[32rem] w-full rounded-xl border border-grid-line/20 bg-white object-contain" />
              ) : null}
              {result.rawReport ? (
                <details>
                  <summary className="cursor-pointer font-mono text-sm text-neon-cyan">{t('rawReport')}</summary>
                  <pre className="mt-3 max-h-96 overflow-auto rounded-xl border border-grid-line/20 bg-black/30 p-4 font-mono text-xs text-muted-foreground">{stringifyJson(result.rawReport)}</pre>
                </details>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

interface IntegrationFormState {
  mode: 'create' | 'edit';
  uuid: string | null;
  name: string;
  description: string;
  configText: string;
  restartNodes: boolean;
  confirmDelete: boolean;
}

type NodeIntegrationSummary = Pick<NodeIntegration, 'uuid' | 'name' | 'description'>;

const EMPTY_INTEGRATION_FORM: IntegrationFormState = {
  mode: 'create',
  uuid: null,
  name: '',
  description: '',
  configText: '{}',
  restartNodes: false,
  confirmDelete: false,
};

function NodeIntegrationsConsole({ canWrite }: { canWrite: boolean }) {
  const t = useTranslations('Infrastructure.remnawaveOperator.integrations');
  const queryClient = useQueryClient();
  const [form, setForm] = useState<IntegrationFormState>(EMPTY_INTEGRATION_FORM);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [loadingIntegrationUuid, setLoadingIntegrationUuid] = useState<string | null>(null);
  const integrationLoadSequence = useRef(0);

  const queryKey = ['infrastructure', 'remnawave-operator', 'node-integrations'] as const;
  const integrationsQuery = useQuery({
    queryKey,
    queryFn: async () => {
      const collection = (await remnawaveOperatorApi.listNodeIntegrations()).data;
      return {
        total: collection.total,
        items: collection.items.map(({ uuid, name, description }) => ({
          uuid,
          name,
          description,
        })),
      };
    },
    retry: false,
    staleTime: 15_000,
  });

  async function editIntegration(integration: NodeIntegrationSummary) {
    const requestSequence = integrationLoadSequence.current + 1;
    integrationLoadSequence.current = requestSequence;
    setLoadingIntegrationUuid(integration.uuid);
    setFeedback(null);
    try {
      const collection = (await remnawaveOperatorApi.listNodeIntegrations()).data;
      const selectedIntegration = collection.items.find((item) => item.uuid === integration.uuid);
      if (!selectedIntegration) throw new Error('Node integration disappeared during selection');
      if (integrationLoadSequence.current !== requestSequence) return;
      setForm({
        mode: 'edit',
        uuid: selectedIntegration.uuid,
        name: selectedIntegration.name,
        description: selectedIntegration.description ?? '',
        configText: stringifyJson(selectedIntegration.config),
        restartNodes: false,
        confirmDelete: false,
      });
    } catch {
      if (integrationLoadSequence.current === requestSequence) {
        setFeedback({ kind: 'error' });
      }
    } finally {
      if (integrationLoadSequence.current === requestSequence) {
        setLoadingIntegrationUuid(null);
      }
    }
  }

  async function settle(outcome: OperatorMutationOutcome<unknown>, committedMessage: string) {
    setFeedback(feedbackFromOutcome(outcome, committedMessage));
    await queryClient.invalidateQueries({ queryKey });
    if (outcome.kind === 'committed') setForm(EMPTY_INTEGRATION_FORM);
  }

  const createMutation = useMutation({
    retry: false,
    mutationFn: async () => {
      const config = parseJsonObject(form.configText);
      if (!config) throw new Error('Invalid node integration configuration');
      return discardCommittedResource(await remnawaveOperatorApi.createNodeIntegration(
        { name: form.name.trim(), description: form.description.trim() || null, config },
        createOperatorIdempotencyKey(),
      ));
    },
    onSuccess: (outcome) => settle(outcome, t('created')),
    onError: () => setFeedback({ kind: 'error' }),
  });
  const updateMutation = useMutation({
    retry: false,
    mutationFn: async () => {
      const config = parseJsonObject(form.configText);
      if (!config) throw new Error('Invalid node integration configuration');
      return discardCommittedResource(await remnawaveOperatorApi.updateNodeIntegration(
        {
          uuid: form.uuid ?? '',
          name: form.name.trim(),
          description: form.description.trim() || null,
          config,
          restartNodes: form.restartNodes,
        },
        createOperatorIdempotencyKey(),
      ));
    },
    onSuccess: (outcome) => settle(outcome, t('updated')),
    onError: () => setFeedback({ kind: 'error' }),
  });
  const deleteMutation = useMutation({
    retry: false,
    mutationFn: (uuid: string) =>
      remnawaveOperatorApi.deleteNodeIntegration(uuid, createOperatorIdempotencyKey()),
    onSuccess: (outcome) => settle(outcome, t('deleted')),
    onError: () => setFeedback({ kind: 'error' }),
  });

  const pending = loadingIntegrationUuid !== null || createMutation.isPending || updateMutation.isPending || deleteMutation.isPending;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    const config = parseJsonObject(form.configText);
    if (!canWrite || form.name.trim().length < 2 || form.name.trim().length > 30 || !config) {
      setFeedback({ kind: 'error', message: t('validation') });
      return;
    }
    if (form.mode === 'edit') updateMutation.mutate();
    else createMutation.mutate();
  }

  return (
    <section aria-labelledby="remnawave-integrations-title" className={panelClass}>
      <div className="flex items-start gap-3">
        <Cable className="mt-1 h-5 w-5 text-neon-cyan" aria-hidden="true" />
        <div>
          <h2 id="remnawave-integrations-title" className="font-display text-xl text-white">{t('title')}</h2>
          <p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">{t('description')}</p>
        </div>
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <div>
          {integrationsQuery.isPending ? <p role="status" className="font-mono text-sm">{t('loading')}</p> : null}
          {integrationsQuery.isError ? <LoadFailure error={integrationsQuery.error} retry={() => { void integrationsQuery.refetch(); }} /> : null}
          {integrationsQuery.data ? (
            integrationsQuery.data.items.length > 0 ? (
              <div className="overflow-x-auto">
                <Table>
                  <caption className="sr-only">{t('caption')}</caption>
                  <TableHeader><TableRow><TableHead>{t('name')}</TableHead><TableHead>{t('descriptionColumn')}</TableHead><TableHead>{t('action')}</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {integrationsQuery.data.items.map((integration) => (
                      <TableRow key={integration.uuid}>
                        <TableCell><p className="font-mono text-sm text-white">{integration.name}</p><p className="mt-1 font-mono text-xs text-muted-foreground">{integration.uuid}</p></TableCell>
                        <TableCell>{integration.description ?? '—'}</TableCell>
                        <TableCell>
                          <Button type="button" variant="outline" magnetic={false} onClick={() => { void editIntegration(integration); }} disabled={!canWrite || pending} aria-label={t('editNamed', { name: integration.name })}>
                            <Pencil className="mr-2 h-4 w-4" aria-hidden="true" />{t('edit')}
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ) : <p className="font-mono text-sm text-muted-foreground">{t('empty')}</p>
          ) : null}
        </div>

        <div>
          {!canWrite ? <ReadOnlyNotice /> : null}
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-display text-base text-white">{form.mode === 'edit' ? t('editTitle') : t('createTitle')}</h3>
            {form.mode === 'edit' ? (
              <Button type="button" variant="ghost" magnetic={false} onClick={() => { setForm(EMPTY_INTEGRATION_FORM); setFeedback(null); }} disabled={pending}>{t('cancel')}</Button>
            ) : null}
          </div>
          <form className="mt-4 space-y-4" onSubmit={submit}>
            <label className={fieldLabelClass} htmlFor="remnawave-integration-name">{t('name')}<Input id="remnawave-integration-name" className="mt-2" value={form.name} onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} disabled={!canWrite || pending} /></label>
            <label className={fieldLabelClass} htmlFor="remnawave-integration-description">{t('descriptionField')}<Input id="remnawave-integration-description" className="mt-2" value={form.description} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} disabled={!canWrite || pending} /></label>
            <label className={fieldLabelClass} htmlFor="remnawave-integration-config">{t('config')}<textarea id="remnawave-integration-config" className={textareaClass} rows={10} value={form.configText} onChange={(event) => setForm((current) => ({ ...current, configText: event.target.value }))} disabled={!canWrite || pending} aria-describedby="remnawave-integration-config-help" /></label>
            <p id="remnawave-integration-config-help" className="font-mono text-xs leading-5 text-amber-200">{t('configPrivacy')}</p>
            {form.mode === 'edit' ? (
              <label className="flex min-h-11 items-center gap-3 rounded-xl border border-grid-line/20 px-3 font-mono text-sm text-white"><input type="checkbox" checked={form.restartNodes} onChange={(event) => setForm((current) => ({ ...current, restartNodes: event.target.checked }))} disabled={!canWrite || pending} />{t('restartNodes')}</label>
            ) : null}
            <MutationFeedback feedback={feedback} successLabel={form.mode === 'edit' ? t('updated') : t('created')} />
            <div className="flex flex-wrap gap-3">
              <Button type="submit" magnetic={false} disabled={!canWrite || pending}><Braces className="mr-2 h-4 w-4" aria-hidden="true" />{pending ? t('saving') : form.mode === 'edit' ? t('update') : t('create')}</Button>
              {form.mode === 'edit' && form.uuid ? (
                <Button type="button" variant="destructive" magnetic={false} disabled={!canWrite || pending || !form.confirmDelete} onClick={() => deleteMutation.mutate(form.uuid ?? '')}><Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />{t('delete')}</Button>
              ) : null}
            </div>
            {form.mode === 'edit' ? (
              <label className="flex items-start gap-3 font-mono text-xs leading-5 text-amber-200"><input type="checkbox" checked={form.confirmDelete} onChange={(event) => setForm((current) => ({ ...current, confirmDelete: event.target.checked }))} disabled={!canWrite || pending} />{t('confirmDelete')}</label>
            ) : null}
          </form>
        </div>
      </div>
    </section>
  );
}

interface NamedJsonItem {
  name: string;
  summary: string;
  value?: Record<string, unknown> | Array<Record<string, unknown>>;
}

interface NamedJsonApi {
  queryKey: readonly string[];
  list: () => Promise<NamedJsonItem[]>;
  load: (name: string) => Promise<Record<string, unknown> | Array<Record<string, unknown>>>;
  create: (name: string, value: Record<string, unknown> | Array<Record<string, unknown>>, key: string) => Promise<OperatorMutationOutcome<unknown>>;
  update: (name: string, value: Record<string, unknown> | Array<Record<string, unknown>>, key: string) => Promise<OperatorMutationOutcome<unknown>>;
  remove: (name: string, key: string) => Promise<OperatorMutationOutcome<unknown>>;
  sync: (name: string, key: string) => Promise<OperatorMutationOutcome<unknown>>;
}

function NamedJsonConsole({
  namespace,
  valueKind,
  canWrite,
  api,
}: {
  namespace: 'sharedLists' | 'snippets';
  valueKind: 'object' | 'array';
  canWrite: boolean;
  api: NamedJsonApi;
}) {
  const t = useTranslations(`Infrastructure.remnawaveOperator.${namespace}`);
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<'create' | 'edit'>('create');
  const [name, setName] = useState('');
  const [valueText, setValueText] = useState(valueKind === 'object' ? '{}' : '[]');
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  const listQuery = useQuery({ queryKey: api.queryKey, queryFn: api.list, retry: false, staleTime: 15_000 });
  const loadMutation = useMutation({
    retry: false,
    mutationFn: api.load,
    onSuccess: (value, selectedName) => {
      setMode('edit');
      setName(selectedName);
      setValueText(stringifyJson(value));
      setConfirmDelete(false);
      setFeedback(null);
    },
    onError: () => setFeedback({ kind: 'error' }),
  });

  async function settle(outcome: OperatorMutationOutcome<unknown>, committedMessage: string) {
    setFeedback(feedbackFromOutcome(outcome, committedMessage));
    await queryClient.invalidateQueries({ queryKey: api.queryKey });
    if (outcome.kind === 'committed') resetEditor();
  }

  const createMutation = useMutation({ retry: false, mutationFn: ({ value }: { value: Record<string, unknown> | Array<Record<string, unknown>> }) => api.create(name.trim(), value, createOperatorIdempotencyKey()), onSuccess: (outcome) => settle(outcome, t('created')), onError: () => setFeedback({ kind: 'error' }) });
  const updateMutation = useMutation({ retry: false, mutationFn: ({ value }: { value: Record<string, unknown> | Array<Record<string, unknown>> }) => api.update(name.trim(), value, createOperatorIdempotencyKey()), onSuccess: (outcome) => settle(outcome, t('updated')), onError: () => setFeedback({ kind: 'error' }) });
  const deleteMutation = useMutation({ retry: false, mutationFn: () => api.remove(name, createOperatorIdempotencyKey()), onSuccess: (outcome) => settle(outcome, t('deleted')), onError: () => setFeedback({ kind: 'error' }) });
  const syncMutation = useMutation({ retry: false, mutationFn: (selectedName: string) => api.sync(selectedName, createOperatorIdempotencyKey()), onSuccess: async (outcome) => { setFeedback(feedbackFromOutcome(outcome, t('synced'))); await queryClient.invalidateQueries({ queryKey: api.queryKey }); }, onError: () => setFeedback({ kind: 'error' }) });

  const pending = loadMutation.isPending || createMutation.isPending || updateMutation.isPending || deleteMutation.isPending || syncMutation.isPending;

  function resetEditor() {
    setMode('create');
    setName('');
    setValueText(valueKind === 'object' ? '{}' : '[]');
    setConfirmDelete(false);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFeedback(null);
    const value = valueKind === 'object' ? parseJsonObject(valueText) : parseJsonArray(valueText);
    const pattern = valueKind === 'object' ? SHARED_LIST_NAME_PATTERN : SNIPPET_NAME_PATTERN;
    if (!canWrite || name.trim().length < 2 || name.trim().length > 255 || !pattern.test(name.trim()) || !value) {
      setFeedback({ kind: 'error', message: t('validation') });
      return;
    }
    if (mode === 'edit') updateMutation.mutate({ value });
    else createMutation.mutate({ value });
  }

  const Icon = namespace === 'sharedLists' ? ListTree : FileJson2;
  return (
    <section aria-labelledby={`remnawave-${namespace}-title`} className={panelClass}>
      <div className="flex items-start gap-3"><Icon className="mt-1 h-5 w-5 text-neon-cyan" aria-hidden="true" /><div><h2 id={`remnawave-${namespace}-title`} className="font-display text-xl text-white">{t('title')}</h2><p className="mt-2 font-mono text-sm leading-6 text-muted-foreground">{t('description')}</p></div></div>
      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <div>
          {listQuery.isPending ? <p role="status" className="font-mono text-sm">{t('loading')}</p> : null}
          {listQuery.isError ? <LoadFailure error={listQuery.error} retry={() => { void listQuery.refetch(); }} /> : null}
          {listQuery.data ? (listQuery.data.length > 0 ? (
            <div className="overflow-x-auto"><Table><caption className="sr-only">{t('caption')}</caption><TableHeader><TableRow><TableHead>{t('name')}</TableHead><TableHead>{t('summary')}</TableHead><TableHead>{t('actions')}</TableHead></TableRow></TableHeader><TableBody>{listQuery.data.map((item) => <TableRow key={item.name}><TableCell className="font-mono text-sm text-white">{item.name}</TableCell><TableCell>{item.summary}</TableCell><TableCell><div className="flex flex-wrap gap-2"><Button type="button" variant="outline" magnetic={false} disabled={!canWrite || pending} onClick={() => loadMutation.mutate(item.name)} aria-label={t('editNamed', { name: item.name })}><Pencil className="mr-2 h-4 w-4" aria-hidden="true" />{t('edit')}</Button><Button type="button" variant="outline" magnetic={false} disabled={!canWrite || pending} onClick={() => syncMutation.mutate(item.name)} aria-label={t('syncNamed', { name: item.name })}><RotateCw className="mr-2 h-4 w-4" aria-hidden="true" />{t('sync')}</Button></div></TableCell></TableRow>)}</TableBody></Table></div>
          ) : <p className="font-mono text-sm text-muted-foreground">{t('empty')}</p>) : null}
        </div>
        <div>
          {!canWrite ? <ReadOnlyNotice /> : null}
          <div className="flex items-center justify-between gap-3"><h3 className="font-display text-base text-white">{mode === 'edit' ? t('editTitle') : t('createTitle')}</h3>{mode === 'edit' ? <Button type="button" variant="ghost" magnetic={false} onClick={() => { resetEditor(); setFeedback(null); }} disabled={pending}>{t('cancel')}</Button> : null}</div>
          <form className="mt-4 space-y-4" onSubmit={submit}>
            <label className={fieldLabelClass} htmlFor={`remnawave-${namespace}-name`}>{t('name')}<Input id={`remnawave-${namespace}-name`} className="mt-2" value={name} onChange={(event) => setName(event.target.value)} disabled={!canWrite || pending || mode === 'edit'} /></label>
            <label className={fieldLabelClass} htmlFor={`remnawave-${namespace}-value`}>{t('value')}<textarea id={`remnawave-${namespace}-value`} className={textareaClass} rows={12} value={valueText} onChange={(event) => setValueText(event.target.value)} disabled={!canWrite || pending} /></label>
            <MutationFeedback feedback={feedback} successLabel={mode === 'edit' ? t('updated') : t('created')} />
            <div className="flex flex-wrap gap-3"><Button type="submit" magnetic={false} disabled={!canWrite || pending}><Braces className="mr-2 h-4 w-4" aria-hidden="true" />{pending ? t('saving') : mode === 'edit' ? t('update') : t('create')}</Button>{mode === 'edit' ? <Button type="button" variant="destructive" magnetic={false} disabled={!canWrite || pending || !confirmDelete} onClick={() => deleteMutation.mutate()}><Trash2 className="mr-2 h-4 w-4" aria-hidden="true" />{t('delete')}</Button> : null}</div>
            {mode === 'edit' ? <label className="flex items-start gap-3 font-mono text-xs leading-5 text-amber-200"><input type="checkbox" checked={confirmDelete} onChange={(event) => setConfirmDelete(event.target.checked)} disabled={!canWrite || pending} />{t('confirmDelete')}</label> : null}
          </form>
        </div>
      </div>
    </section>
  );
}

function SharedListsConsole({ canWrite }: { canWrite: boolean }) {
  const t = useTranslations('Infrastructure.remnawaveOperator.sharedLists');
  const queryKey = ['infrastructure', 'remnawave-operator', 'shared-lists'] as const;
  const api: NamedJsonApi = {
    queryKey,
    list: async () => (await remnawaveOperatorApi.listSharedLists()).data.items.map((item) => ({ name: item.name, summary: t('preview', { type: item.type, count: item.itemsCount }) })),
    load: async (name) => (await remnawaveOperatorApi.getSharedList(name)).data.config,
    create: (name, value, key) => remnawaveOperatorApi.createSharedList({ name, config: value as Record<string, unknown> }, key),
    update: (name, value, key) => remnawaveOperatorApi.updateSharedList({ name, config: value as Record<string, unknown> }, key),
    remove: remnawaveOperatorApi.deleteSharedList,
    sync: remnawaveOperatorApi.syncSharedList,
  };
  return <NamedJsonConsole namespace="sharedLists" valueKind="object" canWrite={canWrite} api={api} />;
}

function RootSnippetsConsole({ canWrite }: { canWrite: boolean }) {
  const t = useTranslations('Infrastructure.remnawaveOperator.snippets');
  const queryKey = ['infrastructure', 'remnawave-operator', 'snippets'] as const;
  const api: NamedJsonApi = {
    queryKey,
    list: async () => (await remnawaveOperatorApi.listRootSnippets()).data.items.map((item) => ({ name: item.name, summary: t('preview', { count: item.snippet.length }), value: item.snippet })),
    load: async (name) => {
      const item = (await remnawaveOperatorApi.listRootSnippets()).data.items.find((candidate) => candidate.name === name);
      if (!item) throw new Error('Root snippet disappeared during selection');
      return item.snippet;
    },
    create: (name, value, key) => remnawaveOperatorApi.createRootSnippet({ name, snippet: value as Array<Record<string, unknown>> }, key),
    update: (name, value, key) => remnawaveOperatorApi.updateRootSnippet({ name, snippet: value as Array<Record<string, unknown>> }, key),
    remove: remnawaveOperatorApi.deleteRootSnippet,
    sync: remnawaveOperatorApi.syncRootSnippet,
  };
  return <NamedJsonConsole namespace="snippets" valueKind="array" canWrite={canWrite} api={api} />;
}

export function RemnawaveOperatorConsole({
  initialSection = 'tags',
}: {
  initialSection?: OperatorSection;
}) {
  const t = useTranslations('Infrastructure.remnawaveOperator');
  const role = useAuthStore((state) => state.user?.role);
  const hasTrustedAdminRole = role === 'admin' || role === 'super_admin' || role === 'owner/super_admin';
  const canRead = hasTrustedAdminRole && hasAdminPermission(role, 'server_read');
  const canWrite = hasTrustedAdminRole && hasAdminPermission(role, 'server_update');
  const [activeSection, setActiveSection] = useState<OperatorSection>(initialSection);

  const statusQuery = useQuery({
    queryKey: ['infrastructure', 'remnawave', 'capabilities-and-streams'],
    queryFn: async () => (await adminRemnawaveStatusApi.getCapabilitiesAndStreams()).data,
    enabled: canRead,
    retry: false,
    staleTime: 15_000,
  });
  const enabledCount = statusQuery.data
    ? SECTIONS.filter((section) => statusQuery.data.capabilities[section.capability]).length
    : 0;
  const activeDefinition = SECTIONS.find((section) => section.key === activeSection) ?? SECTIONS[0];
  const activeEnabled = Boolean(statusQuery.data?.capabilities[activeDefinition.capability]);

  return (
    <InfrastructurePageShell
      eyebrow={t('eyebrow')}
      title={t('title')}
      description={t('description')}
      icon={SlidersHorizontal}
      metrics={[
        { label: t('metrics.enabled'), value: `${enabledCount}/${SECTIONS.length}`, hint: t('metrics.enabledHint'), tone: enabledCount === SECTIONS.length ? 'success' : 'warning' },
        { label: t('metrics.access'), value: canWrite ? t('metrics.write') : canRead ? t('metrics.read') : t('metrics.none'), hint: t('metrics.accessHint'), tone: canWrite ? 'success' : canRead ? 'warning' : 'danger' },
      ]}
      actions={
        <Button type="button" variant="outline" magnetic={false} onClick={() => { void statusQuery.refetch(); }} disabled={!canRead || statusQuery.isFetching}>
          <RefreshCw className={`mr-2 h-4 w-4 ${statusQuery.isFetching ? 'animate-spin' : ''}`} aria-hidden="true" />{t('actions.refreshCapabilities')}
        </Button>
      }
    >
      {!canRead ? (
        <section role="alert" className="rounded-2xl border border-neon-pink/30 bg-neon-pink/5 p-6"><h2 className="font-display text-xl text-white">{t('accessDeniedTitle')}</h2><p className="mt-2 font-mono text-sm text-muted-foreground">{t('accessDenied')}</p></section>
      ) : null}
      {canRead && statusQuery.isPending ? <div role="status" className="h-32 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-surface/35"><span className="sr-only">{t('loading')}</span></div> : null}
      {canRead && statusQuery.isError ? <LoadFailure error={statusQuery.error} retry={() => { void statusQuery.refetch(); }} /> : null}
      {statusQuery.data ? (
        <div className="space-y-5">
          {statusQuery.data.degraded_reason ? <p role="status" className="rounded-xl border border-amber-400/30 bg-amber-400/5 px-4 py-3 font-mono text-sm text-amber-200">{t('degraded', { reason: statusQuery.data.degraded_reason })}</p> : null}
          <div role="tablist" aria-label={t('tablist')} className="flex flex-wrap gap-2 rounded-2xl border border-grid-line/20 bg-terminal-bg/70 p-3">
            {SECTIONS.map((section) => {
              const enabled = statusQuery.data.capabilities[section.capability];
              const Icon = section.icon;
              return <button key={section.key} type="button" role="tab" aria-selected={activeSection === section.key} aria-controls={`operator-panel-${section.key}`} disabled={!enabled} onClick={() => setActiveSection(section.key)} className="inline-flex min-h-11 items-center rounded-xl border border-grid-line/25 px-3 py-2 font-mono text-xs uppercase tracking-[0.1em] text-white transition-colors hover:border-neon-cyan/50 focus-visible:outline-2 focus-visible:outline-neon-cyan disabled:cursor-not-allowed disabled:opacity-40 aria-selected:border-neon-cyan aria-selected:bg-neon-cyan/10 aria-selected:text-neon-cyan"><Icon className="mr-2 h-4 w-4" aria-hidden="true" />{t(`sections.${section.key}`)}</button>;
            })}
          </div>
          <div id={`operator-panel-${activeSection}`} role="tabpanel">
            {!activeEnabled ? <p role="status" className={panelClass}>{t('capabilityUnavailable')}</p> : null}
            {activeEnabled && activeSection === 'tags' ? <TagsConsole canWrite={canWrite} /> : null}
            {activeEnabled && activeSection === 'geoCheck' ? <GeoCheckConsole canWrite={canWrite} /> : null}
            {activeEnabled && activeSection === 'integrations' ? <NodeIntegrationsConsole canWrite={canWrite} /> : null}
            {activeEnabled && activeSection === 'sharedLists' ? <SharedListsConsole canWrite={canWrite} /> : null}
            {activeEnabled && activeSection === 'snippets' ? <RootSnippetsConsole canWrite={canWrite} /> : null}
          </div>
        </div>
      ) : null}
    </InfrastructurePageShell>
  );
}

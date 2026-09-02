'use client';

import { useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, RefreshCw, Save, ShieldAlert } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  partnerRemnawaveStatusApi,
  type PartnerIntegrationMetadataMutationRequest,
  type PartnerIntegrationMetadataMutationResponse,
  type PartnerProfileTagsMutationRequest,
  type PartnerProfileTagsMutationResponse,
  type PartnerRemnawaveMutationOutcome,
  type PartnerRemnawaveResource,
  type PartnerRemnawaveSafeMutation,
} from '@/lib/api/remnawave-status';

const WRITE_PERMISSION = 'remnawave_write';
const PROFILE_TAG_RE = /^[A-Z0-9_:]{1,36}$/;

type MutationErrorKey = 'conflict' | 'forbidden' | 'invalid' | 'notFound' | 'provider' | 'unknown';

type MutationAttempt<TBody> = {
  body: TBody;
  idempotencyKey: string;
};

function getHttpStatus(error: unknown): number | null {
  if (typeof error !== 'object' || error === null || !('response' in error)) {
    return null;
  }
  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === 'number' ? response.status : null;
}

function getMutationErrorKey(error: unknown): MutationErrorKey {
  const status = getHttpStatus(error);
  if (status === 403) return 'forbidden';
  if (status === 404) return 'notFound';
  if (status === 409) return 'conflict';
  if (status === 400 || status === 422) return 'invalid';
  if (status === 502 || status === 503 || status === 504) return 'provider';
  return 'unknown';
}

function canReplayWithSameKey(error: unknown): boolean {
  const status = getHttpStatus(error);
  return status === null || status === 408 || status >= 500;
}

function createIdempotencyKey(): string {
  if (typeof crypto === 'undefined' || typeof crypto.randomUUID !== 'function') {
    throw new Error('Secure browser UUID generation is unavailable');
  }
  return crypto.randomUUID();
}

function expectedSafeMutation(resource: PartnerRemnawaveResource): PartnerRemnawaveSafeMutation | null {
  if (resource.resource_type === 'profile') return 'profile_tags';
  if (resource.resource_type === 'integration') return 'integration_metadata';
  return null;
}

async function refreshResourceState(
  queryClient: ReturnType<typeof useQueryClient>,
  resource: PartnerRemnawaveResource,
): Promise<void> {
  await Promise.all([
    queryClient.invalidateQueries({
      queryKey: ['partner-remnawave-resources', resource.workspace_id],
    }),
    queryClient.invalidateQueries({
      queryKey: ['partner-remnawave-status', resource.workspace_id],
    }),
    queryClient.refetchQueries({
      queryKey: [
        'partner-remnawave-resource',
        resource.workspace_id,
        resource.resource_type,
        resource.resource_uuid,
      ],
      type: 'active',
    }),
  ]);
}

function MutationFeedback({
  error,
  isPending,
  onReplay,
  outcome,
}: {
  error: unknown;
  isPending: boolean;
  onReplay: (() => void) | null;
  outcome:
    | PartnerRemnawaveMutationOutcome<PartnerProfileTagsMutationResponse>
    | PartnerRemnawaveMutationOutcome<PartnerIntegrationMetadataMutationResponse>
    | null;
}) {
  const t = useTranslations('Dashboard.vpnServiceStatus.safeMutations');
  if (isPending) {
    return (
      <p role="status" className="mt-3 inline-flex items-center gap-2 font-mono text-sm text-muted-foreground">
        <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
        {t('submitting')}
      </p>
    );
  }
  if (error) {
    const errorKey = getMutationErrorKey(error);
    return (
      <div role="alert" className="mt-3 rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
        <p className="font-display text-sm text-white">{t(`errors.${errorKey}.title`)}</p>
        <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
          {t(`errors.${errorKey}.description`)}
        </p>
        {onReplay ? (
          <Button type="button" variant="outline" className="mt-3" onClick={onReplay}>
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
            {t('retrySameKey')}
          </Button>
        ) : null}
      </div>
    );
  }
  if (outcome?.kind === 'reconciliation_required') {
    return (
      <div role="status" className="mt-3 flex items-start gap-3 rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-300" aria-hidden="true" />
        <div>
          <p className="font-display text-sm text-white">{t('reconciliation.title')}</p>
          <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
            {t('reconciliation.description')}
          </p>
        </div>
      </div>
    );
  }
  if (outcome) {
    return (
      <div role="status" className="mt-3 flex items-start gap-3 rounded-xl border border-matrix-green/30 bg-matrix-green/5 p-4">
        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-matrix-green" aria-hidden="true" />
        <div>
          <p className="font-display text-sm text-white">{t('success.title')}</p>
          <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
            {t(outcome.kind === 'accepted' ? 'success.accepted' : 'success.completed')}
          </p>
        </div>
      </div>
    );
  }
  return null;
}

function ProfileTagsMutationForm({ resource }: { resource: PartnerRemnawaveResource }) {
  const t = useTranslations('Dashboard.vpnServiceStatus.safeMutations');
  const queryClient = useQueryClient();
  const [tagsInput, setTagsInput] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState<MutationAttempt<PartnerProfileTagsMutationRequest> | null>(null);
  const [outcome, setOutcome] = useState<PartnerRemnawaveMutationOutcome<PartnerProfileTagsMutationResponse> | null>(null);
  const mutation = useMutation({
    mutationFn: (nextAttempt: MutationAttempt<PartnerProfileTagsMutationRequest>) => (
      partnerRemnawaveStatusApi.updateProfileTags(
        resource.workspace_id,
        resource.resource_uuid,
        nextAttempt.body,
        nextAttempt.idempotencyKey,
      )
    ),
    retry: false,
    onSuccess: async (result) => {
      setAttempt(null);
      setOutcome(result);
      await refreshResourceState(queryClient, resource);
    },
    onError: (error) => {
      const status = getHttpStatus(error);
      if (status !== null && status >= 400 && status < 500 && status !== 408) {
        setAttempt(null);
      }
    },
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mutation.isPending || outcome?.kind === 'reconciliation_required') return;
    setOutcome(null);
    const tags = tagsInput.trim() === ''
      ? []
      : tagsInput.split(',').map((tag) => tag.trim());
    if (tags.length > 10) {
      setValidationError(t('profile.validation.tooMany'));
      return;
    }
    if (new Set(tags).size !== tags.length) {
      setValidationError(t('profile.validation.duplicate'));
      return;
    }
    if (tags.some((tag) => !PROFILE_TAG_RE.test(tag))) {
      setValidationError(t('profile.validation.format'));
      return;
    }
    let idempotencyKey: string;
    try {
      idempotencyKey = createIdempotencyKey();
    } catch {
      setValidationError(t('secureUuidUnavailable'));
      return;
    }
    const nextAttempt = { body: { tags }, idempotencyKey };
    setValidationError(null);
    setOutcome(null);
    setAttempt(nextAttempt);
    mutation.mutate(nextAttempt);
  };
  const isReconciliationLocked = outcome?.kind === 'reconciliation_required';

  return (
    <form className="mt-4 rounded-xl border border-grid-line/20 bg-black/20 p-4" onSubmit={submit}>
      <h5 className="font-display text-sm text-white">{t('profile.title')}</h5>
      <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">{t('profile.description')}</p>
      <label htmlFor={`profile-tags-${resource.resource_uuid}`} className="mt-4 block font-mono text-xs text-foreground">
        {t('profile.label')}
      </label>
      <Input
        id={`profile-tags-${resource.resource_uuid}`}
        className="mt-2 font-mono"
        value={tagsInput}
        onChange={(event) => {
          setTagsInput(event.target.value);
          setValidationError(null);
        }}
        placeholder={t('profile.placeholder')}
        aria-invalid={validationError !== null}
        aria-describedby={`profile-tags-help-${resource.resource_uuid}`}
        disabled={mutation.isPending || (attempt !== null && mutation.isError) || isReconciliationLocked}
        autoComplete="off"
      />
      <p id={`profile-tags-help-${resource.resource_uuid}`} className="mt-2 font-mono text-xs leading-5 text-muted-foreground">
        {validationError ?? t('profile.help')}
      </p>
      <Button
        type="submit"
        className="mt-3"
        disabled={mutation.isPending || (attempt !== null && mutation.isError) || isReconciliationLocked}
      >
        <Save className="mr-2 h-4 w-4" aria-hidden="true" />
        {t('profile.submit')}
      </Button>
      <MutationFeedback
        error={mutation.error}
        isPending={mutation.isPending}
        outcome={outcome}
        onReplay={attempt && mutation.isError && canReplayWithSameKey(mutation.error)
          ? () => mutation.mutate(attempt)
          : null}
      />
    </form>
  );
}

function IntegrationMetadataMutationForm({ resource }: { resource: PartnerRemnawaveResource }) {
  const t = useTranslations('Dashboard.vpnServiceStatus.safeMutations');
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [clearDescription, setClearDescription] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState<MutationAttempt<PartnerIntegrationMetadataMutationRequest> | null>(null);
  const [outcome, setOutcome] = useState<PartnerRemnawaveMutationOutcome<PartnerIntegrationMetadataMutationResponse> | null>(null);
  const mutation = useMutation({
    mutationFn: (nextAttempt: MutationAttempt<PartnerIntegrationMetadataMutationRequest>) => (
      partnerRemnawaveStatusApi.updateIntegrationMetadata(
        resource.workspace_id,
        resource.resource_uuid,
        nextAttempt.body,
        nextAttempt.idempotencyKey,
      )
    ),
    retry: false,
    onSuccess: async (result) => {
      setAttempt(null);
      setOutcome(result);
      if (result.kind === 'completed') {
        setName(result.value.name);
        setDescription(result.value.description ?? '');
        setClearDescription(false);
      }
      await refreshResourceState(queryClient, resource);
    },
    onError: (error) => {
      const status = getHttpStatus(error);
      if (status !== null && status >= 400 && status < 500 && status !== 408) {
        setAttempt(null);
      }
    },
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (mutation.isPending || outcome?.kind === 'reconciliation_required') return;
    setOutcome(null);
    const trimmedName = name.trim();
    const trimmedDescription = description.trim();
    const body: PartnerIntegrationMetadataMutationRequest = {};
    if (trimmedName !== '') body.name = trimmedName;
    if (clearDescription) body.description = null;
    else if (trimmedDescription !== '') body.description = trimmedDescription;
    if (Object.keys(body).length === 0) {
      setValidationError(t('integration.validation.required'));
      return;
    }
    if (typeof body.name === 'string' && (body.name.length < 2 || body.name.length > 30)) {
      setValidationError(t('integration.validation.name'));
      return;
    }
    if (typeof body.description === 'string' && body.description.length > 255) {
      setValidationError(t('integration.validation.description'));
      return;
    }
    let idempotencyKey: string;
    try {
      idempotencyKey = createIdempotencyKey();
    } catch {
      setValidationError(t('secureUuidUnavailable'));
      return;
    }
    const nextAttempt = { body, idempotencyKey };
    setValidationError(null);
    setOutcome(null);
    setAttempt(nextAttempt);
    mutation.mutate(nextAttempt);
  };
  const inputsLocked = mutation.isPending
    || (attempt !== null && mutation.isError)
    || outcome?.kind === 'reconciliation_required';

  return (
    <form className="mt-4 rounded-xl border border-grid-line/20 bg-black/20 p-4" onSubmit={submit}>
      <h5 className="font-display text-sm text-white">{t('integration.title')}</h5>
      <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">{t('integration.description')}</p>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div>
          <label htmlFor={`integration-name-${resource.resource_uuid}`} className="block font-mono text-xs text-foreground">
            {t('integration.nameLabel')}
          </label>
          <Input
            id={`integration-name-${resource.resource_uuid}`}
            className="mt-2 font-mono"
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              setValidationError(null);
            }}
            maxLength={30}
            disabled={inputsLocked}
            aria-invalid={validationError !== null}
            aria-describedby={`integration-metadata-help-${resource.resource_uuid}`}
            autoComplete="off"
          />
        </div>
        <div>
          <label htmlFor={`integration-description-${resource.resource_uuid}`} className="block font-mono text-xs text-foreground">
            {t('integration.descriptionLabel')}
          </label>
          <Input
            id={`integration-description-${resource.resource_uuid}`}
            className="mt-2 font-mono"
            value={description}
            onChange={(event) => {
              setDescription(event.target.value);
              setValidationError(null);
            }}
            maxLength={255}
            disabled={inputsLocked || clearDescription}
            aria-invalid={validationError !== null}
            aria-describedby={`integration-metadata-help-${resource.resource_uuid}`}
            autoComplete="off"
          />
        </div>
      </div>
      <label className="mt-3 flex min-h-11 items-center gap-3 font-mono text-xs text-muted-foreground">
        <input
          type="checkbox"
          checked={clearDescription}
          onChange={(event) => {
            setClearDescription(event.target.checked);
            setValidationError(null);
          }}
          disabled={inputsLocked}
          className="h-4 w-4 rounded border-grid-line/40 bg-terminal-bg text-neon-cyan focus-visible:ring-2 focus-visible:ring-neon-cyan"
        />
        {t('integration.clearDescription')}
      </label>
      <p
        id={`integration-metadata-help-${resource.resource_uuid}`}
        aria-live="polite"
        className="mt-2 font-mono text-xs leading-5 text-muted-foreground"
      >
        {validationError ?? t('integration.help')}
      </p>
      <Button type="submit" className="mt-3" disabled={inputsLocked}>
        <Save className="mr-2 h-4 w-4" aria-hidden="true" />
        {t('integration.submit')}
      </Button>
      <MutationFeedback
        error={mutation.error}
        isPending={mutation.isPending}
        outcome={outcome}
        onReplay={attempt && mutation.isError && canReplayWithSameKey(mutation.error)
          ? () => mutation.mutate(attempt)
          : null}
      />
    </form>
  );
}

export function PartnerRemnawaveSafeMutationPanel({
  resource,
  roleCanWrite,
}: {
  resource: PartnerRemnawaveResource;
  roleCanWrite: boolean;
}) {
  const t = useTranslations('Dashboard.vpnServiceStatus.safeMutations');
  const expectedMutation = expectedSafeMutation(resource);
  if (expectedMutation === null) return null;
  const exactGrantCanWrite = resource.effective_permissions.includes(WRITE_PERMISSION);
  const mutationIsAdvertised = resource.available_operations.includes('mutate_resource')
    && resource.safe_mutations.includes(expectedMutation);
  if (!roleCanWrite || !exactGrantCanWrite || !mutationIsAdvertised) {
    return (
      <div role="note" className="mt-4 flex items-start gap-3 rounded-xl border border-grid-line/25 bg-terminal-bg/40 p-4">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-muted-foreground" aria-hidden="true" />
        <div>
          <p className="font-display text-sm text-white">{t('permission.title')}</p>
          <p className="mt-2 font-mono text-xs leading-5 text-muted-foreground">{t('permission.description')}</p>
        </div>
      </div>
    );
  }
  return expectedMutation === 'profile_tags'
    ? <ProfileTagsMutationForm resource={resource} />
    : <IntegrationMetadataMutationForm resource={resource} />;
}

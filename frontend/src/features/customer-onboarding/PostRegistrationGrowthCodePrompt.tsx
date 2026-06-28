'use client';

import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { CheckCircle2, Loader2, RefreshCw, ShieldCheck, TicketCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { CyberInput } from '@/features/auth/components';
import { useRouter } from '@/i18n/navigation';
import { getApiErrorMessage } from '@/lib/api/error-message';
import {
  CUSTOMER_ONBOARDING_CURRENT_QUERY_KEY,
  customerOnboardingApi,
  type CustomerOnboardingApplyResponse,
  type CustomerOnboardingPreviewResponse,
  type CustomerOnboardingSkipResponse,
} from './api';
import { ConnectionBootstrapPanel } from './ConnectionBootstrapPanel';
import { normalizeOnboardingDestination } from './routing';

type OnboardingSurface = 'web' | 'miniapp';

type OnboardingMutationResult =
  | CustomerOnboardingApplyResponse
  | CustomerOnboardingSkipResponse;

type SafeApplyDetails = CustomerOnboardingApplyResponse & {
  entitlement?: Record<string, unknown> | null;
  child_invites?: Record<string, unknown> | null;
};

function normalizeCodeInput(value: string): string {
  return value.trim().toUpperCase();
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function readNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim() && Number.isFinite(Number(value))) {
    return Number(value);
  }
  return null;
}

function createIdempotencyKey(prefix: string): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}:${crypto.randomUUID()}`;
  }
  return `${prefix}:${Date.now()}:${Math.random().toString(16).slice(2)}`;
}

function getResultMessageKey(messageKey: string): string {
  if (messageKey.includes('registration_access_token')) {
    return 'messages.registrationAccessTokenRejected';
  }
  if (messageKey.includes('state_unavailable')) {
    return 'messages.stateUnavailable';
  }
  if (messageKey.includes('flow_token')) {
    return 'messages.flowTokenExpired';
  }
  if (messageKey.includes('gift')) {
    return 'messages.giftRedeemed';
  }
  if (messageKey.includes('invite')) {
    return 'messages.inviteRedeemed';
  }
  if (messageKey.includes('promo') || messageKey.includes('checkout')) {
    return 'messages.promoStaged';
  }
  if (messageKey.includes('not_found')) {
    return 'messages.codeNotFound';
  }
  if (messageKey.includes('expired')) {
    return 'messages.codeExpired';
  }
  if (messageKey.includes('already') || messageKey.includes('conflict')) {
    return 'messages.codeConflict';
  }
  return 'messages.completed';
}

function shouldShowConnectionPanel(result: CustomerOnboardingApplyResponse): boolean {
  return result.status === 'completed' && result.connection_required === true;
}

function getPreviewMessageKey(preview: CustomerOnboardingPreviewResponse): string {
  if (preview.status === 'ambiguous') {
    return 'preview.ambiguous';
  }
  if (preview.status === 'not_found') {
    return 'preview.notFound';
  }
  if (preview.status === 'wrong_context') {
    return preview.next_action === 'stage_for_checkout'
      ? 'preview.promoCheckout'
      : 'preview.wrongContext';
  }
  if (preview.status === 'not_eligible') {
    return 'preview.notEligible';
  }
  if (preview.status === 'expired') {
    return 'preview.expired';
  }
  if (preview.status === 'already_used') {
    return 'preview.alreadyUsed';
  }
  if (preview.status === 'blocked') {
    return 'preview.blocked';
  }
  if (preview.detected_code_type === 'promo') {
    return preview.next_action === 'stage_for_checkout'
      ? 'preview.promoCheckout'
      : 'preview.promo';
  }
  if (preview.detected_code_type === 'invite') {
    return 'preview.invite';
  }
  if (preview.detected_code_type === 'gift') {
    return 'preview.gift';
  }
  if (preview.detected_code_type === 'referral') {
    return 'preview.referral';
  }
  if (preview.detected_code_type === 'partner') {
    return 'preview.partner';
  }
  return 'preview.available';
}

function getPreviewClassName(preview: CustomerOnboardingPreviewResponse): string {
  if (preview.status === 'ambiguous' || preview.status === 'blocked') {
    return 'rounded-lg border border-red-500/35 bg-red-500/10 p-3 text-sm text-red-100';
  }
  if (
    preview.status === 'wrong_context'
    || preview.status === 'not_eligible'
    || preview.status === 'expired'
    || preview.status === 'already_used'
    || preview.status === 'not_found'
  ) {
    return 'rounded-lg border border-amber-400/35 bg-amber-400/10 p-3 text-sm text-amber-100';
  }
  return 'rounded-lg border border-neon-cyan/35 bg-neon-cyan/10 p-3 text-sm text-neon-cyan';
}

export function PostRegistrationGrowthCodePrompt({
  surface = 'web',
}: {
  surface?: OnboardingSurface;
}) {
  const t = useTranslations('Auth.onboarding');
  const router = useRouter();
  const queryClient = useQueryClient();
  const codeInputRef = useRef<HTMLInputElement>(null);
  const applyAttemptRef = useRef<{ code: string; key: string } | null>(null);
  const skipIdempotencyKeyRef = useRef<string | null>(null);
  const [code, setCode] = useState('');
  const [debouncedPreviewCode, setDebouncedPreviewCode] = useState('');
  const [feedback, setFeedback] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);
  const [connectionRequested, setConnectionRequested] = useState(false);
  const [lastApplyResult, setLastApplyResult] = useState<SafeApplyDetails | null>(null);

  const fallbackDestination = surface === 'miniapp' ? '/miniapp/home' : '/dashboard';

  const currentQuery = useQuery({
    queryKey: CUSTOMER_ONBOARDING_CURRENT_QUERY_KEY,
    queryFn: async () => {
      const { data } = await customerOnboardingApi.current();
      return data;
    },
    retry: 1,
    staleTime: 10_000,
  });

  const current = currentQuery.data;
  const previewQuery = useQuery({
    queryKey: [
      'customer-onboarding',
      'growth-code-preview',
      current?.flow_token ?? null,
      debouncedPreviewCode,
    ],
    queryFn: async () => {
      const { data } = await customerOnboardingApi.previewGrowthCode({
        code: debouncedPreviewCode,
        flow_token: current?.flow_token ?? null,
      });
      return data;
    },
    enabled: Boolean(current?.flow_token && debouncedPreviewCode),
    retry: false,
    staleTime: 0,
  });
  const previewBlocksApply = previewQuery.data?.status === 'ambiguous';
  const canSubmit =
    Boolean(current?.flow_token)
    && normalizeCodeInput(code).length > 0
    && !previewBlocksApply;
  const allowedCodeTypes = useMemo(() => {
    const allowed = current?.allowed_code_types ?? [];
    if (allowed.length === 0) {
      return t('allowedAny');
    }
    const labels = {
      gift: t('codeTypes.gift'),
      invite: t('codeTypes.invite'),
      promo: t('codeTypes.promo'),
    };
    return allowed.map((codeType) => labels[codeType]).join(', ');
  }, [current?.allowed_code_types, t]);

  const invalidateOnboardingSideEffects = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: CUSTOMER_ONBOARDING_CURRENT_QUERY_KEY }),
      queryClient.invalidateQueries({ queryKey: ['client-capabilities'] }),
      queryClient.invalidateQueries({ queryKey: ['growth', 'invites'] }),
      queryClient.invalidateQueries({ queryKey: ['growth', 'gifts'] }),
      queryClient.invalidateQueries({ queryKey: ['current-entitlements'] }),
      queryClient.invalidateQueries({ queryKey: ['current-service-state'] }),
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] }),
      queryClient.invalidateQueries({ queryKey: ['payments', 'history'] }),
      queryClient.invalidateQueries({ queryKey: ['miniapp-bootstrap'] }),
      queryClient.invalidateQueries({ queryKey: ['miniapp-offers'] }),
      queryClient.resetQueries({ queryKey: ['miniapp-config'], exact: true }),
    ]);
  };

  const completeFlow = async (result: OnboardingMutationResult) => {
    await invalidateOnboardingSideEffects();
    const destination = normalizeOnboardingDestination(result.next_destination, surface);
    router.replace(destination);
  };

  const getApplyIdempotencyKey = (normalizedCode: string): string => {
    if (applyAttemptRef.current?.code === normalizedCode) {
      return applyAttemptRef.current.key;
    }

    const key = createIdempotencyKey('onboarding-apply');
    applyAttemptRef.current = { code: normalizedCode, key };
    return key;
  };

  const getSkipIdempotencyKey = (): string => {
    if (!skipIdempotencyKeyRef.current) {
      skipIdempotencyKeyRef.current = createIdempotencyKey('onboarding-skip');
    }

    return skipIdempotencyKeyRef.current;
  };

  const applyMutation = useMutation({
    mutationFn: async () => {
      const normalizedCode = normalizeCodeInput(code);
      const { data } = await customerOnboardingApi.applyGrowthCode({
        code: normalizedCode,
        flow_token: current?.flow_token ?? null,
        idempotency_key: getApplyIdempotencyKey(normalizedCode),
        source_surface: surface,
      });
      return data;
    },
    onSuccess: async (result) => {
      const showConnection = shouldShowConnectionPanel(result);
      setLastApplyResult(result as SafeApplyDetails);
      setFeedback({
        kind: 'success',
        message: t(getResultMessageKey(result.message_key), {
          code: result.masked_code ?? t('maskedCodeFallback'),
        }),
      });
      if (showConnection) {
        setConnectionRequested(true);
        await invalidateOnboardingSideEffects();
        return;
      }
      await completeFlow(result);
    },
    onError: (error) => {
      setFeedback({
        kind: 'error',
        message: getApiErrorMessage(error, t('messages.applyFailed')),
      });
      codeInputRef.current?.focus();
    },
  });

  const skipMutation = useMutation({
    mutationFn: async () => {
      const { data } = await customerOnboardingApi.skipGrowthCode({
        flow_token: current?.flow_token ?? null,
        idempotency_key: getSkipIdempotencyKey(),
      });
      return data;
    },
    onSuccess: async (result) => {
      setLastApplyResult(null);
      setFeedback({
        kind: 'success',
        message: t('messages.skipped'),
      });
      await completeFlow(result);
    },
    onError: (error) => {
      setFeedback({
        kind: 'error',
        message: getApiErrorMessage(error, t('messages.skipFailed')),
      });
    },
  });

  const shouldRenderConnectionPanel = connectionRequested || current?.connection_required === true;
  const activationRows = useMemo(() => {
    if (!lastApplyResult) {
      return [];
    }

    const rows: string[] = [];
    const entitlement = isRecord(lastApplyResult.entitlement) ? lastApplyResult.entitlement : null;
    if (entitlement) {
      const displayName = readString(entitlement.display_name)
        ?? readString(entitlement.plan_code)
        ?? readString(entitlement.plan_uuid);
      if (displayName) {
        rows.push(t('activation.plan', { plan: displayName }));
      }

      const periodDays = readNumber(entitlement.period_days);
      if (periodDays !== null && periodDays > 0) {
        rows.push(t('activation.period', { days: periodDays }));
      }

      const deviceLimit = readNumber(entitlement.device_limit);
      if (deviceLimit !== null && deviceLimit > 0) {
        rows.push(t('activation.devices', { count: deviceLimit }));
      }

      const trafficLabel = readString(entitlement.display_traffic_label);
      if (trafficLabel) {
        rows.push(t('activation.traffic', { traffic: trafficLabel }));
      }
    }

    const childInvites = isRecord(lastApplyResult.child_invites) ? lastApplyResult.child_invites : null;
    if (childInvites) {
      const generatedCount = readNumber(childInvites.generated_count);
      const availableCount = readNumber(childInvites.available_count);
      if (generatedCount !== null && generatedCount > 0) {
        rows.push(t('activation.childInvites', {
          count: generatedCount,
          available: availableCount ?? generatedCount,
        }));
      }
    }

    return rows;
  }, [lastApplyResult, t]);

  useEffect(() => {
    if (!currentQuery.isSuccess || !current) {
      return;
    }
    if (
      !shouldRenderConnectionPanel
      && (!current.required || current.status === 'completed' || current.status === 'skipped')
    ) {
      router.replace(fallbackDestination);
    }
  }, [shouldRenderConnectionPanel, current, currentQuery.isSuccess, fallbackDestination, router]);

  useEffect(() => {
    const normalizedCode = normalizeCodeInput(code);
    if (applyAttemptRef.current && applyAttemptRef.current.code !== normalizedCode) {
      applyAttemptRef.current = null;
    }

    const timeoutId = window.setTimeout(() => {
      setDebouncedPreviewCode(normalizedCode);
    }, normalizedCode ? 400 : 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [code]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFeedback(null);
    setLastApplyResult(null);
    if (!canSubmit || applyMutation.isPending || skipMutation.isPending) {
      return;
    }
    applyMutation.mutate();
  };

  const isBusy = currentQuery.isLoading || applyMutation.isPending || skipMutation.isPending;

  return (
    <section
      aria-labelledby="post-registration-onboarding-title"
      className="mx-auto flex min-h-[calc(100dvh-10rem)] w-full max-w-3xl items-center justify-center"
    >
      <div className="w-full rounded-lg border border-grid-line/50 bg-terminal-bg/80 p-5 shadow-[0_0_30px_rgba(0,255,255,0.08)] md:p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border border-neon-cyan/30 bg-neon-cyan/10">
            <ShieldCheck className="h-5 w-5 text-neon-cyan" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon-cyan">
              {t('eyebrow')}
            </p>
            <h1
              id="post-registration-onboarding-title"
              className="mt-2 font-display text-2xl uppercase text-foreground md:text-3xl"
            >
              {t('title')}
            </h1>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              {t('description')}
            </p>
          </div>
        </div>

        <div className="mt-6 rounded-lg border border-grid-line/40 bg-black/20 p-4">
          <div className="flex items-start gap-3">
            <TicketCheck className="mt-0.5 h-4 w-4 shrink-0 text-neon-purple" aria-hidden="true" />
            <div className="min-w-0 text-sm text-muted-foreground">
              <p className="font-mono text-xs uppercase tracking-[0.14em] text-foreground">
                {t('allowedLabel')}
              </p>
              <p className="mt-1">{allowedCodeTypes}</p>
            </div>
          </div>
        </div>

        {shouldRenderConnectionPanel ? (
          <div className="mt-6 space-y-4">
            {activationRows.length > 0 ? (
              <div
                className="rounded-lg border border-matrix-green/35 bg-matrix-green/10 p-4 text-sm text-matrix-green"
                role="status"
              >
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  <div className="min-w-0">
                    <p className="font-mono text-xs uppercase tracking-[0.14em] text-foreground">
                      {t('activation.title')}
                    </p>
                    <ul className="mt-2 space-y-1">
                      {activationRows.map((row) => (
                        <li key={row}>{row}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ) : null}
            <ConnectionBootstrapPanel surface={surface} />
          </div>
        ) : currentQuery.isLoading ? (
          <div className="mt-6 flex items-center gap-3 rounded-lg border border-grid-line/40 p-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin text-neon-cyan" aria-hidden="true" />
            {t('loading')}
          </div>
        ) : currentQuery.isError ? (
          <div className="mt-6 rounded-lg border border-yellow-500/40 bg-yellow-500/10 p-4">
            <p className="text-sm text-yellow-200" role="alert">
              {t('messages.stateUnavailable')}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Button
                type="button"
                onClick={() => void currentQuery.refetch()}
                className="bg-neon-cyan text-black hover:bg-neon-cyan/90"
              >
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('retry')}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.replace(fallbackDestination)}
              >
                {t('continue')}
              </Button>
            </div>
          </div>
        ) : current?.required ? (
          <form onSubmit={handleSubmit} className="mt-6 space-y-5">
            <CyberInput
              ref={codeInputRef}
              label={t('codeLabel')}
              type="text"
              value={code}
              onChange={(event) => {
                setCode(event.target.value.toUpperCase());
                if (feedback?.kind === 'error') {
                  setFeedback(null);
                }
              }}
              placeholder={t('codePlaceholder')}
              disabled={isBusy}
              autoComplete="one-time-code"
              aria-invalid={feedback?.kind === 'error'}
            />

            {normalizeCodeInput(code).length > 0 && current.flow_token ? (
              previewQuery.isLoading || debouncedPreviewCode !== normalizeCodeInput(code) ? (
                <div className="rounded-lg border border-neon-cyan/35 bg-neon-cyan/10 p-3 text-sm text-neon-cyan" role="status">
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    {t('preview.loading')}
                  </div>
                </div>
              ) : previewQuery.isError ? (
                <div className="rounded-lg border border-amber-400/35 bg-amber-400/10 p-3 text-sm text-amber-100" role="alert">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <span>{t('preview.networkError')}</span>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => void previewQuery.refetch()}
                      className="min-h-10"
                      magnetic={false}
                    >
                      <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                      {t('preview.retry')}
                    </Button>
                  </div>
                </div>
              ) : previewQuery.data ? (
                <div className={getPreviewClassName(previewQuery.data)} role={previewBlocksApply ? 'alert' : 'status'}>
                  <div className="flex items-start gap-2">
                    {previewQuery.data.accepted ? (
                      <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                    ) : null}
                    <div className="min-w-0">
                      <p>{t(getPreviewMessageKey(previewQuery.data))}</p>
                      {previewQuery.data.masked_code ? (
                        <p className="mt-1 font-mono text-xs opacity-75">
                          {t('preview.maskedCode', { code: previewQuery.data.masked_code })}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </div>
              ) : null
            ) : null}

            {feedback ? (
              <div
                role={feedback.kind === 'error' ? 'alert' : 'status'}
                className={
                  feedback.kind === 'error'
                    ? 'rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200'
                    : 'rounded-lg border border-matrix-green/40 bg-matrix-green/10 p-3 text-sm text-matrix-green'
                }
              >
                <div className="flex items-start gap-2">
                  {feedback.kind === 'success' ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                  ) : null}
                  <span>{feedback.message}</span>
                </div>
              </div>
            ) : null}

            {!current.flow_token ? (
              <p className="rounded-lg border border-yellow-500/40 bg-yellow-500/10 p-3 text-sm text-yellow-200">
                {t('messages.flowTokenExpired')}
              </p>
            ) : null}

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button
                type="submit"
                disabled={!canSubmit || isBusy}
                className="min-h-11 flex-1 bg-neon-cyan text-black hover:bg-neon-cyan/90"
              >
                {applyMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                ) : null}
                {t('apply')}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={isBusy || !current.flow_token}
                onClick={() => {
                  setFeedback(null);
                  skipMutation.mutate();
                }}
                className="min-h-11 flex-1"
              >
                {skipMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                ) : null}
                {t('skip')}
              </Button>
            </div>
          </form>
        ) : (
          <div className="mt-6 flex items-center gap-3 rounded-lg border border-grid-line/40 p-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin text-neon-cyan" aria-hidden="true" />
            {t('redirecting')}
          </div>
        )}
      </div>
    </section>
  );
}

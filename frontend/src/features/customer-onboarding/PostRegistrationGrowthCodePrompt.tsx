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
  type CustomerOnboardingSkipResponse,
} from './api';
import { normalizeOnboardingDestination } from './routing';

type OnboardingSurface = 'web' | 'miniapp';

type OnboardingMutationResult =
  | CustomerOnboardingApplyResponse
  | CustomerOnboardingSkipResponse;

function normalizeCodeInput(value: string): string {
  return value.trim().toUpperCase();
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

export function PostRegistrationGrowthCodePrompt({
  surface = 'web',
}: {
  surface?: OnboardingSurface;
}) {
  const t = useTranslations('Auth.onboarding');
  const router = useRouter();
  const queryClient = useQueryClient();
  const codeInputRef = useRef<HTMLInputElement>(null);
  const [code, setCode] = useState('');
  const [feedback, setFeedback] = useState<{ kind: 'success' | 'error'; message: string } | null>(null);

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
  const canSubmit = Boolean(current?.flow_token) && normalizeCodeInput(code).length > 0;
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

  const applyMutation = useMutation({
    mutationFn: async () => {
      const { data } = await customerOnboardingApi.applyGrowthCode({
        code: normalizeCodeInput(code),
        flow_token: current?.flow_token ?? null,
      });
      return data;
    },
    onSuccess: async (result) => {
      setFeedback({
        kind: 'success',
        message: t(getResultMessageKey(result.message_key), {
          code: result.masked_code ?? t('maskedCodeFallback'),
        }),
      });
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
      });
      return data;
    },
    onSuccess: async (result) => {
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

  useEffect(() => {
    if (!currentQuery.isSuccess || !current) {
      return;
    }
    if (!current.required || current.status === 'completed' || current.status === 'skipped') {
      router.replace(fallbackDestination);
    }
  }, [current, currentQuery.isSuccess, fallbackDestination, router]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFeedback(null);
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

        {currentQuery.isLoading ? (
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

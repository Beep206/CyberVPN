'use client';

import { FormEvent, useEffect, useId, useMemo, useState } from 'react';
import { AxiosError } from 'axios';
import {
  AlertCircle,
  Check,
  Loader2,
  LockKeyhole,
  RefreshCw,
  X,
} from 'lucide-react';
import { useLocale } from 'next-intl';
import { toIntlLocale } from '@/i18n/intl-locale';
import { cn } from '@/lib/utils';
import {
  privateCatalogApi,
  type PrivateCatalogPreflightOffer,
  type PrivateCatalogPreflightResponse,
} from '@/lib/api/private-catalog';

const MAX_GRANT_EXPIRY_TIMER_MS = 2_147_483_647;

type FeedbackTone = 'success' | 'warning' | 'error';
type PrivateOfferUnlockVariant = 'web' | 'miniapp' | 'pricing';
type PrivateOfferUnlockMode = 'select' | 'preview';

export type PrivateOfferSelection = {
  offerId: string | null;
  planId: string;
  displayName: string;
  durationDays: number;
  price: PrivateCatalogPreflightOffer['price'];
  entitlementSummary: PrivateCatalogPreflightOffer['entitlement_summary'];
  privateCatalogGrantId: string;
  grantExpiresAt: string;
};

export type PrivateOfferUnlockCopy = {
  title: string;
  description: string;
  codeLabel: string;
  codePlaceholder: string;
  unlockCta: string;
  unlockingCta: string;
  retryCta: string;
  clearCta: string;
  availableLabel: string;
  selectedLabel: string;
  selectCta: string;
  previewOnlyHint: string;
  validationError: string;
  noOffers: string;
  networkError: string;
  authorizationError: string;
  genericError: string;
  grantDegraded: string;
  grantExpired: string;
  unlocked: string;
  priceLabel: string;
  durationDays: (days: number) => string;
  expiresAt: (date: string) => string;
  devices: (count: number | string) => string;
  traffic: (label: string) => string;
  modes: (modes: string) => string;
  serverPool: (servers: string) => string;
  support: (support: string) => string;
};

type PrivateOfferTranslator = (
  key: string,
  values?: Record<string, string | number>,
) => string;

export function buildPrivateOfferUnlockCopy(t: PrivateOfferTranslator): PrivateOfferUnlockCopy {
  return {
    title: t('privateOffer.title'),
    description: t('privateOffer.description'),
    codeLabel: t('privateOffer.codeLabel'),
    codePlaceholder: t('privateOffer.codePlaceholder'),
    unlockCta: t('privateOffer.unlockCta'),
    unlockingCta: t('privateOffer.unlockingCta'),
    retryCta: t('privateOffer.retryCta'),
    clearCta: t('privateOffer.clearCta'),
    availableLabel: t('privateOffer.availableLabel'),
    selectedLabel: t('privateOffer.selectedLabel'),
    selectCta: t('privateOffer.selectCta'),
    previewOnlyHint: t('privateOffer.previewOnlyHint'),
    validationError: t('privateOffer.validationError'),
    noOffers: t('privateOffer.noOffers'),
    networkError: t('privateOffer.networkError'),
    authorizationError: t('privateOffer.authorizationError'),
    genericError: t('privateOffer.genericError'),
    grantDegraded: t('privateOffer.grantDegraded'),
    grantExpired: t('privateOffer.grantExpired'),
    unlocked: t('privateOffer.unlocked'),
    priceLabel: t('privateOffer.priceLabel'),
    durationDays: (days) => t('privateOffer.durationDays', { days }),
    expiresAt: (date) => t('privateOffer.expiresAt', { date }),
    devices: (count) => t('privateOffer.devices', { count }),
    traffic: (label) => t('privateOffer.traffic', { label }),
    modes: (modes) => t('privateOffer.modes', { modes }),
    serverPool: (servers) => t('privateOffer.serverPool', { servers }),
    support: (support) => t('privateOffer.support', { support }),
  };
}

type PrivateOfferUnlockProps = {
  storefrontKey: string;
  channel: 'web' | 'miniapp' | string;
  currency: string;
  copy: PrivateOfferUnlockCopy;
  selectedOffer?: PrivateOfferSelection | null;
  onSelectionChange?: (selection: PrivateOfferSelection | null) => void;
  mode?: PrivateOfferUnlockMode;
  variant?: PrivateOfferUnlockVariant;
  className?: string;
};

type FeedbackState = {
  tone: FeedbackTone;
  message: string;
};

function normalizeCodeInput(value: string): string {
  return value.trim().toUpperCase();
}

function getOfferKey(offer: PrivateCatalogPreflightOffer): string {
  return offer.offer_id || offer.plan_id;
}

function formatOfferPrice(
  locale: string,
  price: PrivateCatalogPreflightOffer['price'],
): string {
  const amount = Number(price.amount);
  if (!Number.isFinite(amount)) {
    return `${price.amount} ${price.currency}`;
  }

  try {
    return new Intl.NumberFormat(toIntlLocale(locale), {
      style: 'currency',
      currency: price.currency,
      maximumFractionDigits: amount % 1 === 0 ? 0 : 2,
    }).format(amount);
  } catch {
    return `${price.amount} ${price.currency}`;
  }
}

function formatGrantExpiry(locale: string, expiresAt: string): string {
  const date = new Date(expiresAt);
  if (Number.isNaN(date.getTime())) {
    return expiresAt;
  }

  try {
    return new Intl.DateTimeFormat(toIntlLocale(locale), {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  } catch {
    return expiresAt;
  }
}

function getEntitlementRows(
  summary: PrivateCatalogPreflightOffer['entitlement_summary'],
  copy: PrivateOfferUnlockCopy,
): string[] {
  const rows: string[] = [];
  const deviceLimit = summary.device_limit;
  const trafficLabel = summary.display_traffic_label;
  const connectionModes = summary.connection_modes;
  const serverPool = summary.server_pool;
  const support = summary.support_sla;

  if (
    (typeof deviceLimit === 'number' && Number.isFinite(deviceLimit))
    || typeof deviceLimit === 'string'
  ) {
    rows.push(copy.devices(deviceLimit));
  }

  if (typeof trafficLabel === 'string' && trafficLabel.trim()) {
    rows.push(copy.traffic(trafficLabel));
  }

  if (Array.isArray(connectionModes) && connectionModes.length > 0) {
    rows.push(copy.modes(connectionModes.map(String).join(' · ')));
  }

  if (Array.isArray(serverPool) && serverPool.length > 0) {
    rows.push(copy.serverPool(serverPool.map(String).join(' · ')));
  }

  if (typeof support === 'string' && support.trim()) {
    rows.push(copy.support(support));
  }

  return rows.slice(0, 4);
}

function isGrantExpired(expiresAt: string | null | undefined): boolean {
  if (!expiresAt) {
    return true;
  }

  const expiresAtMs = Date.parse(expiresAt);
  return !Number.isFinite(expiresAtMs) || expiresAtMs <= Date.now();
}

function classifyPreflightError(error: unknown, copy: PrivateOfferUnlockCopy): FeedbackState {
  if (error instanceof AxiosError) {
    if (error.response?.status === 401 || error.response?.status === 403) {
      return {
        tone: 'error',
        message: copy.authorizationError,
      };
    }

    if (!error.response) {
      return {
        tone: 'error',
        message: copy.networkError,
      };
    }
  }

  return {
    tone: 'error',
    message: copy.genericError,
  };
}

function variantClassName(variant: PrivateOfferUnlockVariant): string {
  if (variant === 'miniapp') {
    return 'miniapp-card rounded-[1.5rem] border p-4';
  }

  if (variant === 'pricing') {
    return 'rounded-[1.75rem] border border-border/70 bg-card/70 p-5 backdrop-blur-xl dark:border-white/10 dark:bg-black/45';
  }

  return 'cyber-card bg-terminal-bg p-4';
}

export function PrivateOfferUnlock({
  storefrontKey,
  channel,
  currency,
  copy,
  selectedOffer = null,
  onSelectionChange,
  mode = 'select',
  variant = 'web',
  className,
}: PrivateOfferUnlockProps) {
  const locale = useLocale();
  const headingId = useId();
  const inputId = useId();
  const feedbackId = useId();
  const [codeInput, setCodeInput] = useState('');
  const [lastSubmittedCode, setLastSubmittedCode] = useState('');
  const [response, setResponse] = useState<PrivateCatalogPreflightResponse | null>(null);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const [isPending, setIsPending] = useState(false);

  const grant = response?.private_catalog_grant ?? null;
  const grantExpired = grant ? isGrantExpired(grant.expires_at) : false;
  const offers = useMemo(() => {
    if (!response || !grant || grantExpired) {
      return [];
    }

    return response.private_offers.filter((offer) =>
      offer.plan_id
      && offer.quote_handoff.private_catalog_grant_id === grant.id
    );
  }, [grant, grantExpired, response]);

  const selectedOfferKey = selectedOffer
    ? selectedOffer.offerId || selectedOffer.planId
    : null;

  useEffect(() => {
    if (!grant) {
      return;
    }

    const expiresAtMs = Date.parse(grant.expires_at);
    if (!Number.isFinite(expiresAtMs)) {
      setFeedback({ tone: 'error', message: copy.grantDegraded });
      onSelectionChange?.(null);
      return;
    }

    const delay = expiresAtMs - Date.now();
    if (delay <= 0) {
      setFeedback({ tone: 'warning', message: copy.grantExpired });
      onSelectionChange?.(null);
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setFeedback({ tone: 'warning', message: copy.grantExpired });
      onSelectionChange?.(null);
    }, Math.min(delay, MAX_GRANT_EXPIRY_TIMER_MS));

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [copy.grantDegraded, copy.grantExpired, grant, onSelectionChange]);

  const clearPrivateOffer = () => {
    setCodeInput('');
    setLastSubmittedCode('');
    setResponse(null);
    setFeedback(null);
    onSelectionChange?.(null);
  };

  const handleCodeInputChange = (value: string) => {
    const nextValue = value.toUpperCase();
    setCodeInput(nextValue);

    if (lastSubmittedCode && normalizeCodeInput(nextValue) !== lastSubmittedCode) {
      setLastSubmittedCode('');
      setResponse(null);
      setFeedback(null);
      onSelectionChange?.(null);
    }
  };

  const handleSubmit = async (event?: FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    const normalizedCode = normalizeCodeInput(codeInput);

    if (!normalizedCode) {
      setFeedback({
        tone: 'error',
        message: copy.validationError,
      });
      return;
    }

    setIsPending(true);
    setResponse(null);
    setFeedback(null);
    setCodeInput(normalizedCode);
    setLastSubmittedCode(normalizedCode);
    onSelectionChange?.(null);

    try {
      const preflightResponse = await privateCatalogApi.preflight({
        codes: [{ code: normalizedCode, client_slot_id: 'private-offer' }],
        storefront_key: storefrontKey,
        channel,
        currency,
      });
      const data = preflightResponse.data;
      const privateGrant = data.private_catalog_grant;
      const privateOffers = privateGrant && !isGrantExpired(privateGrant.expires_at)
        ? data.private_offers.filter((offer) =>
            offer.quote_handoff.private_catalog_grant_id === privateGrant.id
          )
        : [];

      setResponse(data);

      if (!privateGrant && data.private_offers.length > 0) {
        setFeedback({
          tone: 'error',
          message: copy.grantDegraded,
        });
        return;
      }

      if (privateGrant && isGrantExpired(privateGrant.expires_at)) {
        setFeedback({
          tone: 'warning',
          message: copy.grantExpired,
        });
        return;
      }

      if (privateOffers.length === 0) {
        setFeedback({
          tone: 'warning',
          message: copy.noOffers,
        });
        return;
      }

      setFeedback({
        tone: 'success',
        message: copy.unlocked,
      });
    } catch (error) {
      setFeedback(classifyPreflightError(error, copy));
    } finally {
      setIsPending(false);
    }
  };

  const handleSelectOffer = (offer: PrivateCatalogPreflightOffer) => {
    const handoffGrantId = offer.quote_handoff.private_catalog_grant_id;
    if (!grant || handoffGrantId !== grant.id || isGrantExpired(grant.expires_at)) {
      setFeedback({
        tone: 'error',
        message: grant && isGrantExpired(grant.expires_at)
          ? copy.grantExpired
          : copy.grantDegraded,
      });
      onSelectionChange?.(null);
      return;
    }

    onSelectionChange?.({
      offerId: offer.offer_id ?? null,
      planId: offer.plan_id,
      displayName: offer.display_name,
      durationDays: offer.duration_days,
      price: offer.price,
      entitlementSummary: offer.entitlement_summary,
      privateCatalogGrantId: handoffGrantId,
      grantExpiresAt: grant.expires_at,
    });
    setFeedback({
      tone: 'success',
      message: copy.selectedLabel,
    });
  };

  const feedbackToneClassName = feedback?.tone === 'success'
    ? 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green'
    : feedback?.tone === 'warning'
      ? 'border-amber-400/30 bg-amber-400/10 text-amber-200'
      : 'border-neon-pink/30 bg-neon-pink/10 text-neon-pink';

  return (
    <section
      aria-labelledby={headingId}
      className={cn(variantClassName(variant), className)}
    >
      <div className="flex items-start gap-3">
        <div className="rounded-xl border border-neon-cyan/30 bg-neon-cyan/10 p-2 text-neon-cyan">
          <LockKeyhole className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <h3
            id={headingId}
            className="font-display text-sm uppercase tracking-[0.14em] text-foreground dark:text-white"
          >
            {copy.title}
          </h3>
          <p className="mt-1 text-sm font-mono leading-relaxed text-muted-foreground">
            {copy.description}
          </p>
        </div>
      </div>

      <form className="mt-4 space-y-3" onSubmit={(event) => void handleSubmit(event)}>
        <label
          htmlFor={inputId}
          className="block font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground"
        >
          {copy.codeLabel}
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            id={inputId}
            type="text"
            value={codeInput}
            onChange={(event) => handleCodeInputChange(event.target.value)}
            placeholder={copy.codePlaceholder}
            disabled={isPending}
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            aria-invalid={feedback?.tone === 'error'}
            aria-describedby={feedback ? feedbackId : undefined}
            className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/30 px-3 py-3 font-mono text-sm uppercase text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/20 disabled:cursor-not-allowed disabled:opacity-60 dark:text-white"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isPending}
              className="inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-neon-cyan px-4 py-3 font-mono text-sm text-black transition-colors hover:bg-neon-cyan/90 focus:outline-none focus:ring-2 focus:ring-neon-cyan/50 disabled:cursor-not-allowed disabled:opacity-60 sm:flex-none"
            >
              {isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  {copy.unlockingCta}
                </>
              ) : (
                copy.unlockCta
              )}
            </button>
            {(response || selectedOffer || lastSubmittedCode) ? (
              <button
                type="button"
                onClick={clearPrivateOffer}
                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-white/10 px-3 text-muted-foreground transition-colors hover:border-white/25 hover:text-foreground focus:outline-none focus:ring-2 focus:ring-white/20 dark:hover:text-white"
                aria-label={copy.clearCta}
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            ) : null}
          </div>
        </div>
      </form>

      {feedback ? (
        <div
          id={feedbackId}
          role={feedback.tone === 'error' ? 'alert' : 'status'}
          className={cn('mt-3 rounded-xl border px-3 py-2 text-xs font-mono', feedbackToneClassName)}
        >
          <div className="flex items-start gap-2">
            {feedback.tone === 'success' ? (
              <Check className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            ) : (
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            )}
            <span>{feedback.message}</span>
            {feedback.tone === 'error' && lastSubmittedCode ? (
              <button
                type="button"
                onClick={() => void handleSubmit()}
                className="ms-auto inline-flex shrink-0 items-center gap-1 rounded border border-current/30 px-2 py-1 uppercase tracking-[0.12em] hover:bg-white/10 focus:outline-none focus:ring-2 focus:ring-current/30"
              >
                <RefreshCw className="h-3 w-3" aria-hidden="true" />
                {copy.retryCta}
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {offers.length > 0 ? (
        <div className="mt-4 space-y-3" role="list" aria-label={copy.availableLabel}>
          <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-neon-cyan/80">
            {copy.availableLabel}
          </p>
          {offers.map((offer) => {
            const offerKey = getOfferKey(offer);
            const isSelected =
              selectedOfferKey === offerKey
              && selectedOffer?.privateCatalogGrantId === grant?.id;
            const entitlementRows = getEntitlementRows(offer.entitlement_summary, copy);
            const expiresAt = grant
              ? copy.expiresAt(formatGrantExpiry(locale, grant.expires_at))
              : null;

            return (
              <div
                key={offerKey}
                role="listitem"
                className={cn(
                  'rounded-2xl border bg-black/25 p-4 transition-colors',
                  isSelected
                    ? 'border-neon-cyan bg-neon-cyan/10'
                    : 'border-white/10 bg-white/[0.03]',
                )}
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="font-display text-base uppercase tracking-[0.14em] text-foreground dark:text-white">
                        {offer.display_name}
                      </h4>
                      <span className="rounded-full border border-neon-cyan/30 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-neon-cyan">
                        {isSelected ? copy.selectedLabel : copy.availableLabel}
                      </span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs font-mono text-muted-foreground">
                      <span>{copy.durationDays(offer.duration_days)}</span>
                      <span>{copy.priceLabel}: {formatOfferPrice(locale, offer.price)}</span>
                      {expiresAt ? <span>{expiresAt}</span> : null}
                    </div>
                    {entitlementRows.length > 0 ? (
                      <ul className="mt-3 grid gap-1 text-xs font-mono text-muted-foreground sm:grid-cols-2">
                        {entitlementRows.map((row) => (
                          <li key={row}>{row}</li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                  {mode === 'select' ? (
                    <button
                      type="button"
                      onClick={() => handleSelectOffer(offer)}
                      disabled={grantExpired}
                      aria-pressed={isSelected}
                      className={cn(
                        'inline-flex min-h-10 shrink-0 items-center justify-center rounded-xl border px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] transition-colors focus:outline-none focus:ring-2 focus:ring-neon-cyan/40 disabled:cursor-not-allowed disabled:opacity-50',
                        isSelected
                          ? 'border-neon-cyan bg-neon-cyan text-black'
                          : 'border-neon-cyan/50 bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan/20',
                      )}
                    >
                      {isSelected ? copy.selectedLabel : copy.selectCta}
                    </button>
                  ) : (
                    <p className="max-w-[12rem] text-xs font-mono leading-relaxed text-muted-foreground">
                      {copy.previewOnlyHint}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}

'use client';

import { useCallback, useEffect, useId, useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCircle,
  Loader2,
  Plus,
  RotateCw,
  Tag,
  X,
  XCircle,
} from 'lucide-react';
import { AxiosError } from 'axios';
import { codesApi, type ResolveGrowthCodeResponse } from '@/lib/api/codes';
import {
  type CheckoutCodeFlow,
  getGrowthCodeResolutionMessageKey,
  getUnsupportedCheckoutCodeMessageKey,
  type UnsupportedCheckoutCodeMessageKey,
} from '@/features/customer-growth/lib/checkout-code-resolution';
import type { GrowthCodeBasketCopy } from '../lib/copy';

type GrowthCodeBasketStatus =
  | 'idle'
  | 'checking'
  | 'accepted'
  | 'rejected'
  | 'warning'
  | 'network_error';

type GrowthCodeBasketItem = {
  id: string;
  code: string;
  maskedCode: string;
  status: GrowthCodeBasketStatus;
  message: string;
  codeType: ResolveGrowthCodeResponse['code_type'];
  resolution?: ResolveGrowthCodeResponse;
};

export type GrowthCodeBasketPrimarySelection = {
  code: string;
  codeType: ResolveGrowthCodeResponse['code_type'];
  resolution: ResolveGrowthCodeResponse;
};

export type GrowthCodeBasketSummary = {
  acceptedCodes: string[];
  acceptedCount: number;
  pendingCount: number;
  warningCount: number;
  rejectedCount: number;
  networkErrorCount: number;
  totalCount: number;
  isDegraded: boolean;
};

type GrowthCodeBasketResolveContext = {
  storefrontKey?: string | null;
  planId?: string | null;
  amount?: number | null;
  channel: string;
  flow: CheckoutCodeFlow;
  partnerCodeEntryAllowed: boolean;
};

type GrowthCodeBasketProps = {
  copy: GrowthCodeBasketCopy;
  context: GrowthCodeBasketResolveContext;
  contextFingerprint: string;
  disabled?: boolean;
  maxCodes?: number;
  variant?: 'web' | 'miniapp';
  className?: string;
  onSelectionChange: (
    primary: GrowthCodeBasketPrimarySelection | null,
    summary: GrowthCodeBasketSummary,
  ) => void;
};

type ResolveItemInput = {
  itemId: string;
  code: string;
};

const DEFAULT_MAX_CODES = 5;

function normalizeGrowthCodeInput(value: string) {
  return value.trim().toUpperCase().slice(0, 64);
}

function maskGrowthCode(value: string) {
  if (value.length <= 6) {
    return value;
  }

  return `${value.slice(0, 4)}...${value.slice(-2)}`;
}

function buildEmptySummary(): GrowthCodeBasketSummary {
  return {
    acceptedCodes: [],
    acceptedCount: 0,
    pendingCount: 0,
    warningCount: 0,
    rejectedCount: 0,
    networkErrorCount: 0,
    totalCount: 0,
    isDegraded: false,
  };
}

function buildSummary(items: GrowthCodeBasketItem[]): GrowthCodeBasketSummary {
  const acceptedCodes = items
    .filter((item) => item.status === 'accepted' && item.resolution?.accepted)
    .map((item) => item.code);
  const acceptedCount = acceptedCodes.length;
  const pendingCount = items.filter((item) => item.status === 'checking').length;

  return {
    acceptedCodes,
    acceptedCount,
    pendingCount,
    warningCount: items.filter((item) => item.status === 'warning').length,
    rejectedCount: items.filter((item) => item.status === 'rejected').length,
    networkErrorCount: items.filter((item) => item.status === 'network_error').length,
    totalCount: items.length,
    isDegraded: false,
  };
}

function getStatusIcon(status: GrowthCodeBasketStatus) {
  if (status === 'checking') {
    return <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />;
  }
  if (status === 'accepted') {
    return <CheckCircle className="h-4 w-4" aria-hidden="true" />;
  }
  if (status === 'rejected' || status === 'network_error') {
    return <XCircle className="h-4 w-4" aria-hidden="true" />;
  }

  return <AlertTriangle className="h-4 w-4" aria-hidden="true" />;
}

function getStatusClassName(status: GrowthCodeBasketStatus) {
  if (status === 'accepted') {
    return 'border-matrix-green/30 bg-matrix-green/10 text-matrix-green';
  }
  if (status === 'rejected' || status === 'network_error') {
    return 'border-neon-pink/30 bg-neon-pink/10 text-neon-pink';
  }
  if (status === 'warning' || status === 'idle') {
    return 'border-amber-400/30 bg-amber-400/10 text-amber-100';
  }

  return 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan';
}

function getUnsupportedKey(
  resolution: ResolveGrowthCodeResponse,
  context: GrowthCodeBasketResolveContext,
): UnsupportedCheckoutCodeMessageKey | null {
  return getUnsupportedCheckoutCodeMessageKey({
    codeType: resolution.code_type,
    flow: context.flow,
    partnerCodeEntryAllowed: context.partnerCodeEntryAllowed,
  });
}

export function GrowthCodeBasket({
  copy,
  context,
  contextFingerprint,
  disabled = false,
  maxCodes = DEFAULT_MAX_CODES,
  variant = 'web',
  className = '',
  onSelectionChange,
}: GrowthCodeBasketProps) {
  const inputId = useId();
  const errorId = useId();
  const statusId = useId();
  const nextItemId = useRef(0);
  const contextFingerprintRef = useRef(contextFingerprint);
  const itemsRef = useRef<GrowthCodeBasketItem[]>([]);
  const [items, setItems] = useState<GrowthCodeBasketItem[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [formError, setFormError] = useState('');

  const notifySelection = useCallback((nextItems: GrowthCodeBasketItem[]) => {
    const summary = buildSummary(nextItems);
    const acceptedItems = nextItems.filter((item) => item.status === 'accepted' && item.resolution);
    const primaryItem = acceptedItems[0] ?? null;

    onSelectionChange(
      primaryItem && primaryItem.resolution
        ? {
            code: primaryItem.code,
            codeType: primaryItem.codeType,
            resolution: primaryItem.resolution,
          }
        : null,
      summary,
    );
  }, [onSelectionChange]);

  const commitItems = useCallback((
    updater: (currentItems: GrowthCodeBasketItem[]) => GrowthCodeBasketItem[],
  ) => {
    const nextItems = updater(itemsRef.current);
    itemsRef.current = nextItems;
    setItems(nextItems);
    notifySelection(nextItems);
  }, [notifySelection]);

  const resolveMutation = useMutation({
    mutationFn: async ({ code }: ResolveItemInput) => {
      const response = await codesApi.resolve({
        code,
        action_context: 'checkout',
        storefront_key: context.storefrontKey ?? undefined,
        plan_id: context.planId ?? undefined,
        amount: context.amount ?? undefined,
        channel: context.channel,
      });

      return response.data;
    },
  });

  const resolveItem = useCallback(async ({ itemId, code }: ResolveItemInput) => {
    const requestContextFingerprint = contextFingerprintRef.current;

    commitItems((currentItems) =>
      currentItems.map((item) =>
        item.id === itemId
          ? {
              ...item,
              status: 'checking',
              message: copy.status.checking,
              resolution: undefined,
            }
          : item,
      ),
    );

    try {
      const resolution = await resolveMutation.mutateAsync({ itemId, code });
      if (requestContextFingerprint !== contextFingerprintRef.current) {
        return;
      }

      const unsupportedKey = resolution.accepted
        ? getUnsupportedKey(resolution, context)
        : null;
      const status: GrowthCodeBasketStatus = resolution.accepted
        ? unsupportedKey
          ? 'warning'
          : 'accepted'
        : resolution.result === 'blocked_by_risk'
          ? 'warning'
          : 'rejected';
      const codeType = resolution.code_type ?? 'unknown';
      const message = unsupportedKey
        ? copy.unsupportedErrors[unsupportedKey]
        : resolution.accepted
          ? copy.status.accepted
          : copy.resolutionErrors[getGrowthCodeResolutionMessageKey(resolution)];

      commitItems((currentItems) =>
        currentItems.map((item) =>
          item.id === itemId
            ? {
                ...item,
                status,
                codeType: resolution.code_type,
                message: `${copy.codeTypes[codeType]}: ${message}`,
                resolution,
              }
            : item,
        ),
      );
    } catch (error) {
      if (requestContextFingerprint !== contextFingerprintRef.current) {
        return;
      }

      const message =
        error instanceof AxiosError && (error.response?.status === 401 || error.response?.status === 403)
          ? copy.resolutionErrors.requiresAuth
          : copy.networkError;

      commitItems((currentItems) =>
        currentItems.map((item) =>
          item.id === itemId
            ? {
                ...item,
                status: 'network_error',
                message,
                resolution: undefined,
              }
            : item,
        ),
      );
    }
  }, [commitItems, context, copy, resolveMutation]);

  useEffect(() => {
    if (contextFingerprintRef.current === contextFingerprint) {
      return;
    }

    contextFingerprintRef.current = contextFingerprint;
    if (itemsRef.current.length === 0) {
      return;
    }

    commitItems((currentItems) =>
      currentItems.map((item) => ({
        ...item,
        status: 'idle',
        message: copy.contextChanged,
        resolution: undefined,
      })),
    );
  }, [commitItems, contextFingerprint, copy.contextChanged]);

  const handleAdd = async () => {
    const normalizedCode = normalizeGrowthCodeInput(inputValue);
    setFormError('');

    if (disabled) {
      return;
    }
    if (!context.planId) {
      setFormError(copy.missingPlan);
      return;
    }
    if (!normalizedCode) {
      setFormError(copy.inputRequired);
      return;
    }
    if (itemsRef.current.length >= maxCodes) {
      setFormError(copy.maxReached);
      return;
    }
    if (itemsRef.current.some((item) => item.code === normalizedCode)) {
      setFormError(copy.duplicate);
      return;
    }

    const itemId = `code-slot-${nextItemId.current + 1}`;
    nextItemId.current += 1;
    const nextItem: GrowthCodeBasketItem = {
      id: itemId,
      code: normalizedCode,
      maskedCode: maskGrowthCode(normalizedCode),
      status: 'checking',
      message: copy.status.checking,
      codeType: null,
    };

    commitItems((currentItems) => [...currentItems, nextItem]);
    setInputValue('');
    await resolveItem({ itemId, code: normalizedCode });
  };

  const handleRemove = (itemId: string) => {
    setFormError('');
    commitItems((currentItems) => currentItems.filter((item) => item.id !== itemId));
  };

  const handleRetry = async (item: GrowthCodeBasketItem) => {
    setFormError('');
    await resolveItem({ itemId: item.id, code: item.code });
  };

  const summary = buildSummary(items);
  const inputDescribedBy = formError ? errorId : statusId;
  const isMiniApp = variant === 'miniapp';
  const containerClassName = isMiniApp
    ? `rounded-[1.5rem] border border-white/10 bg-black/25 p-4 ${className}`
    : `cyber-card bg-terminal-bg p-4 ${className}`;

  return (
    <section className={containerClassName} aria-labelledby={`${inputId}-title`}>
      <div className="mb-3 flex items-start gap-3">
        <div className="rounded-xl border border-neon-purple/30 bg-neon-purple/10 p-2 text-neon-purple">
          <Tag className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="min-w-0 flex-1">
          <h3
            id={`${inputId}-title`}
            className="font-display text-sm uppercase tracking-[0.14em] text-neon-purple"
          >
            {copy.title}
          </h3>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            {copy.description}
          </p>
          <p id={statusId} className="mt-2 text-[11px] font-mono uppercase tracking-[0.14em] text-white/45">
            {copy.maxCount}
          </p>
        </div>
      </div>

      <div className="flex gap-2">
        <label className="sr-only" htmlFor={inputId}>
          {copy.inputLabel}
        </label>
        <input
          id={inputId}
          type="text"
          value={inputValue}
          onChange={(event) => {
            setInputValue(normalizeGrowthCodeInput(event.target.value));
            setFormError('');
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter') {
              event.preventDefault();
              void handleAdd();
            }
          }}
          placeholder={copy.placeholder}
          maxLength={64}
          disabled={disabled || resolveMutation.isPending}
          aria-describedby={inputDescribedBy}
          aria-invalid={Boolean(formError)}
          className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/30 px-3 py-3 font-mono text-sm text-white outline-none transition-colors placeholder:text-white/35 focus:border-neon-cyan/60 disabled:cursor-not-allowed disabled:opacity-50"
        />
        <button
          type="button"
          onClick={() => void handleAdd()}
          disabled={disabled || resolveMutation.isPending || !inputValue.trim()}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-neon-cyan/50 bg-neon-cyan/20 px-3 py-3 font-mono text-sm text-neon-cyan transition-colors hover:bg-neon-cyan/30 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {resolveMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Plus className="h-4 w-4" aria-hidden="true" />
          )}
          <span className={isMiniApp ? 'sr-only' : undefined}>
            {resolveMutation.isPending ? copy.addingCta : copy.addCta}
          </span>
        </button>
      </div>

      {formError ? (
        <p id={errorId} role="alert" className="mt-2 text-xs font-mono text-neon-pink">
          {formError}
        </p>
      ) : null}

      <div className="mt-4 space-y-2" aria-live="polite" aria-atomic="false">
        {items.length === 0 ? (
          <div className="rounded-xl border border-dashed border-white/10 px-4 py-4 text-sm font-mono text-white/50">
            {copy.empty}
          </div>
        ) : (
          items.map((item) => {
            const isAcceptedQueued =
              item.status === 'accepted'
              && summary.acceptedCount > 1;

            return (
              <div
                key={item.id}
                className={`rounded-xl border px-3 py-3 ${getStatusClassName(item.status)}`}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 shrink-0">{getStatusIcon(item.status)}</div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-sm font-semibold">
                        {item.maskedCode}
                      </span>
                      <span className="rounded-full border border-current/25 px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.14em]">
                        {copy.status[item.status]}
                      </span>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed opacity-90">
                      {isAcceptedQueued
                        ? copy.acceptedQueued
                        : item.message}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    {item.status === 'idle' || item.status === 'network_error' ? (
                      <button
                        type="button"
                        onClick={() => void handleRetry(item)}
                        disabled={disabled || resolveMutation.isPending}
                        className="rounded-lg border border-current/30 p-2 transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
                        aria-label={`${copy.retryCta}: ${item.maskedCode}`}
                      >
                        <RotateCw className="h-4 w-4" aria-hidden="true" />
                      </button>
                    ) : null}
                    <button
                      type="button"
                      onClick={() => handleRemove(item.id)}
                      className="rounded-lg border border-current/30 p-2 transition-colors hover:bg-white/10"
                      aria-label={`${copy.removeCta}: ${item.maskedCode}`}
                    >
                      <X className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {summary.pendingCount > 0 ? (
        <p className="mt-3 text-xs font-mono text-neon-cyan">
          {copy.pendingCheckout}
        </p>
      ) : null}

      {summary.acceptedCount > 1 ? (
        <div className="mt-3 rounded-xl border border-amber-400/30 bg-amber-400/10 px-3 py-3 text-xs font-mono text-amber-100">
          {copy.degraded}
        </div>
      ) : null}
    </section>
  );
}

export function createEmptyGrowthCodeBasketSummary(): GrowthCodeBasketSummary {
  return buildEmptySummary();
}

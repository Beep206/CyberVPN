'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowUpRight, Store, Ticket, Waypoints } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';
import {
  publicCatalogApi,
  type PublicCommercialCatalog,
} from '@/lib/api/catalog';
import { plansApi } from '@/lib/api/plans';
import {
  storefrontApi,
  type StorefrontPreviewResponse,
} from '@/lib/api/storefront';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import type { PartnerResellerStorefront } from '@/features/partner-portal-state/lib/portal-state';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import {
  getPartnerResellerCapabilities,
  getPartnerResellerSurfaceMode,
} from '@/features/partner-operations/lib/advanced-operational-capabilities';
import { partnerPortalApi } from '@/lib/api/partner-portal';

const FIELD_CLASS_NAME = 'w-full rounded-xl border border-grid-line/25 bg-terminal-bg/70 px-4 py-3 text-sm font-mono text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-neon-cyan/50 focus:ring-2 focus:ring-neon-cyan/20';

function formatVoucherStatus(status: string) {
  return status.replaceAll('_', ' ');
}

interface ResellerStorefrontOption {
  key: string;
  label: string;
  currency: string;
  partnerCode?: string;
}

function getStorefrontKey(storefront: PartnerResellerStorefront) {
  return storefront.storefrontKey ?? storefront.id;
}

function toStorefrontOption(
  storefront: PartnerResellerStorefront,
): ResellerStorefrontOption {
  return {
    key: getStorefrontKey(storefront),
    label: storefront.label,
    currency: storefront.currency,
    partnerCode: storefront.partnerCode,
  };
}

function formatCatalogAmount(amount: string, currency: string) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(Number(amount));
}

function countBillingPeriods(catalog: PublicCommercialCatalog | null) {
  return catalog?.plans.reduce(
    (total, plan) => total + plan.billingPeriods.length,
    0,
  ) ?? 0;
}

function readErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback;
}

export function ResellerConsolePage() {
  const t = useTranslations('Partner.reseller');
  const portalT = useTranslations('Partner.portalState');
  const queryClient = useQueryClient();
  const { state, activeWorkspace } = usePartnerPortalRuntimeState();
  const mode = getPartnerResellerSurfaceMode(state);
  const capabilities = getPartnerResellerCapabilities(state);
  const activeWorkspaceId = activeWorkspace?.id ?? null;

  const [selectedPlanId, setSelectedPlanId] = useState('');
  const [voucherCount, setVoucherCount] = useState('10');
  const [recipientHint, setRecipientHint] = useState('');
  const [giftMessage, setGiftMessage] = useState('');
  const [issuedCodes, setIssuedCodes] = useState<string[]>([]);
  const [selectedStorefrontKey, setSelectedStorefrontKey] = useState('');
  const [actionFeedback, setActionFeedback] = useState<{
    tone: 'success' | 'error';
    message: string;
  } | null>(null);

  const storefrontOptions = useMemo(
    () => state.resellerStorefronts.map(toStorefrontOption),
    [state.resellerStorefronts],
  );
  const activeStorefrontOption =
    storefrontOptions.find((storefront) => storefront.key === selectedStorefrontKey)
    ?? storefrontOptions[0]
    ?? null;
  const effectiveStorefrontKey = activeStorefrontOption?.key ?? '';

  const plansQuery = useQuery({
    queryKey: ['partner-portal', 'reseller-voucher-plans'],
    queryFn: async () => {
      const response = await plansApi.list();
      return response.data;
    },
    staleTime: 60_000,
    retry: false,
  });

  const storefrontPreviewQuery = useQuery({
    queryKey: [
      'partner-portal',
      'reseller-storefront-preview',
      effectiveStorefrontKey,
      activeStorefrontOption?.partnerCode ?? null,
    ],
    queryFn: async () => {
      if (!activeStorefrontOption) {
        return null;
      }

      const response = await storefrontApi.previewContract(
        activeStorefrontOption.key,
        { partner_code: activeStorefrontOption.partnerCode ?? null },
      );
      return response.data;
    },
    enabled: Boolean(activeStorefrontOption),
    staleTime: 30_000,
    retry: false,
  });

  const catalogPreviewQuery = useQuery({
    queryKey: [
      'partner-portal',
      'reseller-catalog-preview',
      effectiveStorefrontKey,
      activeStorefrontOption?.currency ?? null,
    ],
    queryFn: async () => {
      if (!activeStorefrontOption) {
        return null;
      }

      const response = await publicCatalogApi.getCatalog({
        channel: 'web',
        currency: activeStorefrontOption.currency || undefined,
        storefrontKey: activeStorefrontOption.key,
        uiLocale: 'en-EN',
      });
      return response.data;
    },
    enabled: Boolean(activeStorefrontOption),
    staleTime: 30_000,
    retry: false,
  });

  const planOptions = useMemo(
    () => (plansQuery.data ?? []).map((plan) => ({
      id: plan.uuid,
      label: `${plan.display_name} · ${plan.duration_days}d`,
      hint: `${plan.plan_code || plan.name} · ${Number(plan.price_usd).toFixed(2)} USD`,
    })),
    [plansQuery.data],
  );

  const requestVoucherBatchMutation = useMutation({
    mutationFn: async () => {
      if (!activeWorkspaceId) {
        throw new Error(t('voucherRequest.workspaceRequired'));
      }
      if (!selectedPlanId) {
        throw new Error(t('voucherRequest.planRequired'));
      }

      return partnerPortalApi.requestWorkspaceResellerVoucherBatch(activeWorkspaceId, {
        plan_id: selectedPlanId,
        count: Number(voucherCount),
        recipient_hint: recipientHint.trim() || null,
        gift_message: giftMessage.trim() || null,
      });
    },
    onSuccess: async (response) => {
      if (activeWorkspaceId) {
        await queryClient.invalidateQueries({
          queryKey: ['partner-portal', 'workspace-reseller-voucher-batches', activeWorkspaceId],
        });
      }
      setIssuedCodes(response.data.issued_codes);
      setVoucherCount('10');
      setRecipientHint('');
      setGiftMessage('');
      setActionFeedback({
        tone: 'success',
        message: t('voucherRequest.success', {
          count: response.data.batch.issued_count,
        }),
      });
    },
    onError: (error) => {
      setActionFeedback({
        tone: 'error',
        message: error instanceof Error ? error.message : t('voucherRequest.error'),
      });
    },
  });

  return (
    <PartnerRouteGuard route="reseller" title={t('title')}>
      {(access) => {
        const canWrite = access === 'write' || access === 'admin';

        return (
          <section className="space-y-6">
            <header className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-[11px] font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                    {t('eyebrow')}
                  </p>
                  <h1 className="mt-2 text-2xl font-display tracking-[0.16em] text-white md:text-3xl">
                    {t('title')}
                  </h1>
                  <p className="mt-3 max-w-4xl text-sm font-mono leading-6 text-muted-foreground">
                    {t('subtitle')}
                  </p>
                </div>

                <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[360px]">
                  <div className="flex items-center justify-between gap-3">
                    <span>{t('summary.routeAccess')}</span>
                    <span className="text-neon-cyan">
                      {portalT(`routeAccess.${access}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.workspaceStatus')}</span>
                    <span className="text-foreground">
                      {portalT(`workspaceStatuses.${state.workspaceStatus}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.surfaceMode')}</span>
                    <span className="text-foreground">
                      {portalT(`resellerModes.${mode}`)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.storefronts')}</span>
                    <span className="text-foreground">{state.resellerStorefronts.length}</span>
                  </div>
                  <div className="mt-3 flex items-center justify-between gap-3">
                    <span>{t('summary.voucherBatches')}</span>
                    <span className="text-foreground">{state.resellerVoucherBatches.length}</span>
                  </div>
                </div>
              </div>
            </header>

            {actionFeedback ? (
              <div
                className={`rounded-2xl border px-4 py-3 text-sm font-mono ${
                  actionFeedback.tone === 'success'
                    ? 'border-matrix-green/35 bg-matrix-green/10 text-matrix-green'
                    : 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink'
                }`}
              >
                {actionFeedback.message}
              </div>
            ) : null}

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                  {t('snapshot.pricebook')}
                </p>
                <p className="mt-3 text-sm font-display uppercase tracking-[0.12em] text-white">
                  {state.resellerSnapshot.pricebookLabel || t('snapshot.notAvailable')}
                </p>
              </article>
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                  {t('snapshot.supportOwnership')}
                </p>
                <p className="mt-3 text-sm font-display uppercase tracking-[0.12em] text-white">
                  {state.resellerSnapshot.supportOwnership || t('snapshot.notAvailable')}
                </p>
              </article>
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                  {t('snapshot.customerScope')}
                </p>
                <p className="mt-3 text-sm font-display uppercase tracking-[0.12em] text-white">
                  {state.resellerSnapshot.customerScope || t('snapshot.notAvailable')}
                </p>
              </article>
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
                <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                  {t('snapshot.technicalHealth')}
                </p>
                <p className="mt-3 text-sm font-display uppercase tracking-[0.12em] text-white">
                  {state.resellerSnapshot.technicalHealth || t('snapshot.notAvailable')}
                </p>
              </article>
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
                <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                  <Store className="h-5 w-5 text-neon-cyan" />
                  <div>
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('storefronts.title')}
                    </h2>
                    <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                      {t('storefronts.description')}
                    </p>
                  </div>
                </div>

                <div className="mt-5 space-y-3">
                  {state.resellerStorefronts.map((storefront) => (
                    <article
                      key={storefront.id}
                      className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                    >
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                            {storefront.label}
                          </h3>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {storefront.domain} · {storefront.currency}
                          </p>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {t('storefronts.supportOwner', { value: storefront.supportOwner })}
                          </p>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {storefront.notes[0]}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {portalT(`resellerStorefrontStatuses.${storefront.status}`)}
                          </p>
                        </div>
                      </div>
                    </article>
                  ))}
                </div>
              </article>

              <div className="space-y-6">
                <ResellerCommercialPreviewPanel
                  catalog={catalogPreviewQuery.data ?? null}
                  contract={storefrontPreviewQuery.data ?? null}
                  error={catalogPreviewQuery.error ?? storefrontPreviewQuery.error}
                  isLoading={catalogPreviewQuery.isLoading || storefrontPreviewQuery.isLoading}
                  onSelectStorefront={setSelectedStorefrontKey}
                  selectedStorefrontKey={effectiveStorefrontKey}
                  storefronts={storefrontOptions}
                />

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <Waypoints className="h-5 w-5 text-neon-purple" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('capabilities.title')}
                    </h2>
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t(`modes.${mode}`)}
                  </p>
                  <ul className="mt-4 space-y-3">
                    {capabilities.map((capability) => (
                      <li
                        key={capability.key}
                        className="flex items-center justify-between gap-3 rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3"
                      >
                        <span className="text-sm font-mono text-foreground/90">
                          {t(`capabilities.items.${capability.key}`)}
                        </span>
                        <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                          {portalT(`operationalCapabilityAvailability.${capability.availability}`)}
                        </span>
                      </li>
                    ))}
                  </ul>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <div className="flex items-center gap-3">
                    <Ticket className="h-5 w-5 text-matrix-green" />
                    <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                      {t('voucherBatches.title')}
                    </h2>
                  </div>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {t('voucherBatches.description')}
                  </p>
                  <div className="mt-4 space-y-3">
                    {state.resellerVoucherBatches.length > 0 ? state.resellerVoucherBatches.map((batch) => (
                      <article
                        key={batch.batchId}
                        className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                      >
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div>
                            <h3 className="text-sm font-display uppercase tracking-[0.14em] text-white">
                              {t('voucherBatches.batchTitle', {
                                plan: batch.planFamily,
                                duration: batch.durationDays,
                              })}
                            </h3>
                            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                              {t('voucherBatches.batchStats', {
                                issued: batch.issuedCount,
                                redeemed: batch.redeemedCount,
                                available: batch.availableCount,
                              })}
                            </p>
                            {batch.expiresAt ? (
                              <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                                {t('voucherBatches.expiresAt', { value: batch.expiresAt })}
                              </p>
                            ) : null}
                          </div>
                          <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {formatVoucherStatus(batch.status)}
                          </p>
                        </div>
                        {batch.notes.length > 0 ? (
                          <ul className="mt-3 space-y-2 text-sm font-mono text-muted-foreground">
                            {batch.notes.map((note) => (
                              <li key={note}>{note}</li>
                            ))}
                          </ul>
                        ) : null}
                      </article>
                    )) : (
                      <p className="rounded-xl border border-dashed border-grid-line/25 bg-terminal-bg/55 p-4 text-sm font-mono leading-6 text-muted-foreground">
                        {t('voucherBatches.empty')}
                      </p>
                    )}
                  </div>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('voucherRequest.title')}
                  </h2>
                  <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                    {canWrite ? t('voucherRequest.description') : t('voucherRequest.readOnly')}
                  </p>
                  <div className="mt-4 space-y-3">
                    <label className="block space-y-2">
                      <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('voucherRequest.planLabel')}
                      </span>
                      <select
                        className={FIELD_CLASS_NAME}
                        value={selectedPlanId}
                        onChange={(event) => setSelectedPlanId(event.target.value)}
                        disabled={!canWrite || requestVoucherBatchMutation.isPending}
                      >
                        <option value="">{t('voucherRequest.planPlaceholder')}</option>
                        {planOptions.map((plan) => (
                          <option key={plan.id} value={plan.id}>
                            {plan.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    {selectedPlanId ? (
                      <p className="text-xs font-mono text-muted-foreground">
                        {planOptions.find((plan) => plan.id === selectedPlanId)?.hint}
                      </p>
                    ) : null}
                    <label className="block space-y-2">
                      <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('voucherRequest.countLabel')}
                      </span>
                      <input
                        className={FIELD_CLASS_NAME}
                        inputMode="numeric"
                        value={voucherCount}
                        onChange={(event) => setVoucherCount(event.target.value)}
                        placeholder={t('voucherRequest.countPlaceholder')}
                        disabled={!canWrite || requestVoucherBatchMutation.isPending}
                      />
                    </label>
                    <label className="block space-y-2">
                      <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('voucherRequest.recipientHintLabel')}
                      </span>
                      <input
                        className={FIELD_CLASS_NAME}
                        value={recipientHint}
                        onChange={(event) => setRecipientHint(event.target.value)}
                        placeholder={t('voucherRequest.recipientHintPlaceholder')}
                        disabled={!canWrite || requestVoucherBatchMutation.isPending}
                      />
                    </label>
                    <label className="block space-y-2">
                      <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                        {t('voucherRequest.messageLabel')}
                      </span>
                      <textarea
                        className={`${FIELD_CLASS_NAME} min-h-[110px] resize-y`}
                        value={giftMessage}
                        onChange={(event) => setGiftMessage(event.target.value)}
                        placeholder={t('voucherRequest.messagePlaceholder')}
                        disabled={!canWrite || requestVoucherBatchMutation.isPending}
                      />
                    </label>
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full border-neon-cyan/40 bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan/15 hover:text-neon-cyan"
                      onClick={() => requestVoucherBatchMutation.mutate()}
                      disabled={!canWrite || requestVoucherBatchMutation.isPending || plansQuery.isLoading}
                    >
                      {requestVoucherBatchMutation.isPending
                        ? t('voucherRequest.submitting')
                        : t('voucherRequest.submit')}
                    </Button>
                    {issuedCodes.length > 0 ? (
                      <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-matrix-green/80">
                          {t('voucherRequest.issuedCodesTitle')}
                        </p>
                        <ul className="mt-3 space-y-2 text-sm font-mono text-foreground/90">
                          {issuedCodes.map((code) => (
                            <li key={code}>{code}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                </article>

                <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('links.title')}
                  </h2>
                  <div className="mt-4 flex flex-col gap-3">
                    <Link href="/conversions" className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4">
                      <span>{t('links.conversions')}</span>
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                    <Link href="/integrations" className="inline-flex items-center gap-2 text-sm font-mono text-neon-purple underline underline-offset-4">
                      <span>{t('links.integrations')}</span>
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                    <Link href="/finance" className="inline-flex items-center gap-2 text-sm font-mono text-matrix-green underline underline-offset-4">
                      <span>{t('links.finance')}</span>
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                  </div>
                </article>
              </div>
            </div>
          </section>
        );
      }}
    </PartnerRouteGuard>
  );
}

function ResellerCommercialPreviewPanel({
  catalog,
  contract,
  error,
  isLoading,
  onSelectStorefront,
  selectedStorefrontKey,
  storefronts,
}: {
  catalog: PublicCommercialCatalog | null;
  contract: StorefrontPreviewResponse | null;
  error: unknown;
  isLoading: boolean;
  onSelectStorefront: (value: string) => void;
  selectedStorefrontKey: string;
  storefronts: ResellerStorefrontOption[];
}) {
  const t = useTranslations('Partner.reseller');

  return (
    <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
      <div className="flex items-center gap-3">
        <Store className="h-5 w-5 text-neon-cyan" />
        <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
          {t('commercialPreview.title')}
        </h2>
      </div>
      <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
        {t('commercialPreview.description')}
      </p>

      {storefronts.length === 0 ? (
        <p className="mt-4 rounded-xl border border-dashed border-grid-line/25 bg-terminal-bg/55 p-4 text-sm font-mono leading-6 text-muted-foreground">
          {t('commercialPreview.empty')}
        </p>
      ) : (
        <div className="mt-4 space-y-4">
          <label className="block space-y-2">
            <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('commercialPreview.selectLabel')}
            </span>
            <select
              aria-label={t('commercialPreview.selectLabel')}
              className={FIELD_CLASS_NAME}
              value={selectedStorefrontKey}
              onChange={(event) => onSelectStorefront(event.target.value)}
            >
              {storefronts.map((storefront) => (
                <option key={storefront.key} value={storefront.key}>
                  {storefront.label}
                </option>
              ))}
            </select>
          </label>

          {isLoading ? (
            <div className="h-32 animate-pulse rounded-xl border border-grid-line/20 bg-terminal-bg/55" />
          ) : error ? (
            <div
              className="rounded-xl border border-neon-pink/35 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink"
              role="alert"
              aria-live="assertive"
            >
              {readErrorMessage(error, t('commercialPreview.error'))}
            </div>
          ) : (
            <>
              <div className="grid gap-3 md:grid-cols-2">
                <PreviewMetric
                  label={t('commercialPreview.metrics.status')}
                  value={contract?.status ?? t('snapshot.notAvailable')}
                />
                <PreviewMetric
                  label={t('commercialPreview.metrics.currency')}
                  value={catalog?.context.currency ?? t('snapshot.notAvailable')}
                />
                <PreviewMetric
                  label={t('commercialPreview.metrics.billingPeriods')}
                  value={String(countBillingPeriods(catalog))}
                />
                <PreviewMetric
                  label={t('commercialPreview.metrics.sideEffects')}
                  value={
                    contract?.route_contract.checkout_side_effects
                      ? t('commercialPreview.boolean.yes')
                      : t('commercialPreview.boolean.no')
                  }
                />
              </div>

              <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                  {t('commercialPreview.contractTitle')}
                </p>
                <dl className="mt-3 space-y-2 text-sm font-mono text-muted-foreground">
                  <div className="flex items-center justify-between gap-3">
                    <dt>{t('commercialPreview.routeHost')}</dt>
                    <dd className="text-right text-foreground">
                      {contract?.route_contract.host ?? t('snapshot.notAvailable')}
                    </dd>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <dt>{t('commercialPreview.entryPath')}</dt>
                    <dd className="text-right text-foreground">
                      {contract?.route_contract.customer_entry_path ?? t('snapshot.notAvailable')}
                    </dd>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <dt>{t('commercialPreview.partnerCode')}</dt>
                    <dd className="text-right text-foreground">
                      {contract?.attribution_contract.partner_code ?? t('snapshot.notAvailable')}
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="space-y-3">
                {(catalog?.plans ?? []).slice(0, 3).map((plan) => (
                  <article
                    key={plan.planCode}
                    className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-sm font-display uppercase tracking-[0.14em] text-white">
                          {plan.displayName}
                        </h3>
                        <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                          {plan.planCode} / {plan.supportSla}
                        </p>
                      </div>
                      <p className="text-sm font-display tracking-[0.12em] text-neon-cyan">
                        {plan.billingPeriods[0]
                          ? formatCatalogAmount(
                            plan.billingPeriods[0].displayPrice.amount,
                            plan.billingPeriods[0].displayPrice.currency,
                          )
                          : t('snapshot.notAvailable')}
                      </p>
                    </div>
                  </article>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </article>
  );
}

function PreviewMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 px-4 py-3">
      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 break-words text-sm font-mono text-white">{value}</p>
    </div>
  );
}

'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { AxiosError } from 'axios';
import { Link } from '@/i18n/navigation';
import {
  commerceApi,
  createClientIdempotencyKey,
  type OrderResponse,
  type PaymentAttemptResponse,
} from '@/lib/api/commerce';
import {
  createStorefrontServiceStateRequest,
  entitlementsApi,
  serviceAccessApi,
} from '@/lib/api/service-access';
import { storefrontApi } from '@/lib/api/storefront';
import type { StorefrontSurfaceContext } from '@/features/storefront-shell/lib/runtime';

type StorefrontCheckoutLabels = {
  title: string;
  subtitle: string;
  empty: string;
  checkoutAction: string;
  checkoutPending: string;
  signInCta: string;
  legalNotice: string;
  currentEntitlementLabel: string;
  currentServiceStateLabel: string;
  orderReadyLabel: string;
  orderIdLabel: string;
  attemptStatusLabel: string;
  paymentLinkLabel: string;
  legalLinkLabel: string;
  supportLinkLabel: string;
  pricebookLabel: string;
  includedAddonsLabel: string;
};

type CheckoutCatalogItem = {
  offerId: string;
  offerKey: string;
  offerDisplayName: string;
  planId: string;
  pricebookKey: string;
  visiblePrice: number;
  compareAtPrice: number | null;
  includedAddonCodes: string[];
};

function readErrorMessage(error: unknown, fallback: string): string {
  const axiosError = error as AxiosError<{ detail?: unknown }>;
  const detail = axiosError.response?.data?.detail;

  if (typeof detail === 'string') {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: string }) => item.msg || JSON.stringify(item)).join(', ');
  }

  return fallback;
}

export function StorefrontCheckoutShell({
  surfaceContext,
  labels,
}: {
  surfaceContext: StorefrontSurfaceContext;
  labels: StorefrontCheckoutLabels;
}) {
  const queryClient = useQueryClient();
  const [selectedOfferId, setSelectedOfferId] = useState<string | null>(null);
  const [checkoutResult, setCheckoutResult] = useState<{
    order: OrderResponse;
    paymentAttempt: PaymentAttemptResponse;
  } | null>(null);

  const offersQuery = useQuery({
    queryKey: ['storefront', surfaceContext.storefrontKey, 'offers'],
    queryFn: async () => {
      const response = await storefrontApi.listOffers({ sale_channel: surfaceContext.saleChannel });
      return response.data;
    },
  });

  const pricebooksQuery = useQuery({
    queryKey: ['storefront', surfaceContext.storefrontKey, 'pricebooks', surfaceContext.defaultCurrency],
    queryFn: async () => {
      const response = await storefrontApi.resolvePricebooks({
        storefront_key: surfaceContext.storefrontKey,
        currency_code: surfaceContext.defaultCurrency,
      });
      return response.data;
    },
  });

  const legalSetQuery = useQuery({
    queryKey: ['storefront', surfaceContext.storefrontKey, 'legal-set'],
    queryFn: async () => {
      const response = await storefrontApi.resolveLegalDocumentSet({
        storefront_key: surfaceContext.storefrontKey,
      });
      return response.data;
    },
  });

  const currentEntitlementsQuery = useQuery({
    queryKey: ['storefront', surfaceContext.storefrontKey, 'current-entitlements'],
    queryFn: async () => {
      const response = await entitlementsApi.getCurrent();
      return response.data;
    },
    retry: false,
  });

  const currentServiceStateQuery = useQuery({
    queryKey: ['storefront', surfaceContext.storefrontKey, 'current-service-state'],
    queryFn: async () => {
      const response = await serviceAccessApi.getCurrentServiceState(
        createStorefrontServiceStateRequest(surfaceContext.storefrontKey),
      );
      return response.data;
    },
    retry: false,
  });

  const offers = offersQuery.data ?? [];
  const pricebooks = pricebooksQuery.data ?? [];
  const primaryPricebook = pricebooks[0];
  const offersById = new Map(offers.map((offer) => [offer.id, offer]));
  const catalogItems: CheckoutCatalogItem[] = primaryPricebook
    ? primaryPricebook.entries
      .map((entry) => {
        const offer = offersById.get(entry.offer_id);
        if (!offer) {
          return null;
        }

        return {
          offerId: offer.id,
          offerKey: offer.offer_key,
          offerDisplayName: offer.display_name,
          planId: offer.subscription_plan_id,
          pricebookKey: primaryPricebook.pricebook_key,
          visiblePrice: entry.visible_price,
          compareAtPrice: entry.compare_at_price,
          includedAddonCodes: entry.included_addon_codes,
        };
      })
      .filter((item): item is CheckoutCatalogItem => Boolean(item))
    : [];

  const checkoutMutation = useMutation({
    mutationFn: async (item: CheckoutCatalogItem) => {
      const quoteResponse = await commerceApi.createQuoteSession({
        storefront_key: surfaceContext.storefrontKey,
        pricebook_key: item.pricebookKey,
        offer_key: item.offerKey,
        plan_id: item.planId,
        currency: surfaceContext.defaultCurrency,
        channel: surfaceContext.saleChannel,
        use_wallet: 0,
        partner_code: surfaceContext.defaultPartnerCode,
      });

      const checkoutResponse = await commerceApi.createCheckoutSession(
        { quote_session_id: quoteResponse.data.id },
        createClientIdempotencyKey(`${surfaceContext.storefrontKey}-checkout`),
      );

      const orderResponse = await commerceApi.commitOrder({
        checkout_session_id: checkoutResponse.data.id,
      });

      const paymentAttemptResponse = await commerceApi.createPaymentAttempt(
        { order_id: orderResponse.data.id },
        createClientIdempotencyKey(`${surfaceContext.storefrontKey}-payment-attempt`),
      );

      return {
        order: orderResponse.data,
        paymentAttempt: paymentAttemptResponse.data,
      };
    },
    onSuccess: async (result) => {
      setCheckoutResult(result);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['storefront', surfaceContext.storefrontKey, 'current-entitlements'] }),
        queryClient.invalidateQueries({ queryKey: ['storefront', surfaceContext.storefrontKey, 'current-service-state'] }),
      ]);
    },
  });

  const selectedItem = catalogItems.find((item) => item.offerId === selectedOfferId) ?? catalogItems[0] ?? null;
  const legalDocumentCount = legalSetQuery.data?.documents.length ?? 0;
  const currentEntitlement = currentEntitlementsQuery.data;
  const currentServiceState = currentServiceStateQuery.data;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 md:px-6 md:py-10">
      <section className="rounded-[2rem] border border-grid-line/20 bg-terminal-surface/45 p-6 shadow-[0_0_32px_rgba(0,255,255,0.06)] backdrop-blur md:p-8">
        <div className="space-y-3">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan">{surfaceContext.brandLabel}</p>
          <h1 className="text-3xl font-display font-black uppercase tracking-[0.1em] text-foreground md:text-4xl">
            {labels.title}
          </h1>
          <p className="max-w-3xl font-mono text-sm leading-6 text-muted-foreground">
            {labels.subtitle}
          </p>
          <p className="font-mono text-xs text-muted-foreground">
            {labels.legalNotice.replace('{count}', String(legalDocumentCount))}
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href={surfaceContext.routes.login}
              className="inline-flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-bg/60 px-4 py-2 font-mono text-xs uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan/40"
            >
              {labels.signInCta}
            </Link>
            <Link
              href={surfaceContext.routes.legal}
              className="inline-flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-bg/60 px-4 py-2 font-mono text-xs uppercase tracking-[0.18em] text-neon-purple transition-colors hover:border-neon-purple/40"
            >
              {labels.legalLinkLabel}
            </Link>
            <Link
              href={surfaceContext.routes.support}
              className="inline-flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-bg/60 px-4 py-2 font-mono text-xs uppercase tracking-[0.18em] text-matrix-green transition-colors hover:border-matrix-green/40"
            >
              {labels.supportLinkLabel}
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="grid gap-4">
          {catalogItems.length === 0 ? (
            <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-6 font-mono text-sm text-muted-foreground">
              {labels.empty}
            </div>
          ) : (
            catalogItems.map((item) => {
              const isSelected = selectedOfferId === item.offerId;
              return (
                <button
                  key={item.offerId}
                  type="button"
                  onClick={() => setSelectedOfferId(item.offerId)}
                  className={`rounded-[1.5rem] border p-5 text-left transition-colors ${
                    isSelected
                      ? 'border-neon-cyan bg-neon-cyan/10'
                      : 'border-grid-line/20 bg-terminal-surface/35 hover:border-neon-cyan/35'
                  }`}
                >
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="font-display text-xl text-foreground">{item.offerDisplayName}</p>
                      <p className="mt-2 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
                        {labels.pricebookLabel}: {item.pricebookKey}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-display text-2xl text-neon-cyan">${item.visiblePrice.toFixed(2)}</p>
                      {item.compareAtPrice ? (
                        <p className="font-mono text-xs text-muted-foreground line-through">
                          ${item.compareAtPrice.toFixed(2)}
                        </p>
                      ) : null}
                    </div>
                  </div>
                  <p className="mt-4 font-mono text-xs text-muted-foreground">
                    {labels.includedAddonsLabel.replace('{count}', String(item.includedAddonCodes.length))}
                  </p>
                </button>
              );
            })
          )}
        </div>

        <div className="grid gap-4">
          <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">{labels.currentEntitlementLabel}</p>
            <p className="mt-3 font-display text-xl text-foreground">
              {currentEntitlement?.display_name ?? currentEntitlement?.status ?? 'Sign in required'}
            </p>
            <p className="mt-2 font-mono text-xs text-muted-foreground">
              {currentEntitlement?.expires_at ?? 'Canonical entitlement state appears after customer sign-in.'}
            </p>
          </div>
          <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">{labels.currentServiceStateLabel}</p>
            <p className="mt-3 font-display text-xl text-foreground">
              {currentServiceState?.access_delivery_channel?.channel_type ?? currentServiceState?.entitlement_snapshot.status ?? 'Awaiting customer context'}
            </p>
            <p className="mt-2 font-mono text-xs text-muted-foreground">
              {currentServiceState?.consumption_context.credential_subject_key ?? 'Service delivery stays realm-aware and storefront-scoped.'}
            </p>
          </div>
          <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
            <button
              type="button"
              onClick={() => {
                if (selectedItem) {
                  checkoutMutation.mutate(selectedItem);
                }
              }}
              disabled={!selectedItem || checkoutMutation.isPending || offersQuery.isLoading || pricebooksQuery.isLoading}
              className="inline-flex w-full items-center justify-center rounded-lg bg-neon-cyan px-4 py-3 font-mono text-sm font-bold uppercase tracking-[0.18em] text-black transition-colors hover:bg-neon-cyan/90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {checkoutMutation.isPending ? labels.checkoutPending : labels.checkoutAction}
            </button>
            {checkoutMutation.isError ? (
              <p className="mt-3 font-mono text-xs text-red-400">
                {readErrorMessage(checkoutMutation.error, 'Checkout failed.')}
              </p>
            ) : null}
          </div>
        </div>
      </section>

      {checkoutResult ? (
        <section className="rounded-[1.5rem] border border-neon-cyan/30 bg-neon-cyan/10 p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan">{labels.orderReadyLabel}</p>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            <div>
              <p className="font-mono text-xs text-muted-foreground">{labels.orderIdLabel}</p>
              <p className="mt-1 font-display text-lg text-foreground">{checkoutResult.order.id}</p>
            </div>
            <div>
              <p className="font-mono text-xs text-muted-foreground">{labels.attemptStatusLabel}</p>
              <p className="mt-1 font-display text-lg text-foreground">{checkoutResult.paymentAttempt.status}</p>
            </div>
            <div>
              <p className="font-mono text-xs text-muted-foreground">{labels.paymentLinkLabel}</p>
              {checkoutResult.paymentAttempt.invoice?.payment_url ? (
                <a
                  href={checkoutResult.paymentAttempt.invoice.payment_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-flex font-mono text-sm text-neon-purple underline underline-offset-4"
                >
                  {checkoutResult.paymentAttempt.invoice.invoice_id}
                </a>
              ) : (
                <p className="mt-1 font-mono text-sm text-muted-foreground">No invoice required</p>
              )}
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}

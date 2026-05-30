'use client';

import { useRef, useState, type FormEvent, type RefObject } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ReceiptText, RotateCcw } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  publicCatalogApi,
  type GetPublicCatalogParams,
  type PublicCatalogBillingPeriod,
  type PublicCatalogContext,
  type PublicCommercialCatalog,
  type StorefrontPreviewResponse,
} from '@/lib/api/catalog';
import {
  pricebooksApi,
  type CommercialContextOptionsResponse,
  type UpdateCommercialContextOptionsRequest,
} from '@/lib/api/pricebooks';
import {
  formatCompactNumber,
  formatCurrencyAmount,
  humanizeToken,
  shortId,
} from '@/features/commerce/lib/formatting';
import { CommercePageShell } from '@/features/commerce/components/commerce-page-shell';
import { StatusChip } from '@/features/commerce/components/status-chip';

type CatalogPreviewFilters = {
  channel: string;
  country: string;
  currency: string;
  uiLocale: string;
  storefrontKey: string;
  partnerCode: string;
};

const DEFAULT_FILTERS: CatalogPreviewFilters = {
  channel: 'web',
  country: 'US',
  currency: 'USD',
  uiLocale: 'en-EN',
  storefrontKey: '',
  partnerCode: '',
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function getRequiredString(record: Record<string, unknown>, key: string) {
  const value = record[key];

  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`${key}: expected non-empty string`);
  }

  return value.trim();
}

function getOptionalString(record: Record<string, unknown>, key: string) {
  const value = record[key];

  if (value == null || value === '') {
    return null;
  }

  if (typeof value !== 'string') {
    throw new Error(`${key}: expected string or null`);
  }

  return value.trim() || null;
}

function getOptionalBoolean(record: Record<string, unknown>, key: string) {
  const value = record[key];

  if (value == null) {
    return true;
  }

  if (typeof value !== 'boolean') {
    throw new Error(`${key}: expected boolean`);
  }

  return value;
}

function getStringArray(record: Record<string, unknown>, key: string) {
  const value = record[key];

  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(`${key}: expected non-empty string array`);
  }

  return value.map((item) => {
    if (typeof item !== 'string' || !item.trim()) {
      throw new Error(`${key}: expected string array`);
    }

    return item.trim().toUpperCase();
  });
}

function getOptionalMinorUnits(record: Record<string, unknown>) {
  const value = record.minor_units;

  if (value == null) {
    return 2;
  }

  const parsed = Number(value);

  if (!Number.isInteger(parsed) || parsed < 0 || parsed > 4) {
    throw new Error('minor_units: expected integer between 0 and 4');
  }

  return parsed;
}

function serializeContextOptions(options: CommercialContextOptionsResponse) {
  return JSON.stringify(
    {
      countries: options.countries.map((country) => ({
        country_code: country.country_code,
        default_currency_code: country.default_currency_code,
        supported_currency_codes: country.supported_currency_codes,
        payment_country_code: country.payment_country_code,
        is_enabled: country.is_enabled,
      })),
      currencies: options.currencies.map((currency) => ({
        currency_code: currency.currency_code,
        minor_units: currency.minor_units,
        is_enabled: currency.is_enabled,
      })),
    },
    null,
    2,
  );
}

function parseContextOptionsPayload(
  rawValue: string,
  changeReason: string,
): UpdateCommercialContextOptionsRequest {
  const parsed = JSON.parse(rawValue) as unknown;

  if (!isRecord(parsed) || !Array.isArray(parsed.countries)) {
    throw new Error('countries: expected array');
  }

  const countries = parsed.countries.map((item, index) => {
    if (!isRecord(item)) {
      throw new Error(`countries[${index}]: expected object`);
    }

    return {
      country_code: getRequiredString(item, 'country_code').toUpperCase(),
      default_currency_code: getRequiredString(
        item,
        'default_currency_code',
      ).toUpperCase(),
      supported_currency_codes: getStringArray(
        item,
        'supported_currency_codes',
      ),
      payment_country_code:
        getOptionalString(item, 'payment_country_code')?.toUpperCase() ?? null,
      is_enabled: getOptionalBoolean(item, 'is_enabled'),
    };
  });

  const rawCurrencies = Array.isArray(parsed.currencies)
    ? parsed.currencies
    : [];
  const currencies = rawCurrencies.map((item, index) => {
    if (!isRecord(item)) {
      throw new Error(`currencies[${index}]: expected object`);
    }

    return {
      currency_code: getRequiredString(item, 'currency_code').toUpperCase(),
      minor_units: getOptionalMinorUnits(item),
      is_enabled: getOptionalBoolean(item, 'is_enabled'),
    };
  });

  return {
    countries,
    currencies,
    change_reason: changeReason.trim() || null,
  };
}

function toCatalogParams(filters: CatalogPreviewFilters): GetPublicCatalogParams {
  return {
    channel: filters.channel.trim() || 'web',
    country: filters.country.trim().toUpperCase() || undefined,
    currency: filters.currency.trim().toUpperCase() || undefined,
    uiLocale: filters.uiLocale.trim() || undefined,
    storefrontKey: filters.storefrontKey.trim() || undefined,
  };
}

function moneyFromPeriod(period: PublicCatalogBillingPeriod) {
  return formatCurrencyAmount(
    Number(period.displayPrice.amount),
    period.displayPrice.currency,
  );
}

function compactList(items: readonly string[], emptyLabel: string, maxItems = 6) {
  if (items.length === 0) {
    return emptyLabel;
  }

  const visibleItems = items.slice(0, maxItems);
  const hiddenCount = items.length - visibleItems.length;

  return hiddenCount > 0
    ? `${visibleItems.join(', ')} +${hiddenCount}`
    : visibleItems.join(', ');
}

function catalogBillingPeriodCount(catalog: PublicCommercialCatalog | undefined) {
  return catalog?.plans.reduce(
    (total, plan) => total + plan.billingPeriods.length,
    0,
  );
}

function toPreviewPartnerCode(filters: CatalogPreviewFilters) {
  return filters.partnerCode.trim() || undefined;
}

export function CatalogPreviewConsole() {
  const t = useTranslations('Commerce');
  const queryClient = useQueryClient();
  const [draftFilters, setDraftFilters] =
    useState<CatalogPreviewFilters>(DEFAULT_FILTERS);
  const [submittedFilters, setSubmittedFilters] =
    useState<CatalogPreviewFilters>(DEFAULT_FILTERS);
  const [contextOptionsDraftJson, setContextOptionsDraftJson] = useState<
    string | null
  >(null);
  const [contextOptionsReason, setContextOptionsReason] = useState('');
  const [contextOptionsError, setContextOptionsError] = useState<string | null>(
    null,
  );
  const contextOptionsRef = useRef<HTMLTextAreaElement>(null);

  const catalogQuery = useQuery({
    queryKey: ['commerce', 'catalog-preview', submittedFilters],
    queryFn: async () => {
      const response = await publicCatalogApi.getCatalog(
        toCatalogParams(submittedFilters),
      );
      return response.data;
    },
    staleTime: 30_000,
  });

  const storefrontPreviewQuery = useQuery({
    queryKey: [
      'commerce',
      'storefront-preview',
      submittedFilters.storefrontKey,
      submittedFilters.partnerCode,
    ],
    queryFn: async () => {
      const storefrontKey = submittedFilters.storefrontKey.trim();
      if (!storefrontKey) {
        return null;
      }

      const response = await publicCatalogApi.previewStorefront(
        storefrontKey,
        { partner_code: toPreviewPartnerCode(submittedFilters) },
      );
      return response.data;
    },
    enabled: Boolean(submittedFilters.storefrontKey.trim()),
    staleTime: 30_000,
  });

  const contextOptionsQuery = useQuery({
    queryKey: ['commerce', 'commercial-context', 'options'],
    queryFn: async () => {
      const response = await pricebooksApi.getCommercialContextOptions();
      return response.data;
    },
    staleTime: 60_000,
  });

  const contextOptionsMutation = useMutation({
    mutationFn: (payload: UpdateCommercialContextOptionsRequest) =>
      pricebooksApi.updateCommercialContextOptions(payload),
    onSuccess: async (response) => {
      setContextOptionsDraftJson(serializeContextOptions(response.data));
      setContextOptionsReason('');
      setContextOptionsError(null);
      await queryClient.invalidateQueries({
        queryKey: ['commerce', 'commercial-context', 'options'],
      });
    },
    onError: (error) => {
      setContextOptionsError(
        error instanceof Error ? error.message : t('common.actionFailed'),
      );
    },
  });

  const catalog = catalogQuery.data;
  const contextOptionsJson =
    contextOptionsDraftJson
    ?? (contextOptionsQuery.data
      ? serializeContextOptions(contextOptionsQuery.data)
      : '');

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmittedFilters(draftFilters);
  }

  function handleReset() {
    setDraftFilters(DEFAULT_FILTERS);
    setSubmittedFilters(DEFAULT_FILTERS);
  }

  async function handleContextOptionsSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setContextOptionsError(null);

    let payload: UpdateCommercialContextOptionsRequest;

    try {
      payload = parseContextOptionsPayload(
        contextOptionsJson,
        contextOptionsReason,
      );
    } catch (error) {
      setContextOptionsError(
        t('catalogPreview.contextOptionsJsonInvalidDetail', {
          detail:
            error instanceof Error
              ? error.message
              : t('catalogPreview.contextOptionsJsonInvalid'),
        }),
      );
      contextOptionsRef.current?.focus();
      return;
    }

    await contextOptionsMutation.mutateAsync(payload);
  }

  function handleContextOptionsReset() {
    if (contextOptionsQuery.data) {
      setContextOptionsDraftJson(null);
      setContextOptionsReason('');
      setContextOptionsError(null);
    }
  }

  return (
    <CommercePageShell
      eyebrow={t('catalogPreview.eyebrow')}
      title={t('catalogPreview.title')}
      description={t('catalogPreview.description')}
      icon={ReceiptText}
      metrics={[
        {
          label: t('catalogPreview.metrics.plans'),
          value: formatCompactNumber(catalog?.plans.length),
          hint: t('catalogPreview.metrics.plansHint'),
          tone: 'info',
        },
        {
          label: t('catalogPreview.metrics.periods'),
          value: formatCompactNumber(catalogBillingPeriodCount(catalog)),
          hint: t('catalogPreview.metrics.periodsHint'),
          tone: 'neutral',
        },
        {
          label: t('catalogPreview.metrics.addons'),
          value: formatCompactNumber(catalog?.addons.length),
          hint: t('catalogPreview.metrics.addonsHint'),
          tone: 'success',
        },
        {
          label: t('catalogPreview.metrics.currency'),
          value: catalog?.context.currency ?? '--',
          hint: t('catalogPreview.metrics.currencyHint'),
          tone: 'warning',
        },
      ]}
    >
      <div className="grid min-w-0 max-w-full gap-6 xl:grid-cols-[22rem_minmax(0,1fr)]">
        <aside className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('catalogPreview.filtersTitle')}
          </h2>
          <form className="mt-5 space-y-4" onSubmit={handleSubmit}>
            <SelectField
              label={t('catalogPreview.fields.channel')}
              value={draftFilters.channel}
              onChange={(value) =>
                setDraftFilters((current) => ({ ...current, channel: value }))
              }
              options={[
                { value: 'web', label: 'web' },
                { value: 'miniapp', label: 'miniapp' },
                { value: 'telegram_bot', label: 'telegram_bot' },
              ]}
            />
            <Field
              label={t('catalogPreview.fields.country')}
              value={draftFilters.country}
              onChange={(value) =>
                setDraftFilters((current) => ({ ...current, country: value }))
              }
              placeholder="US"
            />
            <Field
              label={t('catalogPreview.fields.currency')}
              value={draftFilters.currency}
              onChange={(value) =>
                setDraftFilters((current) => ({ ...current, currency: value }))
              }
              placeholder="USD"
            />
            <Field
              label={t('catalogPreview.fields.uiLocale')}
              value={draftFilters.uiLocale}
              onChange={(value) =>
                setDraftFilters((current) => ({ ...current, uiLocale: value }))
              }
              placeholder="en-EN"
            />
            <Field
              label={t('catalogPreview.fields.storefrontKey')}
              value={draftFilters.storefrontKey}
              onChange={(value) =>
                setDraftFilters((current) => ({
                  ...current,
                  storefrontKey: value,
                }))
              }
              placeholder={t('common.optional')}
            />
            <Field
              label={t('catalogPreview.fields.partnerCode')}
              value={draftFilters.partnerCode}
              onChange={(value) =>
                setDraftFilters((current) => ({
                  ...current,
                  partnerCode: value,
                }))
              }
              placeholder={t('common.optional')}
            />

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <Button
                type="submit"
                magnetic={false}
                disabled={catalogQuery.isFetching}
                aria-label={t('catalogPreview.refreshAction')}
              >
                {catalogQuery.isFetching
                  ? t('catalogPreview.refreshing')
                  : t('catalogPreview.refreshAction')}
              </Button>
              <Button
                type="button"
                variant="ghost"
                magnetic={false}
                onClick={handleReset}
                aria-label={t('common.reset')}
              >
                <RotateCcw className="mr-2 h-4 w-4" />
                {t('common.reset')}
              </Button>
            </div>
          </form>

          <CommercialContextOptionsPanel
            errorMessage={contextOptionsError}
            isLoading={contextOptionsQuery.isLoading}
            isSaving={contextOptionsMutation.isPending}
            options={contextOptionsQuery.data}
            optionsJson={contextOptionsJson}
            optionsRef={contextOptionsRef}
            reason={contextOptionsReason}
            onJsonChange={setContextOptionsDraftJson}
            onReasonChange={setContextOptionsReason}
            onReset={handleContextOptionsReset}
            onSubmit={handleContextOptionsSubmit}
          />
        </aside>

        <div className="min-w-0 space-y-6">
          {catalogQuery.error ? (
            <div
              className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink"
              role="alert"
              aria-live="assertive"
            >
              {catalogQuery.error instanceof Error
                ? catalogQuery.error.message
                : t('common.actionFailed')}
            </div>
          ) : null}

          {catalogQuery.isLoading ? (
            <div className="grid gap-3">
              {Array.from({ length: 4 }).map((_, index) => (
                <div
                  key={index}
                  className="h-24 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45"
                />
              ))}
            </div>
          ) : catalog ? (
            <>
              {submittedFilters.storefrontKey.trim() ? (
                <StorefrontPreviewPanel
                  error={storefrontPreviewQuery.error}
                  isLoading={storefrontPreviewQuery.isLoading}
                  preview={storefrontPreviewQuery.data ?? null}
                />
              ) : null}
              <CatalogContextPanel context={catalog.context} />
              <CatalogPlansPanel catalog={catalog} />
              <CatalogAddonsPanel catalog={catalog} />
              <CatalogMetadataPanel catalog={catalog} />
            </>
          ) : (
            <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
              {t('catalogPreview.empty')}
            </div>
          )}
        </div>
      </div>
    </CommercePageShell>
  );
}

function CommercialContextOptionsPanel({
  errorMessage,
  isLoading,
  isSaving,
  onJsonChange,
  onReasonChange,
  onReset,
  onSubmit,
  options,
  optionsJson,
  optionsRef,
  reason,
}: {
  errorMessage: string | null;
  isLoading: boolean;
  isSaving: boolean;
  onJsonChange: (value: string) => void;
  onReasonChange: (value: string) => void;
  onReset: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  options: CommercialContextOptionsResponse | undefined;
  optionsJson: string;
  optionsRef: RefObject<HTMLTextAreaElement | null>;
  reason: string;
}) {
  const t = useTranslations('Commerce');

  return (
    <section className="mt-6 border-t border-grid-line/20 pt-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('catalogPreview.contextOptionsTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('catalogPreview.contextOptionsDescription')}
          </p>
        </div>
        {options ? (
          <StatusChip
            label={humanizeToken(options.source)}
            tone={options.source === 'system_config' ? 'success' : 'info'}
          />
        ) : null}
      </div>

      {isLoading ? (
        <div className="mt-4 h-32 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
      ) : (
        <form className="mt-4 space-y-4" onSubmit={onSubmit}>
          {options ? (
            <div className="grid gap-3 sm:grid-cols-2">
              <InfoLine
                label={t('catalogPreview.contextOptionsCountries')}
                value={formatCompactNumber(options.countries.length)}
              />
              <InfoLine
                label={t('catalogPreview.contextOptionsCurrencies')}
                value={compactList(
                  options.currencies.map((currency) => currency.currency_code),
                  t('common.emptyShort'),
                  4,
                )}
              />
            </div>
          ) : null}

          <label className="block space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('catalogPreview.contextOptionsJson')}
            </span>
            <textarea
              value={optionsJson}
              ref={optionsRef}
              onChange={(event) => onJsonChange(event.target.value)}
              rows={12}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-xs font-mono shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
              {t('catalogPreview.contextOptionsReason')}
            </span>
            <Input
              value={reason}
              onChange={(event) => onReasonChange(event.target.value)}
              placeholder={t('catalogPreview.contextOptionsReasonPlaceholder')}
            />
          </label>

          {errorMessage ? (
            <div
              className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink"
              role="alert"
              aria-live="assertive"
            >
              {errorMessage}
            </div>
          ) : null}

          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="submit"
              magnetic={false}
              disabled={isSaving || !optionsJson.trim()}
              aria-label={t('catalogPreview.contextOptionsSave')}
            >
              {isSaving
                ? t('common.saving')
                : t('catalogPreview.contextOptionsSave')}
            </Button>
            <Button
              type="button"
              variant="ghost"
              magnetic={false}
              onClick={onReset}
              disabled={isSaving || !options}
              aria-label={t('common.reset')}
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              {t('common.reset')}
            </Button>
          </div>
        </form>
      )}
    </section>
  );
}

type StorefrontPreviewOffer = NonNullable<
  StorefrontPreviewResponse['pricing_boundary']['offers']
>[number];

function StorefrontPreviewPanel({
  error,
  isLoading,
  preview,
}: {
  error: unknown;
  isLoading: boolean;
  preview: StorefrontPreviewResponse | null;
}) {
  const t = useTranslations('Commerce');

  if (isLoading) {
    return (
      <section className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
        <div className="h-32 animate-pulse rounded-2xl border border-grid-line/20 bg-terminal-bg/45" />
      </section>
    );
  }

  if (error) {
    return (
      <div
        className="rounded-xl border border-neon-pink/25 bg-neon-pink/10 px-4 py-3 text-sm font-mono text-neon-pink"
        role="alert"
        aria-live="assertive"
      >
        {error instanceof Error
          ? error.message
          : t('catalogPreview.storefrontPreviewError')}
      </div>
    );
  }

  if (!preview) {
    return (
      <section className="min-w-0 rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
        {t('catalogPreview.storefrontPreviewEmpty')}
      </section>
    );
  }

  const offers = preview.pricing_boundary.offers ?? [];

  return (
    <section className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('catalogPreview.storefrontPreviewTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('catalogPreview.storefrontPreviewDescription')}
          </p>
        </div>
        <StatusChip label={humanizeToken(preview.status)} tone="info" />
      </div>

      <div className="mt-5 grid min-w-0 gap-4 md:grid-cols-2">
        <InfoLine
          label={t('catalogPreview.fields.storefrontKey')}
          value={preview.storefront_key}
        />
        <InfoLine
          label={t('catalogPreview.fields.routeHost')}
          value={preview.route_contract.host}
        />
        <InfoLine
          label={t('catalogPreview.fields.entryPath')}
          value={preview.route_contract.customer_entry_path}
        />
        <InfoLine
          label={t('catalogPreview.fields.routeStatus')}
          value={humanizeToken(preview.route_contract.route_status)}
        />
        <InfoLine
          label={t('catalogPreview.fields.checkoutSideEffects')}
          value={
            preview.route_contract.checkout_side_effects
              ? t('catalogPreview.boolean.yes')
              : t('catalogPreview.boolean.no')
          }
        />
        <InfoLine
          label={t('catalogPreview.fields.pricingOffers')}
          value={formatCompactNumber(offers.length)}
        />
        <InfoLine
          label={t('catalogPreview.fields.attributionOwner')}
          value={compactList(
            [
              preview.attribution_contract.owner_type,
              preview.attribution_contract.owner_source,
              preview.attribution_contract.partner_code ?? '',
            ].filter(Boolean),
            t('common.emptyShort'),
          )}
        />
        <InfoLine
          label={t('catalogPreview.fields.analyticsDimensions')}
          value={compactList(
            preview.analytics_contract.expected_dimensions ?? [],
            t('common.emptyShort'),
          )}
        />
      </div>

      <div className="mt-5 grid min-w-0 gap-3 md:grid-cols-2">
        {offers.slice(0, 4).map((offer) => (
          <StorefrontOfferCard key={offer.offer_id} offer={offer} />
        ))}
      </div>
    </section>
  );
}

function StorefrontOfferCard({ offer }: { offer: StorefrontPreviewOffer }) {
  return (
    <article className="min-w-0 rounded-xl border border-grid-line/20 bg-terminal-bg/45 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-display uppercase tracking-[0.14em] text-white">
            {offer.offer_display_name}
          </p>
          <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {offer.pricebook_key} / {offer.region_code ?? offer.currency_code}
          </p>
        </div>
        <StatusChip
          label={formatCurrencyAmount(offer.visible_price, offer.currency_code)}
          tone="success"
        />
      </div>
    </article>
  );
}

function CatalogContextPanel({ context }: { context: PublicCatalogContext }) {
  const t = useTranslations('Commerce');

  return (
    <section className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('catalogPreview.contextTitle')}
          </h2>
          <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
            #{shortId(context.cacheKey)} / {humanizeToken(context.confidence)}
          </p>
        </div>
        <StatusChip
          label={context.currency}
          tone={context.confidence === 'explicit' ? 'success' : 'info'}
        />
      </div>

      <div className="mt-5 grid min-w-0 gap-4 md:grid-cols-2">
        <InfoLine label={t('catalogPreview.fields.uiLocale')} value={context.uiLocale} />
        <InfoLine
          label={t('catalogPreview.fields.displayCountry')}
          value={context.displayCountry}
        />
        <InfoLine
          label={t('catalogPreview.fields.pricingCountry')}
          value={context.pricingCountry}
        />
        <InfoLine
          label={t('catalogPreview.fields.paymentCountry')}
          value={context.paymentCountry}
        />
        <InfoLine
          label={t('catalogPreview.fields.paymentMethods')}
          value={compactList(
            context.paymentMethods.availableMethods,
            t('common.emptyShort'),
          )}
        />
        <InfoLine
          label={t('catalogPreview.fields.selectableCurrencies')}
          value={compactList(
            context.selectableCurrencies,
            t('common.emptyShort'),
          )}
        />
        <InfoLine
          label={t('catalogPreview.fields.selectableCountries')}
          value={compactList(
            context.selectableCountries,
            t('common.emptyShort'),
          )}
        />
        <InfoLine
          label={t('catalogPreview.fields.trace')}
          value={compactList(context.resolutionTrace, t('common.emptyShort'), 3)}
        />
      </div>
    </section>
  );
}

function CatalogPlansPanel({
  catalog,
}: {
  catalog: PublicCommercialCatalog;
}) {
  const t = useTranslations('Commerce');

  return (
    <section className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
        {t('catalogPreview.plansTitle')}
      </h2>
      <div className="mt-5 grid min-w-0 gap-4">
        {catalog.plans.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground">
            {t('catalogPreview.noPlans')}
          </div>
        ) : (
          catalog.plans.map((plan) => (
            <article
              key={plan.planCode}
              className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="font-display uppercase tracking-[0.14em] text-white">
                    {plan.displayName}
                  </p>
                  <p className="mt-1 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {plan.planCode} / {plan.supportSla}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <StatusChip
                    label={plan.trialEligible ? t('catalogPreview.trial') : t('catalogPreview.noTrial')}
                    tone={plan.trialEligible ? 'success' : 'warning'}
                  />
                  <StatusChip
                    label={plan.promoEligible ? t('catalogPreview.promo') : t('catalogPreview.noPromo')}
                    tone={plan.promoEligible ? 'success' : 'info'}
                  />
                </div>
              </div>

              <div className="mt-4 grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-4">
                {plan.billingPeriods.map((period) => (
                  <div
                    key={period.catalogItemKey}
                    className="rounded-xl border border-grid-line/20 bg-terminal-surface/35 p-3"
                  >
                    <p className="text-lg font-display tracking-[0.12em] text-neon-cyan">
                      {moneyFromPeriod(period)}
                    </p>
                    <p className="mt-1 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                      {period.durationDays} {t('common.durationDays')}
                    </p>
                    <p className="mt-3 text-xs font-mono text-muted-foreground">
                      {compactList(period.includedAddonCodes, t('common.emptyShort'))}
                    </p>
                  </div>
                ))}
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function CatalogAddonsPanel({
  catalog,
}: {
  catalog: PublicCommercialCatalog;
}) {
  const t = useTranslations('Commerce');

  return (
    <section className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
        {t('catalogPreview.addonsTitle')}
      </h2>
      <div className="mt-5 grid min-w-0 gap-3 md:grid-cols-2">
        {catalog.addons.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-grid-line/30 bg-terminal-bg/40 px-4 py-8 text-center text-sm font-mono text-muted-foreground md:col-span-2">
            {t('catalogPreview.noAddons')}
          </div>
        ) : (
          catalog.addons.map((addon) => (
            <article
              key={addon.addonId}
              className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                    {addon.displayName}
                  </p>
                  <p className="mt-2 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {addon.code}
                  </p>
                </div>
                <StatusChip
                  label={moneyFromAddon(addon.displayPrice.amount, addon.displayPrice.currency)}
                  tone="info"
                />
              </div>
              <p className="mt-3 text-xs font-mono leading-5 text-muted-foreground">
                {compactList(addon.saleChannels, t('common.emptyShort'))}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  );
}

function moneyFromAddon(amount: string, currency: string) {
  return formatCurrencyAmount(Number(amount), currency);
}

function CatalogMetadataPanel({
  catalog,
}: {
  catalog: PublicCommercialCatalog;
}) {
  const t = useTranslations('Commerce');

  return (
    <section className="min-w-0 rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
        {t('catalogPreview.metadataTitle')}
      </h2>
      <div className="mt-5 grid min-w-0 gap-4 md:grid-cols-2">
        <InfoLine
          label={t('catalogPreview.fields.catalogVersion')}
          value={catalog.catalogVersion}
        />
        <InfoLine
          label={t('catalogPreview.fields.source')}
          value={catalog.metadata.source}
        />
        <InfoLine
          label={t('catalogPreview.fields.storefrontKey')}
          value={catalog.metadata.storefrontKey ?? t('common.emptyShort')}
        />
        <InfoLine
          label={t('catalogPreview.fields.policyIds')}
          value={compactList(catalog.metadata.policyIds, t('common.emptyShort'))}
        />
        <InfoLine
          label={t('catalogPreview.fields.invalidationEvents')}
          value={compactList(
            catalog.metadata.invalidationEvents,
            t('common.emptyShort'),
          )}
        />
      </div>
    </section>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3">
      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 break-words text-sm font-mono text-white">{value}</p>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="space-y-2">
      <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </span>
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <label className="space-y-2">
      <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="flex h-10 w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

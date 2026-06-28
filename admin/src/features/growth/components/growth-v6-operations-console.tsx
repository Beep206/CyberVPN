'use client';

import type { ChangeEvent, ReactNode } from 'react';
import { useState } from 'react';
import {
  BadgeDollarSign,
  CheckCircle2,
  Fingerprint,
  LockKeyhole,
  Power,
  PowerOff,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import { getErrorMessage, humanizeToken } from '@/features/growth/lib/formatting';
import { growthApi } from '@/lib/api/growth';
import type {
  AdminGrowthFxRateResponse,
  AdminGrowthFxStatusResponse,
} from '@/lib/api/growth';
import { hasAdminPermission } from '@/shared/lib/admin-rbac';
import { useAuthStore } from '@/stores/auth-store';

const CAPABILITIES_QUERY_KEY = ['growth', 'v6-operations', 'client-capabilities'];
const FX_STATUS_QUERY_KEY = ['growth', 'v6-operations', 'fx-status'];
const FX_RATES_QUERY_KEY = ['growth', 'v6-operations', 'fx-rates'];
const PRIVATE_TARGETS_QUERY_KEY = ['growth', 'v6-operations', 'private-targets'];
const PRIVATE_GRANTS_QUERY_KEY = ['growth', 'v6-operations', 'private-grants'];
const ONBOARDING_SETTINGS_QUERY_KEY = ['growth', 'v6-operations', 'onboarding-settings'];
const ONBOARDING_STATES_QUERY_KEY = ['growth', 'v6-operations', 'onboarding-states'];
const RISK_MODELS_QUERY_KEY = ['growth', 'v6-operations', 'risk-models'];
const RISK_DECISIONS_QUERY_KEY = ['growth', 'v6-operations', 'risk-decisions'];
const RISK_REVIEWS_QUERY_KEY = ['growth', 'v6-operations', 'risk-reviews'];

function useClientCapabilities() {
  return useQuery({
    queryKey: CAPABILITIES_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.getClientCapabilities();
      return response.data;
    },
    staleTime: 15_000,
  });
}

function useGrowthFxStatus() {
  return useQuery({
    queryKey: FX_STATUS_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.getGrowthFxStatus();
      return response.data;
    },
    staleTime: 15_000,
  });
}

function useGrowthFxRates() {
  return useQuery({
    queryKey: FX_RATES_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.listGrowthFxRates({ limit: 8, offset: 0 });
      return response.data;
    },
    staleTime: 15_000,
  });
}

function usePrivateCatalogTargets() {
  return useQuery({
    queryKey: PRIVATE_TARGETS_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.listPrivateCatalogTargets({ limit: 1 });
      return response.data;
    },
    staleTime: 15_000,
  });
}

function usePrivateCatalogGrants() {
  return useQuery({
    queryKey: PRIVATE_GRANTS_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.listPrivateCatalogGrants({ limit: 3 });
      return response.data;
    },
    staleTime: 15_000,
  });
}

function useGrowthOnboardingSettings() {
  return useQuery({
    queryKey: ONBOARDING_SETTINGS_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.getGrowthOnboardingSettings();
      return response.data;
    },
    staleTime: 15_000,
  });
}

function useGrowthOnboardingStates() {
  return useQuery({
    queryKey: ONBOARDING_STATES_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.listGrowthOnboardingStates({ limit: 3 });
      return response.data;
    },
    staleTime: 15_000,
  });
}

function useGrowthRiskModels() {
  return useQuery({
    queryKey: RISK_MODELS_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.listGrowthRiskModels({ limit: 3 });
      return response.data;
    },
    staleTime: 15_000,
  });
}

function useGrowthRiskDecisions() {
  return useQuery({
    queryKey: RISK_DECISIONS_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.listGrowthRiskDecisions({ limit: 3 });
      return response.data;
    },
    staleTime: 15_000,
  });
}

function useGrowthRiskReviews() {
  return useQuery({
    queryKey: RISK_REVIEWS_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.listGrowthRiskReviews({ status: 'open', limit: 3 });
      return response.data;
    },
    staleTime: 15_000,
  });
}

type OnboardingCodeType = 'promo' | 'invite' | 'gift';

function onboardingCodeTypesForUpdate(values: string[] | undefined): OnboardingCodeType[] {
  const filtered = (values ?? []).filter((value): value is 'promo' | 'invite' | 'gift' =>
    ['promo', 'invite', 'gift'].includes(value),
  );
  return filtered.length ? filtered : ['promo', 'invite', 'gift'];
}

function capabilityTone(value: boolean | undefined) {
  if (value === true) return 'success' as const;
  if (value === false) return 'warning' as const;
  return 'neutral' as const;
}

function capabilityLabel(t: ReturnType<typeof useTranslations>, value: boolean | undefined) {
  if (value === true) return t('v6.common.enabled');
  if (value === false) return t('v6.common.disabled');
  return t('common.missing');
}

function endpointRows(area: 'fx' | 'privateAccess' | 'onboarding' | 'risk') {
  if (area === 'fx') {
    return [
      '/api/v3/admin/growth/fx/status',
      '/api/v3/admin/growth/fx/rates',
      '/api/v3/admin/growth/fx/simulate',
      '/api/v3/admin/growth/fx/rates/refresh',
      '/api/v3/admin/growth/fx/rates/{rate_id}/approve',
      '/api/v3/admin/growth/fx/rates/{rate_id}/reject',
      '/api/v3/admin/growth/fx/providers/{key}/disable',
      '/api/v3/admin/growth/fx/providers/{key}/enable',
    ];
  }

  if (area === 'privateAccess') {
    return [
      '/api/v3/admin/growth/private-catalog/targets',
      '/api/v3/admin/growth/private-grants',
      '/api/v3/admin/growth/private-grants/{id}',
      '/api/v3/admin/growth/private-grants/{id}/revoke',
    ];
  }

  if (area === 'risk') {
    return [
      '/api/v3/admin/growth/risk/models',
      '/api/v3/admin/growth/risk/decisions',
      '/api/v3/admin/growth/risk/reviews',
      '/api/v3/admin/growth/risk/reviews/{id}/resolve',
    ];
  }

  return [
    '/api/v3/admin/growth/onboarding/settings',
    '/api/v3/admin/growth/onboarding/states',
    '/api/v3/admin/growth/onboarding/states/{id}/reset',
    '/api/v3/admin/growth/onboarding/applications',
  ];
}

function DegradedNotice({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div
      role="status"
      className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4"
    >
      <div className="flex items-start gap-3">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-300" aria-hidden="true" />
        <div>
          <p className="text-sm font-display uppercase tracking-[0.18em] text-amber-200">
            {title}
          </p>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {description}
          </p>
        </div>
      </div>
    </div>
  );
}

function CapabilitiesError({
  error,
  fallback,
}: {
  error: unknown;
  fallback: string;
}) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-neon-pink/30 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink"
    >
      {getErrorMessage(error, fallback)}
    </div>
  );
}

function RefreshCapabilitiesButton({
  isFetching,
  onClick,
}: {
  isFetching: boolean;
  onClick: () => void;
}) {
  const t = useTranslations('Growth');

  return (
    <Button type="button" variant="outline" magnetic={false} onClick={onClick}>
      <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
      {isFetching ? t('v6.common.refreshing') : t('v6.common.refresh')}
    </Button>
  );
}

function CapabilityFlag({
  label,
  value,
}: {
  label: string;
  value: boolean | undefined;
}) {
  const t = useTranslations('Growth');

  return (
    <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
        {label}
      </p>
      <div className="mt-3">
        <GrowthStatusChip label={capabilityLabel(t, value)} tone={capabilityTone(value)} />
      </div>
    </div>
  );
}

function EndpointCoverage({
  title,
  description,
  area,
  wrapperAvailable,
}: {
  title: string;
  description: string;
  area: 'fx' | 'privateAccess' | 'onboarding' | 'risk';
  wrapperAvailable: boolean;
}) {
  const t = useTranslations('Growth');
  const endpointHelper = wrapperAvailable
    ? t('v6.common.generatedWrapper')
    : t('v6.common.noGeneratedAdminWrapper');
  const endpointLabel = wrapperAvailable ? t('v6.common.available') : t('v6.common.degraded');
  const endpointTone = wrapperAvailable ? 'success' : 'warning';

  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
        {title}
      </h2>
      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
        {description}
      </p>
      <div className="mt-5 space-y-3">
        <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                /api/v1/client/capabilities
              </p>
              <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                {t('v6.common.generatedWrapper')}
              </p>
            </div>
            <GrowthStatusChip label={t('v6.common.available')} tone="success" />
          </div>
        </div>
        {endpointRows(area).map((endpoint) => (
          <div
            key={endpoint}
            className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
          >
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                  {endpoint}
                </p>
                <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                  {endpointHelper}
                </p>
              </div>
              <GrowthStatusChip label={endpointLabel} tone={endpointTone} />
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

function ActionField({
  label,
  value,
  onChange,
  type = 'text',
  disabled = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: 'text' | 'number';
  disabled?: boolean;
}) {
  return (
    <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
      {label}
      <input
        type={type}
        value={value}
        disabled={disabled}
        onChange={(event: ChangeEvent<HTMLInputElement>) => onChange(event.target.value)}
        className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden transition focus:border-neon-cyan/60"
      />
    </label>
  );
}

function ActionPanel({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
      <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
        {title}
      </h2>
      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
        {description}
      </p>
      <div className="mt-5 space-y-4">{children}</div>
    </article>
  );
}

function MutationStatus({
  error,
  success,
}: {
  error: unknown;
  success: ReactNode;
}) {
  const t = useTranslations('Growth');

  if (error) {
    return (
      <div
        role="alert"
        className="rounded-lg border border-neon-pink/30 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink"
      >
        {getErrorMessage(error, t('v6.common.actionFailed'))}
      </div>
    );
  }

  if (!success) {
    return null;
  }

  return (
    <div
      role="status"
      className="rounded-lg border border-neon-cyan/30 bg-neon-cyan/10 p-4 text-sm font-mono text-foreground"
    >
      {success}
    </div>
  );
}

function SupportRows({
  rows,
  emptyLabel,
}: {
  rows: { id: string; primary: string; secondary: string }[];
  emptyLabel: string;
}) {
  if (!rows.length) {
    return <GrowthEmptyState label={emptyLabel} />;
  }

  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div
          key={row.id}
          className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
        >
          <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
            {row.primary}
          </p>
          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
            {row.secondary}
          </p>
        </div>
      ))}
    </div>
  );
}

function unknownRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function textValue(value: unknown, fallback = '--'): string {
  if (typeof value === 'string' && value.trim()) {
    return value;
  }

  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  return fallback;
}

function booleanValue(value: unknown): boolean | null {
  if (typeof value === 'boolean') {
    return value;
  }

  return null;
}

function fxStatusTone(status: string | null | undefined) {
  const normalizedStatus = status?.toLowerCase();
  if (normalizedStatus === 'active' || normalizedStatus === 'approved') {
    return 'success' as const;
  }
  if (normalizedStatus === 'pending' || normalizedStatus === 'pending_approval') {
    return 'warning' as const;
  }
  if (normalizedStatus === 'rejected' || normalizedStatus === 'disabled' || normalizedStatus === 'expired') {
    return 'danger' as const;
  }
  return 'neutral' as const;
}

function fxProviderRows(providers: AdminGrowthFxStatusResponse['providers'] | undefined) {
  return (providers ?? []).map((provider, index) => {
    const record = unknownRecord(provider);
    const providerKey = textValue(record.provider_key ?? record.key ?? record.name, `provider-${index + 1}`);
    const enabled = booleanValue(record.enabled);
    const status = textValue(record.status, enabled === false ? 'disabled' : 'active');
    const priority = textValue(record.priority);
    const approval = booleanValue(record.requires_admin_approval);
    const staleAfter = textValue(record.stale_after_seconds);

    return {
      id: providerKey,
      primary: `${providerKey} / ${humanizeToken(status)}`,
      secondary: `priority ${priority} / approval ${
        approval == null ? 'unknown' : approval ? 'required' : 'auto'
      } / stale ${staleAfter}s`,
      enabled,
      status,
    };
  });
}

function isPendingFxRate(rate: AdminGrowthFxRateResponse | null | undefined) {
  const status = rate?.status.toLowerCase();
  return status === 'pending' || status === 'pending_approval';
}

function createFxRefreshIdempotencyKey() {
  const randomPart = globalThis.crypto?.randomUUID?.()
    ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `admin-growth-fx-refresh-${randomPart}`;
}

function ReadOnlyNotice({ children }: { children: ReactNode }) {
  return (
    <div
      role="note"
      className="rounded-lg border border-amber-400/30 bg-amber-400/10 p-4 text-xs font-mono leading-5 text-amber-100"
    >
      {children}
    </div>
  );
}

function InfoLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 break-words font-mono text-xs text-foreground">{value}</p>
    </div>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-3">
      <p className="text-[11px] font-mono uppercase tracking-[0.16em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 font-display text-xl tracking-[0.1em] text-white">{value}</p>
    </div>
  );
}

export function GrowthFxConsole() {
  const t = useTranslations('Growth');
  const queryClient = useQueryClient();
  const role = useAuthStore((state) => state.user?.role);
  const canManageFx = hasAdminPermission(role, 'growth.fx.manage');
  const canApproveFx = hasAdminPermission(role, 'growth.fx.approve');
  const capabilitiesQuery = useClientCapabilities();
  const fxStatusQuery = useGrowthFxStatus();
  const fxRatesQuery = useGrowthFxRates();
  const [sourceCurrency, setSourceCurrency] = useState('USD');
  const [targetCurrency, setTargetCurrency] = useState('RUB');
  const [amount, setAmount] = useState('10.00');
  const [rateIdInput, setRateIdInput] = useState('');
  const [providerKeyInput, setProviderKeyInput] = useState('');
  const [fxReason, setFxReason] = useState('growth_fx_lifecycle_review');
  const [refreshIdempotencyKey, setRefreshIdempotencyKey] = useState(createFxRefreshIdempotencyKey);
  const growth = capabilitiesQuery.data?.growth;
  const site = capabilitiesQuery.data?.site;
  const rates = fxRatesQuery.data?.items ?? [];
  const firstRate = rates[0];
  const activeRateId = rateIdInput.trim() || firstRate?.id || '';
  const selectedRate = rates.find((rate) => rate.id === activeRateId) ?? firstRate ?? null;
  const providerRows = fxProviderRows(fxStatusQuery.data?.providers);
  const firstProvider = providerRows[0];
  const activeProviderKey = providerKeyInput.trim() || firstProvider?.id || '';
  const adminApiAvailable = fxStatusQuery.isSuccess && fxRatesQuery.isSuccess;
  const simulationMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.simulateGrowthFxConversion({
        source_amount: amount,
        source_currency: sourceCurrency.toUpperCase(),
        target_currency: targetCurrency.toUpperCase(),
        eligible_discount_base: amount,
        conversion_mode: 'market',
      });
      return response.data;
    },
  });
  const refreshRatesMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.refreshGrowthFxRates({
        ...(activeProviderKey ? { provider_key: activeProviderKey } : {}),
        idempotency_key: refreshIdempotencyKey,
        change_reason: fxReason,
      });
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: FX_STATUS_QUERY_KEY });
      void queryClient.invalidateQueries({ queryKey: FX_RATES_QUERY_KEY });
      setRefreshIdempotencyKey(createFxRefreshIdempotencyKey());
    },
  });
  const approveRateMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.approveGrowthFxRate(activeRateId, {
        change_reason: fxReason,
      });
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: FX_STATUS_QUERY_KEY });
      void queryClient.invalidateQueries({ queryKey: FX_RATES_QUERY_KEY });
    },
  });
  const rejectRateMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.rejectGrowthFxRate(activeRateId, {
        change_reason: fxReason,
      });
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: FX_STATUS_QUERY_KEY });
      void queryClient.invalidateQueries({ queryKey: FX_RATES_QUERY_KEY });
    },
  });
  const disableProviderMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.disableGrowthFxProvider(activeProviderKey, {
        change_reason: fxReason,
      });
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: FX_STATUS_QUERY_KEY });
    },
  });
  const enableProviderMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.enableGrowthFxProvider(activeProviderKey, {
        change_reason: fxReason,
      });
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: FX_STATUS_QUERY_KEY });
    },
  });
  const canSimulate = Boolean(sourceCurrency.trim() && targetCurrency.trim() && amount.trim());
  const canRefreshRates = Boolean(fxReason.trim() && canManageFx);
  const canApproveRate =
    Boolean(activeRateId && fxReason.trim() && isPendingFxRate(selectedRate) && canApproveFx);
  const canRejectRate =
    Boolean(activeRateId && fxReason.trim() && isPendingFxRate(selectedRate) && canApproveFx);
  const canToggleProvider = Boolean(activeProviderKey && fxReason.trim() && canManageFx);

  return (
    <GrowthPageShell
      eyebrow={t('fx.eyebrow')}
      title={t('fx.title')}
      description={t('fx.description')}
      icon={BadgeDollarSign}
      actions={
        <RefreshCapabilitiesButton
          isFetching={capabilitiesQuery.isFetching}
          onClick={() => void capabilitiesQuery.refetch()}
        />
      }
      metrics={[
        {
          label: t('fx.metrics.checkoutDiscounts'),
          value: capabilityLabel(t, growth?.checkout_code_discounts),
          hint: t('fx.metrics.checkoutDiscountsHint'),
          tone: capabilityTone(growth?.checkout_code_discounts),
        },
        {
          label: t('fx.metrics.siteMode'),
          value: site?.customer_site_mode ? humanizeToken(site.customer_site_mode) : t('common.missing'),
          hint: t('fx.metrics.siteModeHint'),
          tone: site?.customer_site_mode === 'full_site' ? 'success' : 'warning',
        },
        {
          label: t('fx.metrics.adminApi'),
          value: adminApiAvailable ? t('v6.common.available') : t('v6.common.degraded'),
          hint: t('fx.metrics.adminApiHint'),
          tone: adminApiAvailable ? 'success' : 'warning',
        },
        {
          label: t('fx.metrics.staleRates'),
          value: String(fxStatusQuery.data?.stale_rate_count ?? 0),
          hint: t('fx.metrics.staleRatesHint'),
          tone: fxStatusQuery.data?.stale_rate_count ? 'warning' : 'success',
        },
      ]}
    >
      {capabilitiesQuery.error ? (
        <CapabilitiesError error={capabilitiesQuery.error} fallback={t('fx.errors.capabilities')} />
      ) : null}
      {fxStatusQuery.error ? (
        <DegradedNotice title={t('fx.degraded.title')} description={t('fx.degraded.description')} />
      ) : null}
      {fxRatesQuery.error ? (
        <DegradedNotice title={t('fx.degraded.title')} description={t('fx.degraded.ratesDescription')} />
      ) : null}
      <div className="grid gap-6 xl:grid-cols-2">
        <EndpointCoverage
          title={t('fx.coverageTitle')}
          description={t('fx.coverageDescription')}
          area="fx"
          wrapperAvailable
        />
        <ActionPanel
          title={t('fx.lifecycleTitle')}
          description={t('fx.lifecycleDescription')}
        >
          {!canManageFx && !canApproveFx ? (
            <ReadOnlyNotice>{t('fx.readOnly')}</ReadOnlyNotice>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-3">
            <MetricCell
              label={t('fx.lifecycle.activeRates')}
              value={String(fxStatusQuery.data?.active_rate_count ?? 0)}
            />
            <MetricCell
              label={t('fx.lifecycle.staleRates')}
              value={String(fxStatusQuery.data?.stale_rate_count ?? 0)}
            />
            <MetricCell
              label={t('fx.lifecycle.disabledRates')}
              value={String(fxStatusQuery.data?.disabled_rate_count ?? 0)}
            />
          </div>
          <SupportRows
            emptyLabel={t('fx.lifecycle.emptyRates')}
            rows={rates.map((rate) => ({
              id: rate.id,
              primary: `${rate.base_currency}/${rate.quote_currency} ${rate.rate}`,
              secondary: `${rate.id} / ${humanizeToken(rate.status)} / ${rate.provider_key} / ${rate.valid_until}`,
            }))}
          />
          {selectedRate ? (
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <div className="flex flex-wrap items-center gap-2">
                <GrowthStatusChip
                  label={humanizeToken(selectedRate.status)}
                  tone={fxStatusTone(selectedRate.status)}
                />
                <GrowthStatusChip label={selectedRate.source_type} tone="info" />
                <GrowthStatusChip
                  label={selectedRate.provider_key}
                  tone="neutral"
                />
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <InfoLine label={t('fx.lifecycle.observedAt')} value={selectedRate.observed_at} />
                <InfoLine label={t('fx.lifecycle.validUntil')} value={selectedRate.valid_until} />
              </div>
            </div>
          ) : null}
          <div className="grid gap-4 md:grid-cols-2">
            <ActionField
              label={t('fx.fields.rate')}
              value={activeRateId}
              onChange={setRateIdInput}
              disabled={!canApproveFx}
            />
            <ActionField
              label={t('fx.fields.reason')}
              value={fxReason}
              onChange={setFxReason}
              disabled={!canManageFx && !canApproveFx}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              magnetic={false}
              disabled={!canApproveRate || approveRateMutation.isPending}
              onClick={() => approveRateMutation.mutate()}
            >
              <CheckCircle2 className="mr-2 h-4 w-4" aria-hidden="true" />
              {approveRateMutation.isPending ? t('v6.common.running') : t('fx.actions.approveRate')}
            </Button>
            <Button
              type="button"
              variant="outline"
              magnetic={false}
              disabled={!canRefreshRates || refreshRatesMutation.isPending}
              onClick={() => refreshRatesMutation.mutate()}
            >
              <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
              {refreshRatesMutation.isPending ? t('v6.common.running') : t('fx.actions.refreshRates')}
            </Button>
            <Button
              type="button"
              variant="outline"
              magnetic={false}
              disabled={!canRejectRate || rejectRateMutation.isPending}
              onClick={() => rejectRateMutation.mutate()}
            >
              <XCircle className="mr-2 h-4 w-4" aria-hidden="true" />
              {rejectRateMutation.isPending ? t('v6.common.running') : t('fx.actions.rejectRate')}
            </Button>
          </div>
          <SupportRows
            emptyLabel={t('fx.lifecycle.emptyProviders')}
            rows={providerRows}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <ActionField
              label={t('fx.fields.provider')}
              value={activeProviderKey}
              onChange={setProviderKeyInput}
              disabled={!canManageFx}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              magnetic={false}
              disabled={!canToggleProvider || disableProviderMutation.isPending}
              onClick={() => disableProviderMutation.mutate()}
            >
              <PowerOff className="mr-2 h-4 w-4" aria-hidden="true" />
              {disableProviderMutation.isPending
                ? t('v6.common.running')
                : t('fx.actions.disableProvider')}
            </Button>
            <Button
              type="button"
              variant="outline"
              magnetic={false}
              disabled={!canToggleProvider || enableProviderMutation.isPending}
              onClick={() => enableProviderMutation.mutate()}
            >
              <Power className="mr-2 h-4 w-4" aria-hidden="true" />
              {enableProviderMutation.isPending
                ? t('v6.common.running')
                : t('fx.actions.enableProvider')}
            </Button>
          </div>
          <MutationStatus
            error={
              refreshRatesMutation.error
              || approveRateMutation.error
              || rejectRateMutation.error
              || disableProviderMutation.error
              || enableProviderMutation.error
            }
            success={
              refreshRatesMutation.data
              || approveRateMutation.data
              || rejectRateMutation.data
              || disableProviderMutation.data
              || enableProviderMutation.data ? (
                <span>
                  {refreshRatesMutation.data
                    ? t('fx.lifecycle.refreshResult', {
                        count: refreshRatesMutation.data.created_snapshots.length,
                      })
                    : approveRateMutation.data
                    ? t('fx.lifecycle.approveResult', {
                        status: approveRateMutation.data.status,
                      })
                    : rejectRateMutation.data
                    ? t('fx.lifecycle.rejectResult', {
                        status: rejectRateMutation.data.status,
                      })
                    : t('fx.lifecycle.providerResult')}
                </span>
              ) : null
            }
          />
        </ActionPanel>
        <ActionPanel
          title={t('fx.simulatorTitle')}
          description={t('fx.simulatorDescription')}
        >
          <div className="grid gap-4 md:grid-cols-3">
            <ActionField
              label={t('fx.fields.sourceCurrency')}
              value={sourceCurrency}
              onChange={setSourceCurrency}
            />
            <ActionField
              label={t('fx.fields.targetCurrency')}
              value={targetCurrency}
              onChange={setTargetCurrency}
            />
            <ActionField
              label={t('fx.fields.amount')}
              value={amount}
              onChange={setAmount}
              type="number"
            />
          </div>
          <Button
            type="button"
            variant="outline"
            magnetic={false}
            disabled={!canSimulate || simulationMutation.isPending}
            onClick={() => simulationMutation.mutate()}
          >
            {simulationMutation.isPending ? t('v6.common.running') : t('fx.actions.simulate')}
          </Button>
          <MutationStatus
            error={simulationMutation.error}
            success={
              simulationMutation.data ? (
                <span>
                  {t('fx.simulationResult', {
                    rounded: simulationMutation.data.rounded_amount,
                    applied: simulationMutation.data.applied_amount,
                    currency: simulationMutation.data.target_currency,
                  })}
                </span>
              ) : null
            }
          />
        </ActionPanel>
      </div>
    </GrowthPageShell>
  );
}

export function GrowthPrivateAccessConsole() {
  const t = useTranslations('Growth');
  const queryClient = useQueryClient();
  const capabilitiesQuery = useClientCapabilities();
  const privateTargetsQuery = usePrivateCatalogTargets();
  const privateGrantsQuery = usePrivateCatalogGrants();
  const [grantIdInput, setGrantIdInput] = useState('');
  const [revokeReason, setRevokeReason] = useState('');
  const growth = capabilitiesQuery.data?.growth;
  const adminApiAvailable = privateTargetsQuery.isSuccess && privateGrantsQuery.isSuccess;
  const firstGrant = privateGrantsQuery.data?.items[0];
  const activeGrantId = grantIdInput.trim() || firstGrant?.id || '';
  const selectedGrant =
    privateGrantsQuery.data?.items.find((grant) => grant.id === activeGrantId)
    ?? firstGrant
    ?? null;
  const openGrantMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.getPrivateCatalogGrant(activeGrantId);
      return response.data;
    },
  });
  const revokeGrantMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.revokePrivateCatalogGrant(activeGrantId, {
        reason: revokeReason,
        expected_status: selectedGrant?.status ?? undefined,
      });
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: PRIVATE_GRANTS_QUERY_KEY });
    },
  });
  const canOpenGrant = Boolean(activeGrantId);
  const canRevokeGrant = Boolean(activeGrantId && revokeReason.trim());

  return (
    <GrowthPageShell
      eyebrow={t('privateAccess.eyebrow')}
      title={t('privateAccess.title')}
      description={t('privateAccess.description')}
      icon={LockKeyhole}
      actions={
        <RefreshCapabilitiesButton
          isFetching={capabilitiesQuery.isFetching}
          onClick={() => void capabilitiesQuery.refetch()}
        />
      }
      metrics={[
        {
          label: t('privateAccess.metrics.promoCodes'),
          value: capabilityLabel(t, growth?.promo_codes),
          hint: t('privateAccess.metrics.promoCodesHint'),
          tone: capabilityTone(growth?.promo_codes),
        },
        {
          label: t('privateAccess.metrics.giftCodes'),
          value: capabilityLabel(t, growth?.gift_codes),
          hint: t('privateAccess.metrics.giftCodesHint'),
          tone: capabilityTone(growth?.gift_codes),
        },
        {
          label: t('privateAccess.metrics.growthHub'),
          value: capabilityLabel(t, growth?.growth_hub),
          hint: t('privateAccess.metrics.growthHubHint'),
          tone: capabilityTone(growth?.growth_hub),
        },
        {
          label: t('privateAccess.metrics.adminApi'),
          value: adminApiAvailable ? t('v6.common.available') : t('v6.common.degraded'),
          hint: t('privateAccess.metrics.adminApiHint'),
          tone: adminApiAvailable ? 'success' : 'warning',
        },
      ]}
    >
      {capabilitiesQuery.error ? (
        <CapabilitiesError error={capabilitiesQuery.error} fallback={t('privateAccess.errors.capabilities')} />
      ) : null}
      {privateTargetsQuery.error ? (
        <DegradedNotice
          title={t('privateAccess.degraded.title')}
          description={t('privateAccess.degraded.description')}
        />
      ) : null}
      {privateGrantsQuery.error ? (
        <DegradedNotice
          title={t('privateAccess.degraded.title')}
          description={t('privateAccess.degraded.grantsDescription')}
        />
      ) : null}
      <div className="grid gap-6 xl:grid-cols-2">
        <EndpointCoverage
          title={t('privateAccess.coverageTitle')}
          description={t('privateAccess.coverageDescription')}
          area="privateAccess"
          wrapperAvailable
        />
        <ActionPanel
          title={t('privateAccess.grantsTitle')}
          description={t('privateAccess.grantsDescription')}
        >
          <SupportRows
            emptyLabel={t('privateAccess.emptyGrants')}
            rows={(privateGrantsQuery.data?.items ?? []).map((grant) => ({
              id: grant.id,
              primary: grant.status,
              secondary: `${grant.id} / ${grant.code_set_hash}`,
            }))}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <ActionField
              label={t('privateAccess.fields.grant')}
              value={activeGrantId}
              onChange={setGrantIdInput}
            />
            <ActionField
              label={t('privateAccess.fields.revokeReason')}
              value={revokeReason}
              onChange={setRevokeReason}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              magnetic={false}
              disabled={!canOpenGrant || openGrantMutation.isPending}
              onClick={() => openGrantMutation.mutate()}
            >
              {openGrantMutation.isPending ? t('v6.common.running') : t('privateAccess.actions.openGrant')}
            </Button>
            <Button
              type="button"
              variant="outline"
              magnetic={false}
              disabled={!canRevokeGrant || revokeGrantMutation.isPending}
              onClick={() => revokeGrantMutation.mutate()}
            >
              {revokeGrantMutation.isPending ? t('v6.common.running') : t('privateAccess.actions.revokeGrant')}
            </Button>
          </div>
          <MutationStatus
            error={openGrantMutation.error || revokeGrantMutation.error}
            success={
              openGrantMutation.data || revokeGrantMutation.data ? (
                <span>
                  {t('privateAccess.grantResult', {
                    status: (revokeGrantMutation.data ?? openGrantMutation.data)?.status ?? t('common.missing'),
                  })}
                </span>
              ) : null
            }
          />
        </ActionPanel>
      </div>
    </GrowthPageShell>
  );
}

export function GrowthOnboardingConsole() {
  const t = useTranslations('Growth');
  const queryClient = useQueryClient();
  const capabilitiesQuery = useClientCapabilities();
  const onboardingSettingsQuery = useGrowthOnboardingSettings();
  const onboardingStatesQuery = useGrowthOnboardingStates();
  const [stateIdInput, setStateIdInput] = useState('');
  const [resetReason, setResetReason] = useState('');
  const [settingsReason, setSettingsReason] = useState('');
  const onboardingCapabilities = capabilitiesQuery.data?.onboarding;
  const onboardingSettings = onboardingSettingsQuery.data;
  const promptEnabled =
    onboardingSettings?.post_registration_code_prompt_enabled
    ?? onboardingCapabilities?.post_registration_code_prompt;
  const stateStoreReady = onboardingSettings?.state_store_ready ?? onboardingCapabilities?.state_store;
  const webOtpEnabled = onboardingSettings?.web_otp_enabled ?? onboardingCapabilities?.web_otp;
  const telegramMiniappEnabled =
    onboardingSettings?.telegram_miniapp_enabled ?? onboardingCapabilities?.telegram_miniapp;
  const allowReferralInput =
    onboardingSettings?.allow_referral_input ?? onboardingCapabilities?.allow_referral_input;
  const allowPartnerInput =
    onboardingSettings?.allow_partner_input ?? onboardingCapabilities?.allow_partner_input;
  const flowKey = onboardingSettings?.flow_key ?? onboardingCapabilities?.flow_key;
  const flowVersion = onboardingSettings?.version ?? onboardingCapabilities?.version;
  const allowedCodeTypeList =
    onboardingSettings?.allowed_code_types ?? onboardingCapabilities?.allowed_code_types;
  const allowedCodeTypes = allowedCodeTypeList?.length
    ? allowedCodeTypeList.map((codeType) => humanizeToken(codeType)).join(', ')
    : t('common.missing');
  const adminApiAvailable = onboardingSettingsQuery.isSuccess && onboardingStatesQuery.isSuccess;
  const firstState = onboardingStatesQuery.data?.items[0];
  const activeStateId = stateIdInput.trim() || firstState?.id || '';
  const selectedState =
    onboardingStatesQuery.data?.items.find((state) => state.id === activeStateId)
    ?? firstState
    ?? null;
  const updateSettingsMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.updateGrowthOnboardingSettings({
        post_registration_code_prompt_enabled: Boolean(promptEnabled),
        web_otp_enabled: Boolean(webOtpEnabled),
        telegram_miniapp_enabled: Boolean(telegramMiniappEnabled),
        state_store_ready: Boolean(stateStoreReady),
        flow_key: flowKey || 'post_registration_growth_code_v1',
        version: Number(flowVersion || 1),
        allowed_code_types: onboardingCodeTypesForUpdate(allowedCodeTypeList),
        allow_referral_input: Boolean(allowReferralInput),
        allow_partner_input: Boolean(allowPartnerInput),
        change_reason: settingsReason,
      });
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ONBOARDING_SETTINGS_QUERY_KEY });
      void queryClient.invalidateQueries({ queryKey: CAPABILITIES_QUERY_KEY });
    },
  });
  const resetStateMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.resetGrowthOnboardingState(activeStateId, {
        reason: resetReason,
        expected_status: selectedState?.status ?? undefined,
      });
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ONBOARDING_STATES_QUERY_KEY });
    },
  });
  const canUpdateSettings = Boolean(settingsReason.trim());
  const canResetState = Boolean(activeStateId && resetReason.trim());

  return (
    <GrowthPageShell
      eyebrow={t('onboarding.eyebrow')}
      title={t('onboarding.title')}
      description={t('onboarding.description')}
      icon={Fingerprint}
      actions={
        <RefreshCapabilitiesButton
          isFetching={capabilitiesQuery.isFetching || onboardingSettingsQuery.isFetching}
          onClick={() => {
            void capabilitiesQuery.refetch();
            void onboardingSettingsQuery.refetch();
          }}
        />
      }
      metrics={[
        {
          label: t('onboarding.metrics.prompt'),
          value: capabilityLabel(t, promptEnabled),
          hint: t('onboarding.metrics.promptHint'),
          tone: capabilityTone(promptEnabled),
        },
        {
          label: t('onboarding.metrics.stateStore'),
          value: capabilityLabel(t, stateStoreReady),
          hint: t('onboarding.metrics.stateStoreHint'),
          tone: capabilityTone(stateStoreReady),
        },
        {
          label: t('onboarding.metrics.flowVersion'),
          value: flowKey && flowVersion ? `${flowKey} v${flowVersion}` : t('common.missing'),
          hint: t('onboarding.metrics.flowVersionHint'),
          tone: flowKey && flowVersion ? 'info' : 'warning',
        },
        {
          label: t('onboarding.metrics.adminApi'),
          value: adminApiAvailable ? t('v6.common.available') : t('v6.common.degraded'),
          hint: t('onboarding.metrics.adminApiHint'),
          tone: adminApiAvailable ? 'success' : 'warning',
        },
      ]}
    >
      {capabilitiesQuery.error ? (
        <CapabilitiesError error={capabilitiesQuery.error} fallback={t('onboarding.errors.capabilities')} />
      ) : null}
      {onboardingSettingsQuery.error ? (
        <DegradedNotice title={t('onboarding.degraded.title')} description={t('onboarding.degraded.description')} />
      ) : null}
      {onboardingStatesQuery.error ? (
        <DegradedNotice
          title={t('onboarding.degraded.title')}
          description={t('onboarding.degraded.statesDescription')}
        />
      ) : null}
      <div className="grid gap-6 xl:grid-cols-2">
        <EndpointCoverage
          title={t('onboarding.coverageTitle')}
          description={t('onboarding.coverageDescription')}
          area="onboarding"
          wrapperAvailable
        />
        <ActionPanel
          title={t('onboarding.settingsTitle')}
          description={t('onboarding.settingsDescription')}
        >
          {flowKey && flowVersion ? (
            <div className="grid gap-3 md:grid-cols-2">
              <CapabilityFlag label={t('onboarding.flags.webOtp')} value={webOtpEnabled} />
              <CapabilityFlag
                label={t('onboarding.flags.telegramMiniapp')}
                value={telegramMiniappEnabled}
              />
              <CapabilityFlag label={t('onboarding.flags.referralInput')} value={allowReferralInput} />
              <CapabilityFlag label={t('onboarding.flags.partnerInput')} value={allowPartnerInput} />
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4 md:col-span-2">
                <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('onboarding.flags.allowedCodeTypes')}
                </p>
                <p className="mt-3 font-mono text-sm text-foreground">{allowedCodeTypes}</p>
              </div>
            </div>
          ) : (
            <GrowthEmptyState label={t('onboarding.empty')} />
          )}
          <SupportRows
            emptyLabel={t('onboarding.emptyStates')}
            rows={(onboardingStatesQuery.data?.items ?? []).map((state) => ({
              id: state.id,
              primary: state.status,
              secondary: `${state.id} / ${state.flow_key} v${state.flow_version}`,
            }))}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <ActionField
              label={t('onboarding.fields.settingsReason')}
              value={settingsReason}
              onChange={setSettingsReason}
            />
            <ActionField
              label={t('onboarding.fields.state')}
              value={activeStateId}
              onChange={setStateIdInput}
            />
            <ActionField
              label={t('onboarding.fields.resetReason')}
              value={resetReason}
              onChange={setResetReason}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              magnetic={false}
              disabled={!canUpdateSettings || updateSettingsMutation.isPending}
              onClick={() => updateSettingsMutation.mutate()}
            >
              {updateSettingsMutation.isPending
                ? t('v6.common.running')
                : t('onboarding.actions.updateSettings')}
            </Button>
            <Button
              type="button"
              variant="outline"
              magnetic={false}
              disabled={!canResetState || resetStateMutation.isPending}
              onClick={() => resetStateMutation.mutate()}
            >
              {resetStateMutation.isPending ? t('v6.common.running') : t('onboarding.actions.resetState')}
            </Button>
          </div>
          <MutationStatus
            error={updateSettingsMutation.error || resetStateMutation.error}
            success={
              updateSettingsMutation.data || resetStateMutation.data ? (
                <span>
                  {updateSettingsMutation.data
                    ? t('onboarding.settingsResult', { version: updateSettingsMutation.data.version })
                    : t('onboarding.resetResult', {
                        status: resetStateMutation.data?.status ?? t('common.missing'),
                      })}
                </span>
              ) : null
            }
          />
        </ActionPanel>
      </div>
    </GrowthPageShell>
  );
}

export function GrowthRiskConsole() {
  const t = useTranslations('Growth');
  const queryClient = useQueryClient();
  const capabilitiesQuery = useClientCapabilities();
  const riskModelsQuery = useGrowthRiskModels();
  const riskDecisionsQuery = useGrowthRiskDecisions();
  const riskReviewsQuery = useGrowthRiskReviews();
  const [reviewIdInput, setReviewIdInput] = useState('');
  const [resolutionReason, setResolutionReason] = useState('');
  const growth = capabilitiesQuery.data?.growth;
  const firstReview = riskReviewsQuery.data?.items[0];
  const activeReviewId = reviewIdInput.trim() || firstReview?.id || '';
  const selectedReview =
    riskReviewsQuery.data?.items.find((review) => review.id === activeReviewId)
    ?? firstReview
    ?? null;
  const adminApiAvailable =
    riskModelsQuery.isSuccess && riskDecisionsQuery.isSuccess && riskReviewsQuery.isSuccess;
  const resolveReviewMutation = useMutation({
    mutationFn: async () => {
      const response = await growthApi.resolveGrowthRiskReview(activeReviewId, {
        decision: 'allow',
        resolution_status: 'resolved',
        resolution_reason: resolutionReason,
        resolution_evidence: {
          source: 'admin_growth_v6_operations_console',
          previous_status: selectedReview?.status ?? null,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: RISK_REVIEWS_QUERY_KEY });
    },
  });
  const canResolveReview = Boolean(activeReviewId && resolutionReason.trim());

  return (
    <GrowthPageShell
      eyebrow={t('risk.eyebrow')}
      title={t('risk.title')}
      description={t('risk.description')}
      icon={ShieldAlert}
      actions={
        <RefreshCapabilitiesButton
          isFetching={
            capabilitiesQuery.isFetching
            || riskModelsQuery.isFetching
            || riskDecisionsQuery.isFetching
            || riskReviewsQuery.isFetching
          }
          onClick={() => {
            void capabilitiesQuery.refetch();
            void riskModelsQuery.refetch();
            void riskDecisionsQuery.refetch();
            void riskReviewsQuery.refetch();
          }}
        />
      }
      metrics={[
        {
          label: t('risk.metrics.checkoutDiscounts'),
          value: capabilityLabel(t, growth?.checkout_code_discounts),
          hint: t('risk.metrics.checkoutDiscountsHint'),
          tone: capabilityTone(growth?.checkout_code_discounts),
        },
        {
          label: t('risk.metrics.models'),
          value: String(riskModelsQuery.data?.total ?? 0),
          hint: t('risk.metrics.modelsHint'),
          tone: riskModelsQuery.isSuccess ? 'info' : 'warning',
        },
        {
          label: t('risk.metrics.decisions'),
          value: String(riskDecisionsQuery.data?.total ?? 0),
          hint: t('risk.metrics.decisionsHint'),
          tone: riskDecisionsQuery.isSuccess ? 'info' : 'warning',
        },
        {
          label: t('risk.metrics.adminApi'),
          value: adminApiAvailable ? t('v6.common.available') : t('v6.common.degraded'),
          hint: t('risk.metrics.adminApiHint'),
          tone: adminApiAvailable ? 'success' : 'warning',
        },
      ]}
    >
      {capabilitiesQuery.error ? (
        <CapabilitiesError error={capabilitiesQuery.error} fallback={t('risk.errors.capabilities')} />
      ) : null}
      {riskModelsQuery.error || riskDecisionsQuery.error || riskReviewsQuery.error ? (
        <DegradedNotice title={t('risk.degraded.title')} description={t('risk.degraded.description')} />
      ) : null}
      <div className="grid gap-6 xl:grid-cols-2">
        <EndpointCoverage
          title={t('risk.coverageTitle')}
          description={t('risk.coverageDescription')}
          area="risk"
          wrapperAvailable
        />
        <ActionPanel
          title={t('risk.lifecycleTitle')}
          description={t('risk.lifecycleDescription')}
        >
          <SupportRows
            emptyLabel={t('risk.emptyModels')}
            rows={(riskModelsQuery.data?.items ?? []).map((model) => ({
              id: model.id,
              primary: `${model.model_key} ${model.version}`,
              secondary: `${model.status} / ${model.approval_state} / ${model.deployment_mode}`,
            }))}
          />
          <SupportRows
            emptyLabel={t('risk.emptyDecisions')}
            rows={(riskDecisionsQuery.data?.items ?? []).map((decision) => ({
              id: decision.id,
              primary: decision.final_action,
              secondary: `${decision.risk_band} / ${decision.action_context} / ${decision.id}`,
            }))}
          />
          <SupportRows
            emptyLabel={t('risk.emptyReviews')}
            rows={(riskReviewsQuery.data?.items ?? []).map((review) => ({
              id: review.id,
              primary: review.status,
              secondary: `${review.review_type} / ${review.decision} / ${review.id}`,
            }))}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <ActionField
              label={t('risk.fields.review')}
              value={activeReviewId}
              onChange={setReviewIdInput}
            />
            <ActionField
              label={t('risk.fields.resolutionReason')}
              value={resolutionReason}
              onChange={setResolutionReason}
            />
          </div>
          <Button
            type="button"
            variant="outline"
            magnetic={false}
            disabled={!canResolveReview || resolveReviewMutation.isPending}
            onClick={() => resolveReviewMutation.mutate()}
          >
            {resolveReviewMutation.isPending ? t('v6.common.running') : t('risk.actions.resolveReview')}
          </Button>
          <MutationStatus
            error={resolveReviewMutation.error}
            success={
              resolveReviewMutation.data ? (
                <span>{t('risk.reviewResult', { status: resolveReviewMutation.data.status })}</span>
              ) : null
            }
          />
        </ActionPanel>
      </div>
    </GrowthPageShell>
  );
}

'use client';

import { useMemo, useState } from 'react';
import { Globe2, Route } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { growthApi } from '@/lib/api/growth';
import type { AdminCustomerSiteRuntime, UpdateAdminCustomerSiteRuntimeConfigRequest } from '@/lib/api/growth';
import { GrowthEmptyState } from '@/features/growth/components/growth-empty-state';
import { GrowthPageShell } from '@/features/growth/components/growth-page-shell';
import { GrowthStatusChip } from '@/features/growth/components/growth-status-chip';
import { formatDateTime, getErrorMessage, humanizeToken } from '@/features/growth/lib/formatting';

const DEFAULT_PREVIEW_URL = 'https://cyber-vpn.net/en/pricing?ref=partner-001&utm_campaign=beta&code=PR-PRO100';
const LOCALE_SEGMENT_RE = /^[a-z]{2}(?:-[A-Z]{2})?$/;
const SITE_RUNTIME_QUERY_KEY = ['growth', 'site-mode', 'customer-site-runtime'];
const SITE_TIMELINE_QUERY_KEY = ['growth', 'site-mode', 'customer-site-runtime', 'timeline'];
const SITE_MODE_OPTIONS = ['full_site', 'cabinet_only', 'maintenance'] as const;
const CABINET_MARKETING_ACTION_OPTIONS = ['redirect_public', 'allow', 'not_found'] as const;

interface SiteModeFormState {
  mode: AdminCustomerSiteRuntime['mode'];
  publicHosts: string;
  cabinetHosts: string;
  cabinetDestinationPath: string;
  allowedPathPrefixes: string;
  cabinetAllowedPathPrefixes: string;
  cabinetMarketingRouteAction: NonNullable<AdminCustomerSiteRuntime['cabinet_marketing_route_action']>;
  publicMarketingDestinationPath: string;
  legalPathPrefixes: string;
  operationalPathPrefixes: string;
  preserveQueryKeys: string;
  changeReason: string;
  confirmation: string;
}

function firstValue(values: string[] | undefined, fallback: string) {
  const value = values?.[0];
  return value && value.trim() ? value : fallback;
}

function siteModeTone(mode: string | undefined) {
  if (mode === 'full_site') return 'success' as const;
  if (mode === 'cabinet_only') return 'warning' as const;
  if (mode === 'maintenance') return 'danger' as const;
  return 'neutral' as const;
}

function pathIsAllowed(pathname: string, prefixes: string[] | undefined) {
  if (!prefixes?.length) {
    return false;
  }
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

function siteRouteClass(pathname: string, site: AdminCustomerSiteRuntime | undefined) {
  if (pathIsAllowed(pathname, site?.legal_path_prefixes)) return 'legal_route';
  if (pathIsAllowed(pathname, site?.operational_path_prefixes)) return 'operational_route';
  if (pathIsAllowed(pathname, site?.cabinet_allowed_prefixes)) return 'cabinet_route';
  if (pathIsAllowed(pathname, site?.allowed_path_prefixes)) return 'allowed_route';
  return 'marketing_route';
}

function buildPreservedSearch(source: URL, preserveKeys: string[] | undefined) {
  const result = new URLSearchParams();
  for (const key of preserveKeys ?? []) {
    const values = source.searchParams.getAll(key);
    for (const value of values) {
      result.append(key, value);
    }
  }
  return result.toString();
}

function previewCabinetRoute(
  rawUrl: string,
  site: AdminCustomerSiteRuntime | undefined,
) {
  try {
    const source = new URL(rawUrl);
    const publicHosts = site?.public_hosts ?? [];
    const cabinetHost = firstValue(site?.cabinet_hosts, 'my.cyber-vpn.net');
    const publicHost = firstValue(site?.public_hosts, 'cyber-vpn.net');
    const destinationPath = site?.cabinet_destination_path || '/dashboard';
    const mode = site?.mode ?? 'full_site';
    const isPublicHost = publicHosts.length === 0 || publicHosts.includes(source.host);
    const isCabinetHost = Boolean(site?.cabinet_hosts?.includes(source.host));
    const routeClass = siteRouteClass(source.pathname, site);
    const safePublicRoute = routeClass === 'legal_route' || routeClass === 'operational_route';
    const publicAllowedRoute = safePublicRoute || routeClass === 'allowed_route';
    const cabinetAllowedRoute = safePublicRoute || routeClass === 'cabinet_route';
    const cabinetMarketingAction = site?.cabinet_marketing_route_action ?? 'redirect_public';
    const shouldRedirect =
      mode === 'cabinet_only'
      && ((isPublicHost && !publicAllowedRoute) || (isCabinetHost && !cabinetAllowedRoute && cabinetMarketingAction === 'redirect_public'));
    const firstSegment = source.pathname.split('/').filter(Boolean)[0];
    const localePrefix = firstSegment && LOCALE_SEGMENT_RE.test(firstSegment) ? `/${firstSegment}` : '';
    const normalizedCabinetDestination = destinationPath.startsWith('/') ? destinationPath : `/${destinationPath}`;
    const normalizedPublicDestination = (site?.public_marketing_destination_path || '/').startsWith('/')
      ? site?.public_marketing_destination_path || '/'
      : `/${site?.public_marketing_destination_path || ''}`;
    const redirectHost = isCabinetHost ? publicHost : cabinetHost;
    const redirectPath = isCabinetHost ? normalizedPublicDestination : normalizedCabinetDestination;
    const target = new URL(`https://${redirectHost}${localePrefix}${redirectPath}`);
    const preservedSearch = buildPreservedSearch(source, site?.preserve_query_keys);

    target.search = preservedSearch;

    return {
      error: null,
      source: source.toString(),
      target: shouldRedirect ? target.toString() : source.toString(),
      shouldRedirect,
      mode,
      reason: shouldRedirect
        ? 'cabinet_only_redirect'
        : mode === 'cabinet_only' && isCabinetHost && !cabinetAllowedRoute && cabinetMarketingAction === 'not_found'
          ? 'cabinet_marketing_not_found'
          : publicAllowedRoute || cabinetAllowedRoute
            ? routeClass
            : 'full_site_passthrough',
    };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : String(error),
      source: rawUrl,
      target: rawUrl,
      shouldRedirect: false,
      mode: site?.mode ?? 'unknown',
      reason: 'invalid_url',
    };
  }
}

function csvFromValues(values: string[] | undefined) {
  return values?.join(', ') ?? '';
}

function valuesFromCsv(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function formFromSite(site: AdminCustomerSiteRuntime | undefined): SiteModeFormState {
  return {
    mode: site?.mode ?? 'full_site',
    publicHosts: csvFromValues(site?.public_hosts),
    cabinetHosts: csvFromValues(site?.cabinet_hosts),
    cabinetDestinationPath: site?.cabinet_destination_path ?? '/dashboard',
    allowedPathPrefixes: csvFromValues(site?.allowed_path_prefixes),
    cabinetAllowedPathPrefixes: csvFromValues(site?.cabinet_allowed_prefixes),
    cabinetMarketingRouteAction: site?.cabinet_marketing_route_action ?? 'redirect_public',
    publicMarketingDestinationPath: site?.public_marketing_destination_path ?? '/',
    legalPathPrefixes: csvFromValues(site?.legal_path_prefixes),
    operationalPathPrefixes: csvFromValues(site?.operational_path_prefixes),
    preserveQueryKeys: csvFromValues(site?.preserve_query_keys),
    changeReason: '',
    confirmation: '',
  };
}

function buildUpdatePayload(
  form: SiteModeFormState,
  site: AdminCustomerSiteRuntime,
): UpdateAdminCustomerSiteRuntimeConfigRequest {
  return {
    mode: form.mode,
    public_hosts: valuesFromCsv(form.publicHosts),
    cabinet_hosts: valuesFromCsv(form.cabinetHosts),
    cabinet_destination_path: form.cabinetDestinationPath.trim(),
    allowed_path_prefixes: valuesFromCsv(form.allowedPathPrefixes),
    cabinet_allowed_prefixes: valuesFromCsv(form.cabinetAllowedPathPrefixes),
    cabinet_marketing_route_action: form.cabinetMarketingRouteAction,
    public_marketing_destination_path: form.publicMarketingDestinationPath.trim(),
    legal_path_prefixes: valuesFromCsv(form.legalPathPrefixes),
    operational_path_prefixes: valuesFromCsv(form.operationalPathPrefixes),
    preserve_query_keys: valuesFromCsv(form.preserveQueryKeys),
    expected_version: site.version,
    change_reason: form.changeReason.trim(),
  };
}

export function CustomerSiteModeConsole() {
  const t = useTranslations('Growth');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const [previewUrl, setPreviewUrl] = useState(DEFAULT_PREVIEW_URL);
  const [formOverrides, setFormOverrides] = useState<Partial<SiteModeFormState>>({});
  const [feedback, setFeedback] = useState<string | null>(null);

  const runtimeQuery = useQuery({
    queryKey: SITE_RUNTIME_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.getCustomerSiteRuntime();
      return response.data;
    },
  });

  const timelineQuery = useQuery({
    queryKey: SITE_TIMELINE_QUERY_KEY,
    queryFn: async () => {
      const response = await growthApi.getCustomerSiteRuntimeTimeline({ limit: 8 });
      return response.data;
    },
    staleTime: 15_000,
  });

  const site = runtimeQuery.data?.site;
  const formDefaults = useMemo(() => formFromSite(site), [site]);
  const form: SiteModeFormState = {
    ...formDefaults,
    ...formOverrides,
    changeReason: formOverrides.changeReason ?? '',
    confirmation: formOverrides.confirmation ?? '',
  };
  const preview = previewCabinetRoute(previewUrl, site);
  const reasonReady = form.changeReason.trim().length >= 3;
  const confirmationValue = form.confirmation.trim();
  const updateConfirmationReady = Boolean(site && confirmationValue === form.mode);
  const rollbackConfirmationReady = confirmationValue === 'full_site';

  const updateMutation = useMutation({
    mutationFn: async () => {
      if (!site) {
        throw new Error('customer_site_runtime_missing');
      }
      return growthApi.updateCustomerSiteRuntime(buildUpdatePayload(form, site));
    },
    onSuccess: async () => {
      setFeedback(t('siteMode.feedback.updated'));
      setFormOverrides((current) => ({
        changeReason: current.changeReason ?? '',
        confirmation: '',
      }));
      await queryClient.invalidateQueries({ queryKey: SITE_RUNTIME_QUERY_KEY });
      await queryClient.invalidateQueries({ queryKey: SITE_TIMELINE_QUERY_KEY });
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('siteMode.feedback.updateFailed')));
    },
  });

  const rollbackMutation = useMutation({
    mutationFn: async () => {
      if (!site) {
        throw new Error('customer_site_runtime_missing');
      }
      return growthApi.executeCustomerSiteRuntimeAction({
        action: 'rollback_to_full_site',
        expected_version: site.version,
        change_reason: form.changeReason.trim(),
      });
    },
    onSuccess: async () => {
      setFeedback(t('siteMode.feedback.rollback'));
      setFormOverrides((current) => ({
        changeReason: current.changeReason ?? '',
        confirmation: '',
      }));
      await queryClient.invalidateQueries({ queryKey: SITE_RUNTIME_QUERY_KEY });
      await queryClient.invalidateQueries({ queryKey: SITE_TIMELINE_QUERY_KEY });
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('siteMode.feedback.rollbackFailed')));
    },
  });

  return (
    <GrowthPageShell
      eyebrow={t('siteMode.eyebrow')}
      title={t('siteMode.title')}
      description={t('siteMode.description')}
      icon={Globe2}
      metrics={[
        {
          label: t('siteMode.metrics.mode'),
          value: site?.mode ? t(`siteMode.modes.${site.mode}`) : t('common.missing'),
          hint: t('siteMode.metrics.modeHint'),
          tone: siteModeTone(site?.mode),
        },
        {
          label: t('siteMode.metrics.cabinetHost'),
          value: firstValue(site?.cabinet_hosts, t('common.missing')),
          hint: t('siteMode.metrics.cabinetHostHint'),
          tone: site?.cabinet_hosts?.length ? 'info' : 'warning',
        },
        {
          label: t('siteMode.metrics.destination'),
          value: site?.cabinet_destination_path ?? t('common.missing'),
          hint: t('siteMode.metrics.destinationHint'),
          tone: site?.cabinet_destination_path ? 'neutral' : 'warning',
        },
        {
          label: t('siteMode.metrics.configVersion'),
          value: site?.version ? String(site.version) : t('common.missing'),
          hint: t('siteMode.metrics.configVersionHint'),
          tone: site?.version ? 'info' : 'warning',
        },
      ]}
    >
      {runtimeQuery.error ? (
        <div role="alert" className="rounded-lg border border-neon-pink/30 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
          {getErrorMessage(runtimeQuery.error, t('siteMode.errors.loadFailed'))}
        </div>
      ) : null}
      {feedback ? (
        <div role="status" className="rounded-lg border border-neon-cyan/25 bg-neon-cyan/10 p-4 text-sm font-mono text-neon-cyan">
          {feedback}
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <div className="flex items-start gap-3">
            <Route className="mt-0.5 h-5 w-5 text-neon-cyan" aria-hidden="true" />
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
                {t('siteMode.previewTitle')}
              </h2>
              <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                {t('siteMode.previewDescription')}
              </p>
            </div>
          </div>

          <label className="mt-5 block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
            {t('siteMode.fields.url')}
            <input
              value={previewUrl}
              onChange={(event) => setPreviewUrl(event.target.value)}
              className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
            />
          </label>

          <div className="mt-5 grid gap-3 rounded-lg border border-grid-line/20 bg-terminal-bg/45 p-4">
            <GrowthStatusChip
              label={preview.shouldRedirect ? t('siteMode.preview.redirect') : t('siteMode.preview.pass')}
              tone={preview.shouldRedirect ? 'warning' : 'success'}
            />
            <InfoLine label={t('siteMode.preview.source')} value={preview.source} />
            <InfoLine label={t('siteMode.preview.target')} value={preview.target} />
            <InfoLine label={t('siteMode.preview.reason')} value={t(`siteMode.reasons.${preview.reason}`)} />
            {preview.error ? (
              <p className="text-xs font-mono text-neon-pink">{preview.error}</p>
            ) : null}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
          <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
            {t('siteMode.matrixTitle')}
          </h2>
          <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
            {t('siteMode.matrixDescription')}
          </p>

          {runtimeQuery.isLoading ? (
            <div className="mt-5">
              <GrowthEmptyState label={t('siteMode.loading')} />
            </div>
          ) : site ? (
            <div className="mt-5 space-y-4">
              <InfoLine
                label={t('siteMode.fields.publicHosts')}
                value={(site.public_hosts ?? []).join(', ') || t('common.missing')}
              />
              <InfoLine
                label={t('siteMode.fields.cabinetHosts')}
                value={(site.cabinet_hosts ?? []).join(', ') || t('common.missing')}
              />
              <InfoLine
                label={t('siteMode.fields.allowedPrefixes')}
                value={(site.allowed_path_prefixes ?? []).join(', ') || t('common.missing')}
              />
              <InfoLine
                label={t('siteMode.fields.cabinetAllowedPrefixes')}
                value={(site.cabinet_allowed_prefixes ?? []).join(', ') || t('common.missing')}
              />
              <InfoLine
                label={t('siteMode.fields.cabinetMarketingAction')}
                value={t(`siteMode.cabinetMarketingActions.${site.cabinet_marketing_route_action ?? 'redirect_public'}`)}
              />
              <InfoLine
                label={t('siteMode.fields.publicMarketingDestination')}
                value={site.public_marketing_destination_path ?? t('common.missing')}
              />
              <InfoLine
                label={t('siteMode.fields.legalPrefixes')}
                value={(site.legal_path_prefixes ?? []).join(', ') || t('common.missing')}
              />
              <InfoLine
                label={t('siteMode.fields.operationalPrefixes')}
                value={(site.operational_path_prefixes ?? []).join(', ') || t('common.missing')}
              />
              <InfoLine
                label={t('siteMode.fields.preserveKeys')}
                value={(site.preserve_query_keys ?? []).join(', ') || t('common.missing')}
              />
              <InfoLine
                label={t('siteMode.fields.registrationPolicy')}
                value={site.registration_policy_independent ? t('siteMode.boolean.true') : t('siteMode.boolean.false')}
              />
              <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                {t('siteMode.fields.mode')}
                <select
                  value={form.mode}
                  onChange={(event) => setFormOverrides((current) => ({
                    ...current,
                    mode: event.target.value as SiteModeFormState['mode'],
                  }))}
                  className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
                >
                  {SITE_MODE_OPTIONS.map((mode) => (
                    <option key={mode} value={mode}>
                      {t(`siteMode.modes.${mode}`)}
                    </option>
                  ))}
                </select>
              </label>
              <SiteModeInput
                label={t('siteMode.fields.publicHosts')}
                value={form.publicHosts}
                onChange={(value) => setFormOverrides((current) => ({ ...current, publicHosts: value }))}
              />
              <SiteModeInput
                label={t('siteMode.fields.cabinetHosts')}
                value={form.cabinetHosts}
                onChange={(value) => setFormOverrides((current) => ({ ...current, cabinetHosts: value }))}
              />
              <SiteModeInput
                label={t('siteMode.fields.destination')}
                value={form.cabinetDestinationPath}
                onChange={(value) => setFormOverrides((current) => ({ ...current, cabinetDestinationPath: value }))}
              />
              <SiteModeInput
                label={t('siteMode.fields.allowedPrefixes')}
                value={form.allowedPathPrefixes}
                onChange={(value) => setFormOverrides((current) => ({ ...current, allowedPathPrefixes: value }))}
              />
              <SiteModeInput
                label={t('siteMode.fields.cabinetAllowedPrefixes')}
                value={form.cabinetAllowedPathPrefixes}
                onChange={(value) => setFormOverrides((current) => ({ ...current, cabinetAllowedPathPrefixes: value }))}
              />
              <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                {t('siteMode.fields.cabinetMarketingAction')}
                <select
                  value={form.cabinetMarketingRouteAction}
                  onChange={(event) => setFormOverrides((current) => ({
                    ...current,
                    cabinetMarketingRouteAction: event.target.value as SiteModeFormState['cabinetMarketingRouteAction'],
                  }))}
                  className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
                >
                  {CABINET_MARKETING_ACTION_OPTIONS.map((action) => (
                    <option key={action} value={action}>
                      {t(`siteMode.cabinetMarketingActions.${action}`)}
                    </option>
                  ))}
                </select>
              </label>
              <SiteModeInput
                label={t('siteMode.fields.publicMarketingDestination')}
                value={form.publicMarketingDestinationPath}
                onChange={(value) => setFormOverrides((current) => ({ ...current, publicMarketingDestinationPath: value }))}
              />
              <SiteModeInput
                label={t('siteMode.fields.legalPrefixes')}
                value={form.legalPathPrefixes}
                onChange={(value) => setFormOverrides((current) => ({ ...current, legalPathPrefixes: value }))}
              />
              <SiteModeInput
                label={t('siteMode.fields.operationalPrefixes')}
                value={form.operationalPathPrefixes}
                onChange={(value) => setFormOverrides((current) => ({ ...current, operationalPathPrefixes: value }))}
              />
              <SiteModeInput
                label={t('siteMode.fields.preserveKeys')}
                value={form.preserveQueryKeys}
                onChange={(value) => setFormOverrides((current) => ({ ...current, preserveQueryKeys: value }))}
              />
              <SiteModeInput
                label={t('siteMode.fields.reason')}
                value={form.changeReason}
                onChange={(value) => setFormOverrides((current) => ({ ...current, changeReason: value }))}
              />
              <SiteModeInput
                label={t('siteMode.fields.confirmation')}
                value={form.confirmation}
                onChange={(value) => setFormOverrides((current) => ({ ...current, confirmation: value }))}
              />
              <p className="text-xs font-mono leading-5 text-muted-foreground">
                {t('siteMode.confirmationHint', {
                  update: form.mode,
                  rollback: 'full_site',
                })}
              </p>
              <div className="flex flex-wrap gap-3">
                <Button
                  type="button"
                  variant="outline"
                  magnetic={false}
                  disabled={!reasonReady || !updateConfirmationReady || updateMutation.isPending || rollbackMutation.isPending}
                  onClick={() => updateMutation.mutate()}
                >
                  {updateMutation.isPending ? t('siteMode.updating') : t('siteMode.updateAction')}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  magnetic={false}
                  disabled={!reasonReady || !rollbackConfirmationReady || updateMutation.isPending || rollbackMutation.isPending || site.mode === 'full_site'}
                  onClick={() => rollbackMutation.mutate()}
                >
                  {rollbackMutation.isPending ? t('siteMode.rollingBack') : t('siteMode.rollbackAction')}
                </Button>
              </div>
            </div>
          ) : (
            <div className="mt-5">
              <GrowthEmptyState label={t('siteMode.empty')} />
            </div>
          )}
        </article>
      </div>

      <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <h2 className="text-sm font-display uppercase tracking-[0.22em] text-white">
              {t('siteMode.auditTitle')}
            </h2>
            <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
              {t('siteMode.auditDescription')}
            </p>
          </div>
          <GrowthStatusChip label={t('siteMode.auditGenerated')} tone="info" />
        </div>

        {timelineQuery.error ? (
          <div role="alert" className="mt-5 rounded-lg border border-neon-pink/30 bg-neon-pink/10 p-4 text-sm font-mono text-neon-pink">
            {getErrorMessage(timelineQuery.error, t('siteMode.errors.auditLoadFailed'))}
          </div>
        ) : null}

        <div className="mt-5 space-y-3">
          {timelineQuery.isLoading ? (
            <GrowthEmptyState label={t('siteMode.auditLoading')} />
          ) : timelineQuery.data?.length ? (
            timelineQuery.data.map((entry) => (
              <div
                key={entry.id}
                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
              >
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                      {humanizeToken(entry.action)}
                    </p>
                    <p className="mt-2 text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
                      {formatDateTime(entry.created_at, locale)}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <GrowthStatusChip label={humanizeToken(entry.event_type)} tone="neutral" />
                    {entry.resulting_mode ? (
                      <GrowthStatusChip
                        label={t(`siteMode.modes.${entry.resulting_mode}`)}
                        tone={siteModeTone(entry.resulting_mode)}
                      />
                    ) : null}
                  </div>
                </div>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <InfoLine
                    label={t('siteMode.auditFields.version')}
                    value={entry.resulting_version ? String(entry.resulting_version) : t('common.missing')}
                  />
                  <InfoLine
                    label={t('siteMode.auditFields.admin')}
                    value={entry.admin_id ?? t('common.missing')}
                  />
                  <InfoLine
                    label={t('siteMode.auditFields.reason')}
                    value={entry.change_reason ?? t('common.missing')}
                  />
                </div>
              </div>
            ))
          ) : (
            <GrowthEmptyState label={t('siteMode.auditEmpty')} />
          )}
        </div>
      </article>
    </GrowthPageShell>
  );
}

function SiteModeInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block text-xs font-mono uppercase tracking-[0.16em] text-muted-foreground">
      {label}
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 w-full rounded-lg border border-grid-line/25 bg-terminal-bg/70 px-3 py-2 text-sm text-foreground outline-hidden focus:border-neon-cyan/60 focus:ring-2 focus:ring-neon-cyan/25"
      />
    </label>
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

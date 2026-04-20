'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowUpRight, ReceiptText, Rows3 } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { partnerPortalApi } from '@/lib/api/partner-portal';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import {
  getPartnerConversionsCapabilities,
  getPartnerConversionsSurfaceMode,
} from '@/features/partner-operations/lib/advanced-operational-capabilities';

function formatDateTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function formatMoney(value: number, currencyCode: string, locale: string): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currencyCode,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function ConversionsOrdersPage() {
  const locale = useLocale();
  const t = useTranslations('Partner.conversions');
  const portalT = useTranslations('Partner.portalState');
  const { state, activeWorkspace } = usePartnerPortalRuntimeState();
  const mode = getPartnerConversionsSurfaceMode(state);
  const capabilities = getPartnerConversionsCapabilities(state);
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);

  const effectiveSelectedRecordId = selectedRecordId ?? state.conversionRecords[0]?.id ?? null;
  const selectedRecord = useMemo(
    () => state.conversionRecords.find((record) => record.id === effectiveSelectedRecordId) ?? null,
    [effectiveSelectedRecordId, state.conversionRecords],
  );

  const explainabilityQuery = useQuery({
    queryKey: [
      'partner-portal',
      'workspace-conversion-explainability',
      activeWorkspace?.id ?? null,
      effectiveSelectedRecordId,
    ],
    queryFn: async () => {
      if (!activeWorkspace || !effectiveSelectedRecordId) {
        return null;
      }
      const response = await partnerPortalApi.getWorkspaceConversionExplainability(
        activeWorkspace.id,
        effectiveSelectedRecordId,
      );
      return response.data;
    },
    enabled: Boolean(activeWorkspace?.id && effectiveSelectedRecordId),
    staleTime: 30_000,
    retry: false,
  });

  return (
    <PartnerRouteGuard route="conversions" title={t('title')}>
      {(access) => (
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
                  <span>{t('summary.currentLane')}</span>
                  <span className="text-foreground">
                    {state.primaryLane
                      ? portalT(`laneLabels.${state.primaryLane}`)
                      : portalT('noLane')}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.routeAccess')}</span>
                  <span className="text-neon-cyan">
                    {portalT(`routeAccess.${access}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.surfaceMode')}</span>
                  <span className="text-foreground">
                    {portalT(`conversionsModes.${mode}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.records')}</span>
                  <span className="text-foreground">{state.conversionRecords.length}</span>
                </div>
              </div>
            </div>
          </header>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
              <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                {t('cards.commissionable')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.14em] text-white">
                {state.conversionRecords.filter((item) => item.status === 'commissionable').length}
              </p>
            </article>
            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
              <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                {t('cards.onHold')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.14em] text-white">
                {state.conversionRecords.filter((item) => item.status === 'on_hold').length}
              </p>
            </article>
            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
              <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                {t('cards.disputes')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.14em] text-white">
                {state.cases.filter((item) => item.kind === 'attribution_dispute' || item.kind === 'payout_dispute').length}
              </p>
            </article>
            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
              <p className="text-[11px] font-mono uppercase tracking-[0.22em] text-neon-cyan/80">
                {t('cards.customerScope')}
              </p>
              <p className="mt-3 text-sm font-display uppercase tracking-[0.14em] text-white">
                {state.conversionRecords[0]
                  ? portalT(`customerScopes.${state.conversionRecords[0].customerScope}`)
                  : portalT('customerScopes.masked')}
              </p>
            </article>
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
              <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                <ReceiptText className="h-5 w-5 text-neon-cyan" />
                <div>
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('records.title')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('records.description')}
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {state.conversionRecords.map((record) => {
                  const isSelected = record.id === effectiveSelectedRecordId;

                  return (
                    <button
                      key={record.id}
                      type="button"
                      className={`w-full rounded-2xl border p-4 text-left transition-colors ${
                        isSelected
                          ? 'border-neon-cyan/45 bg-neon-cyan/10'
                          : 'border-grid-line/20 bg-terminal-surface/35 hover:border-neon-cyan/25'
                      }`}
                      onClick={() => setSelectedRecordId(record.id)}
                    >
                      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                        <div>
                          <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                            {portalT(`conversionKinds.${record.kind}`)} · {record.orderLabel}
                          </h3>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {record.customerLabel} · {portalT(`customerScopes.${record.customerScope}`)} · {record.geo}
                          </p>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {t('records.code', { value: record.codeLabel })}
                          </p>
                          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                            {record.notes[0]}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-display tracking-[0.12em] text-white">
                            {record.amount}
                          </p>
                          <p className="mt-2 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                            {portalT(`conversionStatuses.${record.status}`)}
                          </p>
                          <p className="mt-2 text-xs font-mono text-muted-foreground">
                            {formatDateTime(record.updatedAt, locale)}
                          </p>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </article>

            <div className="space-y-6">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <div className="flex items-center gap-3">
                  <Rows3 className="h-5 w-5 text-neon-purple" />
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
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('explainability.title')}
                </h2>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {selectedRecord
                    ? t('explainability.description', { order: selectedRecord.orderLabel })
                    : t('explainability.empty')}
                </p>

                {selectedRecord && explainabilityQuery.isLoading ? (
                  <p className="mt-4 text-sm font-mono leading-6 text-muted-foreground">
                    {t('explainability.loading')}
                  </p>
                ) : null}

                {selectedRecord && explainabilityQuery.isError ? (
                  <p className="mt-4 text-sm font-mono leading-6 text-neon-pink">
                    {t('explainability.error')}
                  </p>
                ) : null}

                {selectedRecord && explainabilityQuery.data ? (
                  <div className="mt-4 space-y-4">
                    <div className="grid gap-3 md:grid-cols-2">
                      <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {t('explainability.cards.commissionability')}
                        </p>
                        <p className="mt-2 text-sm font-display uppercase tracking-[0.14em] text-white">
                          {explainabilityQuery.data.commissionability_evaluation.commissionability_status}
                        </p>
                      </div>
                      <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {t('explainability.cards.settlement')}
                        </p>
                        <p className="mt-2 text-sm font-display uppercase tracking-[0.14em] text-white">
                          {explainabilityQuery.data.order.settlement_status}
                        </p>
                      </div>
                      <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {t('explainability.cards.saleChannel')}
                        </p>
                        <p className="mt-2 text-sm font-display uppercase tracking-[0.14em] text-white">
                          {explainabilityQuery.data.order.sale_channel}
                        </p>
                      </div>
                      <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {t('explainability.cards.commissionBase')}
                        </p>
                        <p className="mt-2 text-sm font-display uppercase tracking-[0.14em] text-white">
                          {formatMoney(
                            explainabilityQuery.data.order.commission_base_amount,
                            explainabilityQuery.data.order.currency_code,
                            locale,
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-purple/80">
                        {t('explainability.reasonCodesTitle')}
                      </p>
                      {(explainabilityQuery.data.commissionability_evaluation.reason_codes?.length ?? 0) > 0 ? (
                        <ul className="mt-3 space-y-2">
                          {(explainabilityQuery.data.commissionability_evaluation.reason_codes ?? []).map((reasonCode) => (
                            <li
                              key={reasonCode}
                              className="rounded-lg border border-grid-line/15 bg-terminal-surface/35 px-3 py-2 text-sm font-mono leading-6 text-muted-foreground"
                            >
                              {reasonCode}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                          {t('explainability.noReasonCodes')}
                        </p>
                      )}
                    </div>

                    <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4">
                      <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-purple/80">
                        {t('explainability.snapshotTitle')}
                      </p>
                      <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words text-xs font-mono leading-6 text-muted-foreground">
                        {JSON.stringify(explainabilityQuery.data.explainability ?? {}, null, 2)}
                      </pre>
                    </div>
                  </div>
                ) : null}
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('links.title')}
                </h2>
                <div className="mt-4 flex flex-col gap-3">
                  <Link href="/analytics" className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4">
                    <span>{t('links.analytics')}</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                  <Link href="/finance" className="inline-flex items-center gap-2 text-sm font-mono text-neon-purple underline underline-offset-4">
                    <span>{t('links.finance')}</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                  <Link href="/cases" className="inline-flex items-center gap-2 text-sm font-mono text-matrix-green underline underline-offset-4">
                    <span>{t('links.cases')}</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </article>
            </div>
          </div>
        </section>
      )}
    </PartnerRouteGuard>
  );
}

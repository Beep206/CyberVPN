'use client';

import { ArrowUpRight, KeyRound, Waypoints } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';
import {
  getPartnerIntegrationsCapabilities,
  getPartnerIntegrationsSurfaceMode,
} from '@/features/partner-operations/lib/advanced-operational-capabilities';

function formatDateTime(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function IntegrationsConsolePage() {
  const locale = useLocale();
  const t = useTranslations('Partner.integrations');
  const portalT = useTranslations('Partner.portalState');
  const { state } = usePartnerPortalRuntimeState();
  const mode = getPartnerIntegrationsSurfaceMode(state);
  const capabilities = getPartnerIntegrationsCapabilities(state);

  return (
    <PartnerRouteGuard route="integrations" title={t('title')}>
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
                  <span>{t('summary.routeAccess')}</span>
                  <span className="text-neon-cyan">
                    {portalT(`routeAccess.${access}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.technicalReadiness')}</span>
                  <span className="text-foreground">
                    {portalT(`technicalStates.${state.technicalReadiness}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.surfaceMode')}</span>
                  <span className="text-foreground">
                    {portalT(`integrationsModes.${mode}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.credentials')}</span>
                  <span className="text-foreground">{state.integrationCredentials.length}</span>
                </div>
              </div>
            </div>
          </header>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
              <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                <KeyRound className="h-5 w-5 text-neon-cyan" />
                <div>
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('credentials.title')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('credentials.description')}
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {state.integrationCredentials.map((credential) => (
                  <article
                    key={credential.id}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {credential.label}
                        </h3>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {portalT(`integrationCredentialKinds.${credential.kind}`)}
                        </p>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {credential.notes[0]}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {portalT(`integrationCredentialStatuses.${credential.status}`)}
                        </p>
                        <p className="mt-2 text-xs font-mono text-muted-foreground">
                          {credential.lastRotatedAt
                            ? t('credentials.rotatedAt', { value: formatDateTime(credential.lastRotatedAt, locale) })
                            : t('credentials.notRotated')}
                        </p>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </article>

            <div className="space-y-6">
              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <div className="flex items-center gap-3">
                  <Waypoints className="h-5 w-5 text-neon-purple" />
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('delivery.title')}
                  </h2>
                </div>
                <div className="mt-4 space-y-3">
                  {state.integrationDeliveryLogs.map((item) => (
                    <article
                      key={item.id}
                      className="rounded-xl border border-grid-line/20 bg-terminal-bg/55 p-4"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {portalT(`integrationDeliveryChannels.${item.channel}`)}
                        </p>
                        <span className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan">
                          {portalT(`integrationDeliveryStatuses.${item.status}`)}
                        </span>
                      </div>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {item.destination}
                      </p>
                      <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                        {item.notes[0]}
                      </p>
                    </article>
                  ))}
                </div>
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('capabilities.title')}
                </h2>
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
                  {t('links.title')}
                </h2>
                <div className="mt-4 flex flex-col gap-3">
                  <Link href="/conversions" className="inline-flex items-center gap-2 text-sm font-mono text-neon-cyan underline underline-offset-4">
                    <span>{t('links.conversions')}</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                  <Link href="/cases" className="inline-flex items-center gap-2 text-sm font-mono text-neon-purple underline underline-offset-4">
                    <span>{t('links.cases')}</span>
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </Link>
                  <Link href="/reseller" className="inline-flex items-center gap-2 text-sm font-mono text-matrix-green underline underline-offset-4">
                    <span>{t('links.reseller')}</span>
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

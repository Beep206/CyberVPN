'use client';

import { Ticket, Waypoints } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { PartnerRouteGuard } from '@/features/partner-portal-state/components/partner-route-guard';
import type { PartnerRouteAccessLevel } from '@/features/partner-portal-state/lib/portal-access';
import {
  getPartnerCodeCapabilities,
  getPartnerCommercialSurfaceMode,
} from '@/features/partner-commercial/lib/commercial-capabilities';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';

function isWriteAccess(access: PartnerRouteAccessLevel) {
  return access === 'write' || access === 'admin';
}

export function CodesTrackingPage() {
  const t = useTranslations('Partner.codes');
  const portalT = useTranslations('Partner.portalState');
  const { state } = usePartnerPortalRuntimeState();
  const mode = getPartnerCommercialSurfaceMode('codes', state);
  const capabilities = getPartnerCodeCapabilities(state);

  return (
    <PartnerRouteGuard route="codes" title={t('title')}>
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

              <div className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-4 text-sm font-mono text-muted-foreground lg:w-[340px]">
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
                    {portalT(`commercialModes.${mode}`)}
                  </span>
                </div>
                <div className="mt-3 flex items-center justify-between gap-3">
                  <span>{t('summary.governance')}</span>
                  <span className="text-foreground">
                    {portalT(`governanceStates.${state.governanceState}`)}
                  </span>
                </div>
              </div>
            </div>
          </header>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(0,0.95fr)]">
            <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
              <div className="flex items-center gap-3 border-b border-grid-line/20 pb-4">
                <Ticket className="h-5 w-5 text-neon-cyan" />
                <div>
                  <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                    {t('inventory.title')}
                  </h2>
                  <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                    {t('inventory.description')}
                  </p>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                {state.codes.length > 0 ? state.codes.map((code) => (
                  <article
                    key={code.id}
                    className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4"
                  >
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-sm font-display uppercase tracking-[0.16em] text-white">
                          {code.label}
                        </h3>
                        <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                          {t('inventory.destination', { value: code.destination })}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-neon-cyan/80">
                          {portalT(`codeKinds.${code.kind}`)}
                        </p>
                        <p className="mt-2 text-xs font-mono text-muted-foreground">
                          {portalT(`codeStatuses.${code.status}`)}
                        </p>
                      </div>
                    </div>
                    <ul className="mt-4 space-y-2 text-sm font-mono text-muted-foreground">
                      {code.notes.map((note) => (
                        <li key={note}>{note}</li>
                      ))}
                    </ul>
                  </article>
                )) : (
                  <p className="rounded-2xl border border-dashed border-grid-line/25 bg-terminal-surface/25 p-4 text-sm font-mono leading-6 text-muted-foreground">
                    {t('inventory.empty')}
                  </p>
                )}
              </div>
            </article>

            <div className="space-y-6">
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
                        {portalT(`capabilityAvailability.${capability.availability}`)}
                      </span>
                    </li>
                  ))}
                </ul>
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('actions.title')}
                </h2>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {!isWriteAccess(access) || mode === 'read_only'
                    ? t('actions.readOnly')
                    : mode === 'starter'
                      ? t('actions.starter')
                      : mode === 'controlled'
                        ? t('actions.controlled')
                        : t('actions.full')}
                </p>
              </article>

              <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5 shadow-[0_0_24px_rgba(0,255,255,0.04)] md:p-6">
                <h2 className="text-lg font-display uppercase tracking-[0.18em] text-white">
                  {t('links.title')}
                </h2>
                <div className="mt-4 flex flex-col gap-3">
                  <Link href="/campaigns" className="text-sm font-mono text-neon-cyan underline underline-offset-4">
                    {t('links.campaigns')}
                  </Link>
                  <Link href="/compliance" className="text-sm font-mono text-neon-purple underline underline-offset-4">
                    {t('links.compliance')}
                  </Link>
                  <Link href="/programs" className="text-sm font-mono text-matrix-green underline underline-offset-4">
                    {t('links.programs')}
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

'use client';

import { ArrowUpRight, LockKeyhole } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import {
  PARTNER_NAV_ITEMS,
  getPartnerRouteRequiredReleaseRing,
} from '@/features/partner-shell/config/section-registry';
import { AdminSectionOverview } from '@/shared/ui/pages/admin-section-overview';
import { getPartnerRoleRouteAccess } from '@/features/partner-portal-state/lib/portal-access';
import {
  getPartnerRouteBlockReason,
  getPartnerRouteVisibility,
  type PartnerRouteKey,
} from '@/features/partner-portal-state/lib/portal-visibility';
import { usePartnerPortalBootstrapState } from '@/features/partner-portal-state/lib/use-partner-portal-bootstrap-state';

interface PartnerSectionOverviewClientProps {
  section: PartnerRouteKey;
  title: string;
  description: string;
  currentState: string;
  backendCoverage: string;
  nextFocus: string;
  availableNowLabel: string;
  nextModulesLabel: string;
  currentStateLabel: string;
  backendCoverageLabel: string;
  nextFocusLabel: string;
  returnToDashboardLabel: string;
  availableNow: readonly string[];
  nextModules: readonly string[];
  readinessTone: 'strong' | 'partial' | 'blocked';
  requiredAccessLabel: string;
}

export function PartnerSectionOverviewClient({
  section,
  requiredAccessLabel,
  ...overviewProps
}: PartnerSectionOverviewClientProps) {
  const t = useTranslations('Partner.portalState');
  const { state } = usePartnerPortalBootstrapState();
  const visibility = getPartnerRouteVisibility(section, state);
  const routeAccess = getPartnerRoleRouteAccess(section, state);
  const blockReason = getPartnerRouteBlockReason(section, state);
  const requiredReleaseRing = getPartnerRouteRequiredReleaseRing(section);
  const sectionIcon = PARTNER_NAV_ITEMS.find((item) => item.href === `/${section}`)?.icon;

  if (visibility === 'hidden' || routeAccess === 'none') {
    return (
      <section className="rounded-[1.75rem] border border-grid-line/20 bg-terminal-bg/85 px-4 py-5 text-foreground shadow-[0_0_40px_rgba(0,255,255,0.04)] md:px-8 md:py-8">
        <div className="mx-auto max-w-5xl space-y-6">
          <header className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 md:p-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-neon-pink/30 bg-neon-pink/10 text-neon-pink">
                  <LockKeyhole className="h-5 w-5" />
                </div>
                <div>
                  <h1 className="text-2xl font-display tracking-[0.18em] text-white md:text-3xl">
                    {overviewProps.title}
                  </h1>
                  <p className="mt-3 max-w-3xl text-sm font-mono leading-6 text-muted-foreground">
                    {blockReason === 'release_ring'
                      ? t('sectionAccess.releaseRingBlockedDescription', {
                          section: overviewProps.title,
                          currentRing: t(`releaseRings.${state.releaseRing}`),
                          requiredRing: t(`releaseRings.${requiredReleaseRing}`),
                        })
                      : routeAccess === 'none'
                        ? t('sectionAccess.roleBlockedDescription', {
                            section: overviewProps.title,
                            role: t(`workspaceRoles.${state.workspaceRole}`),
                          })
                        : t('sectionAccess.blockedDescription', { section: overviewProps.title })}
                  </p>
                </div>
              </div>
              <span className="inline-flex rounded-full border border-neon-pink/30 bg-neon-pink/10 px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em] text-neon-pink">
                {t(`routeVisibility.${visibility}`)}
              </span>
            </div>
          </header>

          <div className="grid gap-4 lg:grid-cols-3">
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-5">
              <h2 className="text-xs font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                {t('sectionAccess.currentStatusLabel')}
              </h2>
              <p className="mt-3 text-sm font-mono leading-6 text-foreground/90">
                {t(`workspaceStatuses.${state.workspaceStatus}`)}
              </p>
            </article>
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-5">
              <h2 className="text-xs font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                {t('sectionAccess.requiredAccessLabel')}
              </h2>
              <p className="mt-3 text-sm font-mono leading-6 text-foreground/90">
                {requiredAccessLabel}
              </p>
            </article>
            <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-5">
              <h2 className="text-xs font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                {t('sectionAccess.currentAccessLabel')}
              </h2>
              <p className="mt-3 text-sm font-mono leading-6 text-foreground/90">
                {t(`routeAccess.${routeAccess}`)}
              </p>
            </article>
            {blockReason === 'release_ring' ? (
              <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/30 p-5">
                <h2 className="text-xs font-mono uppercase tracking-[0.24em] text-neon-cyan/80">
                  {t('sectionAccess.requiredReleaseRingLabel')}
                </h2>
                <p className="mt-3 text-sm font-mono leading-6 text-foreground/90">
                  {t(`releaseRings.${requiredReleaseRing}`)}
                </p>
                <p className="mt-2 text-xs font-mono leading-5 text-muted-foreground">
                  {t('sectionAccess.currentReleaseRingLabel')}: {t(`releaseRings.${state.releaseRing}`)}
                </p>
              </article>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-3">
            {routeAccess === 'none' && blockReason !== 'release_ring' ? (
              <Link
                href="/settings"
                className="inline-flex items-center gap-2 rounded-full border border-grid-line/30 bg-terminal-bg/70 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan/40 hover:text-white"
              >
                <span>{t('sectionAccess.settingsLink')}</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            ) : (
              <Link
                href="/application"
                className="inline-flex items-center gap-2 rounded-full border border-grid-line/30 bg-terminal-bg/70 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan/40 hover:text-white"
              >
                <span>{t('sectionAccess.applicationLink')}</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            )}
            {blockReason === 'release_ring' ? (
              <Link
                href="/notifications"
                className="inline-flex items-center gap-2 rounded-full border border-grid-line/30 bg-terminal-bg/70 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-purple transition-colors hover:border-neon-purple/40 hover:text-white"
              >
                <span>{t('sectionAccess.notificationsLink')}</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            ) : (
              <Link
                href="/cases"
                className="inline-flex items-center gap-2 rounded-full border border-grid-line/30 bg-terminal-bg/70 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-purple transition-colors hover:border-neon-purple/40 hover:text-white"
              >
                <span>{t('sectionAccess.casesLink')}</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            )}
          </div>
        </div>
      </section>
    );
  }

  return (
    <div className="space-y-4">
      {visibility !== 'full' ? (
        <div className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 px-4 py-3 text-sm font-mono text-muted-foreground">
          {t('sectionAccess.banner', {
            access: t(`routeAccess.${routeAccess}`),
            status: t(`workspaceStatuses.${state.workspaceStatus}`),
          })}
        </div>
      ) : null}
      {sectionIcon ? (
        <AdminSectionOverview
          {...overviewProps}
          icon={sectionIcon}
        />
      ) : null}
    </div>
  );
}

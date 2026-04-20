'use client';

import type { ReactNode } from 'react';
import { ArrowUpRight, LockKeyhole } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { getPartnerRouteRequiredReleaseRing } from '@/features/partner-shell/config/section-registry';
import type { PartnerRouteKey } from '@/features/partner-portal-state/lib/portal-visibility';
import {
  getPartnerRouteBlockReason,
  getPartnerRouteVisibility,
} from '@/features/partner-portal-state/lib/portal-visibility';
import { getPartnerRoleRouteAccess } from '@/features/partner-portal-state/lib/portal-access';
import { usePartnerPortalRuntimeState } from '@/features/partner-portal-state/lib/use-partner-portal-runtime-state';

export function PartnerRouteGuard({
  route,
  title,
  children,
}: {
  route: PartnerRouteKey;
  title: string;
  children: (access: ReturnType<typeof getPartnerRoleRouteAccess>) => ReactNode;
}) {
  const t = useTranslations('Partner.portalState');
  const { state } = usePartnerPortalRuntimeState();
  const access = getPartnerRoleRouteAccess(route, state);
  const visibility = getPartnerRouteVisibility(route, state);
  const blockReason = getPartnerRouteBlockReason(route, state);

  if (access === 'none') {
    const blockedByVisibility = visibility === 'hidden';
    const requiredReleaseRing = getPartnerRouteRequiredReleaseRing(route);

    return (
      <section className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/85 p-5 shadow-[0_0_32px_rgba(0,255,255,0.04)] md:p-7">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-neon-pink/30 bg-neon-pink/10 text-neon-pink">
            <LockKeyhole className="h-5 w-5" />
          </div>
          <div className="space-y-3">
            <h1 className="text-2xl font-display tracking-[0.16em] text-white md:text-3xl">
              {title}
            </h1>
            <p className="max-w-3xl text-sm font-mono leading-6 text-muted-foreground">
              {blockReason === 'release_ring'
                ? t('sectionAccess.releaseRingBlockedDescription', {
                    section: title,
                    currentRing: t(`releaseRings.${state.releaseRing}`),
                    requiredRing: t(`releaseRings.${requiredReleaseRing}`),
                  })
                : blockedByVisibility
                ? t('sectionAccess.blockedDescription', { section: title })
                : t('sectionAccess.roleBlockedDescription', {
                    section: title,
                    role: t(`workspaceRoles.${state.workspaceRole}`),
                  })}
            </p>
            {blockReason === 'release_ring' ? (
              <div className="flex flex-wrap gap-3 text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                <span className="rounded-full border border-grid-line/25 bg-terminal-surface/35 px-3 py-1">
                  {t('sectionAccess.currentReleaseRingLabel')}: {t(`releaseRings.${state.releaseRing}`)}
                </span>
                <span className="rounded-full border border-grid-line/25 bg-terminal-surface/35 px-3 py-1">
                  {t('sectionAccess.requiredReleaseRingLabel')}: {t(`releaseRings.${requiredReleaseRing}`)}
                </span>
              </div>
            ) : null}
            <div className="flex flex-wrap gap-3">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 rounded-full border border-grid-line/30 bg-terminal-bg/70 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan/40 hover:text-white"
              >
                <span>{t('sectionAccess.dashboardLink')}</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
              {blockReason === 'release_ring' ? (
                <Link
                  href="/notifications"
                  className="inline-flex items-center gap-2 rounded-full border border-grid-line/30 bg-terminal-bg/70 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-purple transition-colors hover:border-neon-purple/40 hover:text-white"
                >
                  <span>{t('sectionAccess.notificationsLink')}</span>
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              ) : blockedByVisibility ? (
                <Link
                  href="/cases"
                  className="inline-flex items-center gap-2 rounded-full border border-grid-line/30 bg-terminal-bg/70 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-purple transition-colors hover:border-neon-purple/40 hover:text-white"
                >
                  <span>{t('sectionAccess.casesLink')}</span>
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              ) : (
                <Link
                  href="/settings"
                  className="inline-flex items-center gap-2 rounded-full border border-grid-line/30 bg-terminal-bg/70 px-4 py-2 text-xs font-mono uppercase tracking-[0.18em] text-neon-purple transition-colors hover:border-neon-purple/40 hover:text-white"
                >
                  <span>{t('sectionAccess.settingsLink')}</span>
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              )}
            </div>
          </div>
        </div>
      </section>
    );
  }

  return <>{children(access)}</>;
}

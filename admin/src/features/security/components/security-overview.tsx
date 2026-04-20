'use client';

import {
  Activity,
  Key,
  Route,
  ShieldCheck,
  Smartphone,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useLocale, useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { authApi } from '@/lib/api/auth';
import { securityApi } from '@/lib/api/security';
import { twofaApi } from '@/lib/api/twofa';
import { SecurityEmptyState } from '@/features/security/components/security-empty-state';
import { SecurityPageShell } from '@/features/security/components/security-page-shell';
import { SecurityStatusChip } from '@/features/security/components/security-status-chip';
import {
  calculateSecurityScore,
  formatDateTime,
  getSecurityTier,
} from '@/features/security/lib/formatting';

function getToneForTier(tier: ReturnType<typeof getSecurityTier>) {
  if (tier === 'strong') return 'success' as const;
  if (tier === 'moderate') return 'warning' as const;
  return 'danger' as const;
}

export function SecurityOverview() {
  const t = useTranslations('AdminSecurity');
  const locale = useLocale();

  const sessionQuery = useQuery({
    queryKey: ['security', 'session'],
    queryFn: async () => {
      const response = await authApi.session();
      return response.data;
    },
    staleTime: 30_000,
  });

  const devicesQuery = useQuery({
    queryKey: ['security', 'devices'],
    queryFn: async () => {
      const response = await authApi.listDevices();
      return response.data;
    },
    staleTime: 15_000,
  });

  const twoFactorQuery = useQuery({
    queryKey: ['security', 'two-factor', 'status'],
    queryFn: async () => {
      const response = await twofaApi.getStatus();
      return response.data;
    },
    staleTime: 15_000,
  });

  const antiPhishingQuery = useQuery({
    queryKey: ['security', 'anti-phishing'],
    queryFn: async () => {
      const response = await securityApi.getAntiphishingCode();
      return response.data;
    },
    staleTime: 15_000,
  });

  const session = sessionQuery.data;
  const devices = devicesQuery.data?.devices ?? [];
  const twoFactorEnabled = twoFactorQuery.data?.status === 'enabled';
  const hasAntiPhishing = Boolean(antiPhishingQuery.data?.code);
  const score = calculateSecurityScore({
    deviceCount: devices.length,
    hasAntiPhishing,
    isActive: Boolean(session?.is_active),
    isEmailVerified: Boolean(session?.is_email_verified),
    isTwoFactorEnabled: twoFactorEnabled,
  });
  const postureTier = getSecurityTier(score);

  const signals = [
    {
      label: t('overview.signals.twoFactor'),
      value: twoFactorEnabled ? t('common.enabled') : t('common.disabled'),
      tone: twoFactorEnabled ? 'success' : 'danger',
      hint: t('overview.signals.twoFactorHint'),
    },
    {
      label: t('overview.signals.antiPhishing'),
      value: hasAntiPhishing ? t('common.enabled') : t('common.disabled'),
      tone: hasAntiPhishing ? 'success' : 'warning',
      hint: t('overview.signals.antiPhishingHint'),
    },
    {
      label: t('overview.signals.email'),
      value: session?.is_email_verified ? t('common.verified') : t('common.unverified'),
      tone: session?.is_email_verified ? 'success' : 'warning',
      hint: t('overview.signals.emailHint'),
    },
    {
      label: t('overview.signals.account'),
      value: session?.is_active ? t('common.active') : t('common.disabled'),
      tone: session?.is_active ? 'info' : 'danger',
      hint: t('overview.signals.accountHint'),
    },
  ] as const;

  return (
    <SecurityPageShell
      eyebrow={t('overview.eyebrow')}
      title={t('overview.title')}
      description={t('overview.description')}
      icon={ShieldCheck}
      metrics={[
        {
          label: t('overview.metrics.score'),
          value: `${score}%`,
          hint: t(`overview.metrics.${postureTier}Hint`),
          tone: getToneForTier(postureTier),
        },
        {
          label: t('overview.metrics.sessions'),
          value: String(devices.length),
          hint: t('overview.metrics.sessionsHint'),
          tone: devices.length > 3 ? 'warning' : 'info',
        },
        {
          label: t('overview.metrics.twoFactor'),
          value: twoFactorEnabled ? t('common.enabled') : t('common.disabled'),
          hint: t('overview.metrics.twoFactorHint'),
          tone: twoFactorEnabled ? 'success' : 'danger',
        },
        {
          label: t('overview.metrics.antiPhishing'),
          value: hasAntiPhishing ? t('common.enabled') : t('common.disabled'),
          hint: t('overview.metrics.antiPhishingHint'),
          tone: hasAntiPhishing ? 'success' : 'warning',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-5">
          <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
            {t('overview.routesTitle')}
          </h2>
          <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
            {t('overview.routesDescription')}
          </p>

          <div className="mt-5 grid gap-3">
            {[
              { href: '/security/review-queue', title: t('nav.reviewQueue'), description: t('overview.routes.reviewQueue') },
              { href: '/security/sessions', title: t('nav.sessions'), description: t('overview.routes.sessions') },
              { href: '/security/two-factor', title: t('nav.twoFactor'), description: t('overview.routes.twoFactor') },
              { href: '/security/anti-phishing', title: t('nav.antiPhishing'), description: t('overview.routes.antiPhishing') },
              { href: '/security/posture', title: t('nav.posture'), description: t('overview.routes.posture') },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4 transition-colors hover:border-neon-pink/35 hover:bg-terminal-bg/60"
              >
                <p className="text-sm font-display uppercase tracking-[0.18em] text-white">
                  {item.title}
                </p>
                <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
                  {item.description}
                </p>
              </Link>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-pink">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.signalsTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.signalsDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {signals.map((signal) => (
              <div
                key={signal.label}
                className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                    {signal.label}
                  </p>
                  <SecurityStatusChip label={signal.value} tone={signal.tone} />
                </div>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {signal.hint}
                </p>
              </div>
            ))}
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-pink">
              <Smartphone className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.sessionsTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.sessionsDescription')}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.sessionStats.total')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                {devices.length}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.sessionStats.currentIp')}
              </p>
              <p className="mt-3 text-sm font-mono leading-6 text-white">
                {session?.current_sign_in_ip ?? '--'}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.sessionStats.lastLogin')}
              </p>
              <p className="mt-3 text-sm font-mono leading-6 text-white">
                {formatDateTime(session?.last_login_at, locale)}
              </p>
            </div>
            <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
              <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {t('overview.sessionStats.signIns')}
              </p>
              <p className="mt-3 text-2xl font-display tracking-[0.12em] text-white">
                {session?.sign_in_count ?? 0}
              </p>
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-pink">
              <Key className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.identityTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t('overview.identityDescription')}
              </p>
            </div>
          </div>

          {session ? (
            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.email')}
                </p>
                <p className="mt-3 text-sm font-mono leading-6 text-white">
                  {session.email ?? '--'}
                </p>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.role')}
                </p>
                <p className="mt-3 text-sm font-mono leading-6 uppercase text-white">
                  {session.role}
                </p>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('overview.identity.createdAt')}
                </p>
                <p className="mt-3 text-sm font-mono leading-6 text-white">
                  {formatDateTime(session.created_at, locale)}
                </p>
              </div>
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('overview.identity.accountState')}
                </p>
                <div className="mt-3">
                  <SecurityStatusChip
                    label={session.is_active ? t('common.active') : t('common.disabled')}
                    tone={session.is_active ? 'success' : 'danger'}
                  />
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-5">
              <SecurityEmptyState label={t('common.loading')} />
            </div>
          )}
        </article>

        <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur xl:col-span-12">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-grid-line/20 bg-terminal-bg/60 text-neon-pink">
              <Route className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
                {t('overview.guidanceTitle')}
              </h2>
              <p className="mt-1 text-sm font-mono text-muted-foreground">
                {t(`overview.guidance.${postureTier}`)}
              </p>
            </div>
          </div>
        </article>
      </div>
    </SecurityPageShell>
  );
}

'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  LockKeyhole,
  ShieldCheck,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { authApi } from '@/lib/api/auth';
import { securityApi } from '@/lib/api/security';
import { twofaApi } from '@/lib/api/twofa';
import { SecurityEmptyState } from '@/features/security/components/security-empty-state';
import { SecurityPageShell } from '@/features/security/components/security-page-shell';
import { SecurityStatusChip } from '@/features/security/components/security-status-chip';
import {
  calculateSecurityScore,
  formatDateTime,
  getErrorMessage,
  getSecurityTier,
} from '@/features/security/lib/formatting';

function getToneForTier(tier: ReturnType<typeof getSecurityTier>) {
  if (tier === 'strong') return 'success' as const;
  if (tier === 'moderate') return 'warning' as const;
  return 'danger' as const;
}

export function SecurityPostureConsole() {
  const t = useTranslations('AdminSecurity');
  const locale = useLocale();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [feedback, setFeedback] = useState<string | null>(null);

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

  const changePasswordMutation = useMutation({
    mutationFn: (payload: {
      current_password: string;
      new_password: string;
      new_password_confirm: string;
    }) => securityApi.changePassword(payload),
    onSuccess: (response) => {
      setCurrentPassword('');
      setNewPassword('');
      setNewPasswordConfirm('');
      setFeedback(response.data.message || t('posture.passwordChangeSuccess'));
    },
    onError: (error) => {
      setFeedback(getErrorMessage(error, t('common.actionFailed')));
    },
  });

  const session = sessionQuery.data;
  const devices = devicesQuery.data?.devices ?? [];
  const score = calculateSecurityScore({
    deviceCount: devices.length,
    hasAntiPhishing: Boolean(antiPhishingQuery.data?.code),
    isActive: Boolean(session?.is_active),
    isEmailVerified: Boolean(session?.is_email_verified),
    isTwoFactorEnabled: twoFactorQuery.data?.status === 'enabled',
  });
  const tier = getSecurityTier(score);

  const postureSignals = [
    {
      label: t('posture.signals.twoFactor'),
      value:
        twoFactorQuery.data?.status === 'enabled'
          ? t('common.enabled')
          : t('common.disabled'),
      tone: twoFactorQuery.data?.status === 'enabled' ? 'success' : 'danger',
      hint: t('posture.signals.twoFactorHint'),
    },
    {
      label: t('posture.signals.antiPhishing'),
      value: antiPhishingQuery.data?.code ? t('common.enabled') : t('common.pending'),
      tone: antiPhishingQuery.data?.code ? 'success' : 'warning',
      hint: t('posture.signals.antiPhishingHint'),
    },
    {
      label: t('posture.signals.email'),
      value: session?.is_email_verified ? t('common.verified') : t('common.unverified'),
      tone: session?.is_email_verified ? 'success' : 'warning',
      hint: t('posture.signals.emailHint'),
    },
    {
      label: t('posture.signals.sessions'),
      value: String(devices.length),
      tone: devices.length > 3 ? 'warning' : 'info',
      hint: t('posture.signals.sessionsHint'),
    },
  ] as const;

  return (
    <SecurityPageShell
      eyebrow={t('posture.eyebrow')}
      title={t('posture.title')}
      description={t('posture.description')}
      icon={LockKeyhole}
      metrics={[
        {
          label: t('posture.metrics.score'),
          value: `${score}%`,
          hint: t(`posture.metrics.${tier}Hint`),
          tone: getToneForTier(tier),
        },
        {
          label: t('posture.metrics.signIns'),
          value: String(session?.sign_in_count ?? 0),
          hint: t('posture.metrics.signInsHint'),
          tone: 'info',
        },
        {
          label: t('posture.metrics.lastLogin'),
          value: formatDateTime(session?.last_login_at, locale),
          hint: t('posture.metrics.lastLoginHint'),
          tone: 'neutral',
        },
        {
          label: t('posture.metrics.sessions'),
          value: String(devices.length),
          hint: t('posture.metrics.sessionsHint'),
          tone: devices.length > 3 ? 'warning' : 'success',
        },
      ]}
    >
      <div className="grid gap-6 xl:grid-cols-12">
        <section className="space-y-6 xl:col-span-7">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('posture.signalsTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('posture.signalsDescription')}
            </p>

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              {postureSignals.map((signal) => (
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

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('posture.accountTitle')}
            </h2>

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
                  <p className="mt-3 text-sm font-mono uppercase leading-6 text-white">
                    {session.role}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.currentIp')}
                  </p>
                  <p className="mt-3 text-sm font-mono leading-6 text-white">
                    {session.current_sign_in_ip ?? '--'}
                  </p>
                </div>
                <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                  <p className="text-[11px] font-mono uppercase tracking-[0.18em] text-muted-foreground">
                    {t('common.createdAt')}
                  </p>
                  <p className="mt-3 text-sm font-mono leading-6 text-white">
                    {formatDateTime(session.created_at, locale)}
                  </p>
                </div>
              </div>
            ) : (
              <div className="mt-5">
                <SecurityEmptyState label={t('common.loading')} />
              </div>
            )}
          </article>
        </section>

        <section className="space-y-6 xl:col-span-5">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('posture.passwordTitle')}
            </h2>
            <p className="mt-2 text-sm font-mono leading-6 text-muted-foreground">
              {t('posture.passwordDescription')}
            </p>

            {feedback ? (
              <div className="mt-5 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-4 py-3 text-sm font-mono text-foreground">
                {feedback}
              </div>
            ) : null}

            <div className="mt-5 space-y-4">
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.currentPassword')}
                </span>
                <Input
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  placeholder={t('posture.currentPasswordPlaceholder')}
                />
              </label>
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.newPassword')}
                </span>
                <Input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  placeholder={t('posture.newPasswordPlaceholder')}
                />
              </label>
              <label className="block space-y-2">
                <span className="text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                  {t('common.newPasswordConfirm')}
                </span>
                <Input
                  type="password"
                  value={newPasswordConfirm}
                  onChange={(event) => setNewPasswordConfirm(event.target.value)}
                  placeholder={t('posture.confirmPasswordPlaceholder')}
                />
              </label>
              <Button
                type="button"
                magnetic={false}
                disabled={changePasswordMutation.isPending}
                onClick={() => {
                  if (!currentPassword.trim()) {
                    setFeedback(t('common.validation.passwordRequired'));
                    return;
                  }
                  if (!newPassword.trim()) {
                    setFeedback(t('common.validation.newPasswordRequired'));
                    return;
                  }
                  if (newPassword !== newPasswordConfirm) {
                    setFeedback(t('common.validation.passwordMismatch'));
                    return;
                  }
                  changePasswordMutation.mutate({
                    current_password: currentPassword,
                    new_password: newPassword,
                    new_password_confirm: newPasswordConfirm,
                  });
                }}
              >
                {t('posture.passwordAction')}
              </Button>
            </div>
          </article>

          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-5 backdrop-blur">
            <h2 className="text-sm font-display uppercase tracking-[0.24em] text-white">
              {t('posture.guidanceTitle')}
            </h2>
            <div className="mt-5 space-y-3">
              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-display uppercase tracking-[0.16em] text-white">
                    {t('posture.guidance.primary')}
                  </p>
                  <SecurityStatusChip
                    label={t(`posture.guidance.${tier}Label`)}
                    tone={getToneForTier(tier)}
                  />
                </div>
                <p className="mt-3 text-sm font-mono leading-6 text-muted-foreground">
                  {t(`posture.guidance.${tier}`)}
                </p>
              </div>

              <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/45 p-4">
                <div className="flex items-center gap-3">
                  <ShieldCheck className="h-4 w-4 text-neon-pink" />
                  <p className="text-sm font-mono leading-6 text-muted-foreground">
                    {t('posture.guidance.secondary')}
                  </p>
                </div>
              </div>
            </div>
          </article>
        </section>
      </div>
    </SecurityPageShell>
  );
}

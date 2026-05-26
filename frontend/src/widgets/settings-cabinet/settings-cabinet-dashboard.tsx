'use client';

import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Copy,
  Fingerprint,
  KeyRound,
  Laptop,
  Link2,
  LockKeyhole,
  Monitor,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Trash2,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useState, type FormEvent, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@/i18n/navigation';
import { useAuthStore } from '@/stores/auth-store';
import {
  authApi,
  entitlementsApi,
  growthNotificationsApi,
  profileApi,
  securityApi,
  twofaApi,
} from '@/lib/api';
import { markPerformance } from '@/shared/lib/web-vitals';
import { AntiphishingModal } from '@/app/[locale]/(dashboard)/settings/components/AntiphishingModal';
import { ChangePasswordModal } from '@/app/[locale]/(dashboard)/settings/components/ChangePasswordModal';
import { TwoFactorModal } from '@/app/[locale]/(dashboard)/settings/components/TwoFactorModal';
import {
  buildCoreNotificationPatch,
  buildGrowthNotificationPatch,
  CORE_NOTIFICATION_PREFERENCES,
  formatDateTime,
  formatShortId,
  getDeviceLimitSummary,
  getDeviceKind,
  getEnabledCount,
  getSecurityPosture,
  GROWTH_NOTIFICATION_PREFERENCES,
  getProfileTimezoneOptions,
  maskAntiphishingCode,
  parseDeviceLabel,
  PROFILE_LANGUAGE_OPTIONS,
  readDeviceLimit,
  type CoreNotificationPreferenceKey,
  type DeviceLimitState,
  type GrowthNotificationPreferenceKey,
  type ProfileUpdate,
  type StatusTone,
} from './settings-cabinet-model';

const PROFILE_STALE_MS = 5 * 60_000;
const SECURITY_STALE_MS = 45_000;

const toneClasses: Record<StatusTone, { border: string; fill: string; text: string }> = {
  amber: {
    border: 'border-amber-400/30',
    fill: 'bg-amber-400/10',
    text: 'text-amber-300',
  },
  cyan: {
    border: 'border-neon-cyan/30',
    fill: 'bg-neon-cyan/10',
    text: 'text-neon-cyan',
  },
  green: {
    border: 'border-matrix-green/30',
    fill: 'bg-matrix-green/10',
    text: 'text-matrix-green',
  },
  muted: {
    border: 'border-grid-line/30',
    fill: 'bg-terminal-bg/40',
    text: 'text-muted-foreground',
  },
  pink: {
    border: 'border-neon-pink/30',
    fill: 'bg-neon-pink/10',
    text: 'text-neon-pink',
  },
  purple: {
    border: 'border-neon-purple/30',
    fill: 'bg-neon-purple/10',
    text: 'text-neon-purple',
  },
};

type SensitiveModal = 'antiphishing' | 'password' | 'twoFactor' | null;

function StatusPill({ children, tone }: { children: ReactNode; tone: StatusTone }) {
  const classes = toneClasses[tone];

  return (
    <span
      className={`inline-flex min-h-8 items-center rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.18em] ${classes.border} ${classes.fill} ${classes.text}`}
    >
      {children}
    </span>
  );
}

function LoadingCard({ className = 'min-h-24' }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`${className} animate-pulse rounded-3xl border border-grid-line/30 bg-terminal-surface/40`}
    />
  );
}

function MetricCard({
  icon,
  label,
  tone = 'cyan',
  value,
}: {
  icon: ReactNode;
  label: string;
  tone?: StatusTone;
  value: string;
}) {
  return (
    <article className="rounded-2xl border border-grid-line/30 bg-terminal-surface/45 p-5">
      <div className={toneClasses[tone].text}>{icon}</div>
      <p className="mt-4 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
        {label}
      </p>
      <p className="mt-2 truncate text-2xl font-display text-white">{value}</p>
    </article>
  );
}

function getDeviceIcon(kind: 'desktop' | 'mobile' | 'tablet') {
  if (kind === 'mobile') {
    return Smartphone;
  }

  if (kind === 'tablet') {
    return Monitor;
  }

  return Laptop;
}

function getLimitHelpKey(state: DeviceLimitState) {
  return `devices.limitHelp.${state}` as const;
}

export function SettingsCabinetDashboard() {
  const t = useTranslations('Settings.cabinet');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const telegramMagicLinkAuth = useAuthStore((state) => state.telegramMagicLinkAuth);
  const authLoading = useAuthStore((state) => state.isLoading);
  const [activeModal, setActiveModal] = useState<SensitiveModal>(null);
  const [banner, setBanner] = useState<{ tone: StatusTone; text: string } | null>(null);
  const [copyState, setCopyState] = useState<'account' | 'idle'>('idle');
  const [isStartingTelegramLink, setIsStartingTelegramLink] = useState(false);
  const publicSiteBaseUrl = 'https://cyber-vpn.net';

  const profileQuery = useQuery({
    queryKey: ['settings', 'profile'],
    queryFn: async () => {
      const response = await profileApi.getProfile();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: PROFILE_STALE_MS,
  });

  const userQuery = useQuery({
    queryKey: ['settings', 'auth-user'],
    queryFn: async () => {
      const response = await authApi.me();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: PROFILE_STALE_MS,
  });

  const twoFactorQuery = useQuery({
    queryKey: ['settings', 'two-factor-status'],
    queryFn: async () => {
      const response = await twofaApi.getStatus();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: SECURITY_STALE_MS,
  });

  const antiphishingQuery = useQuery({
    queryKey: ['settings', 'antiphishing'],
    queryFn: async () => {
      const response = await securityApi.getAntiphishingCode();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: SECURITY_STALE_MS,
  });

  const coreNotificationsQuery = useQuery({
    queryKey: ['settings', 'notification-preferences', 'core'],
    queryFn: async () => {
      const response = await profileApi.getNotificationPreferences();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: PROFILE_STALE_MS,
  });

  const growthNotificationsQuery = useQuery({
    queryKey: ['settings', 'notification-preferences', 'growth'],
    queryFn: async () => {
      const response = await growthNotificationsApi.getPreferences();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: PROFILE_STALE_MS,
  });

  const devicesQuery = useQuery({
    queryKey: ['settings', 'devices'],
    queryFn: async () => {
      const response = await authApi.listDevices();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: SECURITY_STALE_MS,
  });

  const entitlementQuery = useQuery({
    queryKey: ['settings', 'entitlement'],
    queryFn: async () => {
      const response = await entitlementsApi.getCurrent();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: PROFILE_STALE_MS,
  });

  const profile = profileQuery.data ?? null;
  const user = userQuery.data ?? null;
  const twoFactorStatus = twoFactorQuery.data ?? null;
  const antiphishingCode = antiphishingQuery.data ?? null;
  const coreNotifications = coreNotificationsQuery.data ?? null;
  const growthNotifications = growthNotificationsQuery.data ?? null;
  const devices = devicesQuery.data?.devices ?? [];
  const entitlement = entitlementQuery.data ?? null;
  const timezoneOptions = getProfileTimezoneOptions();
  const selectedLanguage = PROFILE_LANGUAGE_OPTIONS.some(
    (option) => option.value === profile?.language,
  )
    ? profile?.language ?? ''
    : '';
  const selectedTimezone = timezoneOptions.some(
    (option) => option.value === profile?.timezone,
  )
    ? profile?.timezone ?? ''
    : '';
  const currentDevice = devices.find((device) => device.is_current) ?? null;
  const otherDevices = devices.filter((device) => !device.is_current && device.device_id);
  const deviceLimitSummary = getDeviceLimitSummary({
    active: devices.length,
    limit: readDeviceLimit(entitlement),
  });
  const deviceLimitText =
    entitlementQuery.isPending
      ? t('labels.loading')
      : deviceLimitSummary.limit === null
        ? t('devices.limitUnknown', { used: deviceLimitSummary.active })
        : t('devices.limitUsed', {
            limit: deviceLimitSummary.limit,
            used: deviceLimitSummary.active,
          });
  const deviceRemainingText =
    entitlementQuery.isPending || deviceLimitSummary.remaining === null
      ? t('labels.notAvailable')
      : String(Math.max(0, deviceLimitSummary.remaining));
  const deviceLimitHelp = t(getLimitHelpKey(deviceLimitSummary.state), {
    count: Math.abs(deviceLimitSummary.remaining ?? 0),
    remaining: Math.max(0, deviceLimitSummary.remaining ?? 0),
  });
  const posture = getSecurityPosture({
    antiPhishingCode: antiphishingCode,
    devices,
    notificationPreferences: coreNotifications,
    twoFactorStatus,
  });
  const hasAnyError =
    profileQuery.isError ||
    userQuery.isError ||
    twoFactorQuery.isError ||
    antiphishingQuery.isError ||
    coreNotificationsQuery.isError ||
    growthNotificationsQuery.isError ||
    entitlementQuery.isError ||
    devicesQuery.isError;

  const updateProfileMutation = useMutation({
    mutationFn: async (payload: ProfileUpdate) => {
      const response = await profileApi.updateProfile(payload);
      return response.data;
    },
    onSuccess: (updatedProfile) => {
      queryClient.setQueryData(['settings', 'profile'], updatedProfile);
      markPerformance('settings-profile-save', {
        changed_language: updatedProfile.language,
      });
      setBanner({ tone: 'green', text: t('feedback.profileSaved') });
    },
    onError: () => {
      setBanner({ tone: 'pink', text: t('feedback.profileFailed') });
    },
  });

  const updateCoreNotificationMutation = useMutation({
    mutationFn: async ({
      key,
      value,
    }: {
      key: CoreNotificationPreferenceKey;
      value: boolean;
    }) => {
      const response = await profileApi.updateNotificationPreferences(
        buildCoreNotificationPatch(key, value),
      );
      return response.data;
    },
    onSuccess: (updatedPreferences, variables) => {
      queryClient.setQueryData(
        ['settings', 'notification-preferences', 'core'],
        updatedPreferences,
      );
      markPerformance('settings-notification-toggle', {
        channel: 'core',
        enabled: variables.value,
        key: variables.key,
      });
    },
    onError: () => {
      setBanner({ tone: 'pink', text: t('feedback.notificationsFailed') });
    },
  });

  const updateGrowthNotificationMutation = useMutation({
    mutationFn: async ({
      key,
      value,
    }: {
      key: GrowthNotificationPreferenceKey;
      value: boolean;
    }) => {
      const response = await growthNotificationsApi.updatePreferences(
        buildGrowthNotificationPatch(key, value),
      );
      return response.data;
    },
    onSuccess: (updatedPreferences, variables) => {
      queryClient.setQueryData(
        ['settings', 'notification-preferences', 'growth'],
        updatedPreferences,
      );
      markPerformance('settings-notification-toggle', {
        channel: 'growth',
        enabled: variables.value,
        key: variables.key,
      });
    },
    onError: () => {
      setBanner({ tone: 'pink', text: t('feedback.notificationsFailed') });
    },
  });

  const revokeDeviceMutation = useMutation({
    mutationFn: async (deviceId: string) => {
      await authApi.logoutDevice(deviceId);
      return deviceId;
    },
    onSuccess: (deviceId) => {
      void queryClient.invalidateQueries({ queryKey: ['settings', 'devices'] });
      markPerformance('settings-device-revoke', {
        scope: 'single',
        target: formatShortId(deviceId),
      });
      setBanner({ tone: 'green', text: t('feedback.deviceRevoked') });
    },
    onError: () => {
      setBanner({ tone: 'pink', text: t('feedback.deviceFailed') });
    },
  });

  const revokeOtherDevicesMutation = useMutation({
    mutationFn: async () => {
      await Promise.all(
        otherDevices.map((device) => authApi.logoutDevice(String(device.device_id))),
      );
      return otherDevices.length;
    },
    onSuccess: (count) => {
      void queryClient.invalidateQueries({ queryKey: ['settings', 'devices'] });
      markPerformance('settings-device-revoke', {
        count,
        scope: 'others',
      });
      setBanner({ tone: 'green', text: t('feedback.devicesRevoked', { count }) });
    },
    onError: () => {
      setBanner({ tone: 'pink', text: t('feedback.deviceFailed') });
    },
  });

  const openModal = (modal: SensitiveModal) => {
    setActiveModal(modal);
    if (modal) {
      markPerformance('settings-security-action-open', { modal });
    }
  };

  const saveProfile = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    updateProfileMutation.mutate({
      display_name: String(formData.get('display_name') ?? '').trim() || null,
      language: String(formData.get('language') ?? '').trim() || null,
      timezone: String(formData.get('timezone') ?? '').trim() || null,
    });
  };

  const refreshAll = () =>
    Promise.all([
      profileQuery.refetch(),
      userQuery.refetch(),
      twoFactorQuery.refetch(),
      antiphishingQuery.refetch(),
      coreNotificationsQuery.refetch(),
      growthNotificationsQuery.refetch(),
      entitlementQuery.refetch(),
      devicesQuery.refetch(),
    ]);

  const copyAccountId = async () => {
    const clipboard = typeof navigator === 'undefined' ? undefined : navigator.clipboard;
    if (!profile?.id || typeof clipboard?.writeText !== 'function') {
      return;
    }

    try {
      await clipboard.writeText(profile.id);
      markPerformance('settings-account-id-copy');
      setCopyState('account');
      window.setTimeout(() => setCopyState('idle'), 1600);
    } catch {
      setBanner({ tone: 'pink', text: t('feedback.copyFailed') });
    }
  };

  const startTelegramLink = async () => {
    setIsStartingTelegramLink(true);
    try {
      await telegramMagicLinkAuth();
    } catch {
      setBanner({ tone: 'pink', text: t('feedback.telegramLinkFailed') });
      setIsStartingTelegramLink(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-[2rem] border border-neon-cyan/25 bg-terminal-surface/55 p-6 shadow-[0_0_70px_rgba(0,255,255,0.08)] backdrop-blur md:p-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(0,255,255,0.18),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(255,0,255,0.13),transparent_32%)]" />
        <div className="relative grid gap-6 xl:grid-cols-[1.1fr_0.9fr] xl:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.34em] text-neon-cyan">
              {t('hero.eyebrow')}
            </p>
            <h1 className="mt-4 max-w-4xl text-4xl font-display tracking-[0.08em] text-white md:text-5xl">
              {t('title')}
            </h1>
            <p className="mt-4 max-w-3xl font-mono text-sm leading-7 text-muted-foreground">
              {t('subtitle')}
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => void refreshAll()}
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                {t('actions.refresh')}
              </button>
              <a
                href={`${publicSiteBaseUrl}/${locale}/delete-account`}
                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-neon-pink/35 bg-neon-pink/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-pink transition hover:bg-neon-pink/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
              >
                {t('actions.privacy')}
              </a>
            </div>
          </div>

          <div className="rounded-3xl border border-grid-line/30 bg-black/25 p-5">
            <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              {t('hero.securityPosture')}
            </p>
            <div className="mt-4 flex items-center gap-3">
              <ShieldCheck className={`h-6 w-6 ${toneClasses[posture.tone].text}`} aria-hidden="true" />
              <StatusPill tone={posture.tone}>{t(`posture.${posture.state}`)}</StatusPill>
            </div>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-grid-line/30">
              <div
                className="h-full rounded-full bg-matrix-green"
                style={{ width: `${posture.score}%` }}
              />
            </div>
            <p className="mt-4 font-mono text-sm leading-7 text-muted-foreground">
              {t('hero.securityScore', { score: posture.score })}
            </p>
          </div>
        </div>
      </section>

      {hasAnyError && (
        <section
          className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 font-mono text-sm text-amber-200"
          role="status"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
            <div>
              <p className="font-semibold">{t('errors.partialTitle')}</p>
              <p className="mt-1 text-amber-100/80">{t('errors.partialDescription')}</p>
            </div>
          </div>
        </section>
      )}

      {banner && (
        <section
          className={`rounded-2xl border p-4 font-mono text-sm ${toneClasses[banner.tone].border} ${toneClasses[banner.tone].fill} ${toneClasses[banner.tone].text}`}
          role="status"
        >
          {banner.text}
        </section>
      )}

      <section className="grid gap-4 md:grid-cols-4" aria-label={t('summary.ariaLabel')}>
        <MetricCard
          icon={<Fingerprint className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.twoFactor')}
          tone={twoFactorStatus?.status === 'enabled' ? 'green' : 'amber'}
          value={twoFactorStatus?.status === 'enabled' ? t('labels.enabled') : t('labels.disabled')}
        />
        <MetricCard
          icon={<KeyRound className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.antiphishing')}
          tone={antiphishingCode?.code ? 'green' : 'amber'}
          value={antiphishingCode?.code ? maskAntiphishingCode(antiphishingCode.code) : t('labels.notSet')}
        />
        <MetricCard
          icon={<Bell className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.notifications')}
          tone="cyan"
          value={String(
            getEnabledCount(coreNotifications) + getEnabledCount(growthNotifications),
          )}
        />
        <MetricCard
          icon={<Laptop className="h-5 w-5" aria-hidden="true" />}
          label={t('summary.devices')}
          tone={deviceLimitSummary.tone === 'muted' ? 'purple' : deviceLimitSummary.tone}
          value={
            deviceLimitSummary.limit === null
              ? String(devices.length)
              : `${devices.length}/${deviceLimitSummary.limit}`
          }
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <article className="rounded-[2rem] border border-neon-cyan/25 bg-terminal-surface/55 p-6 backdrop-blur">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
                {t('profile.eyebrow')}
              </p>
              <h2 className="mt-3 text-2xl font-display text-white">{t('profile.title')}</h2>
              <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
                {t('profile.description')}
              </p>
            </div>
            <StatusPill tone={profileQuery.isPending ? 'muted' : 'green'}>
              {profileQuery.isPending ? t('labels.loading') : t('labels.synced')}
            </StatusPill>
          </div>

          {profileQuery.isPending ? (
            <div className="mt-6 space-y-3">
              <LoadingCard />
              <LoadingCard />
            </div>
          ) : (
            <form key={profile?.id} className="mt-6 space-y-5" onSubmit={saveProfile}>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="space-y-2">
                  <span className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t('profile.email')}
                  </span>
                  <input
                    readOnly
                    value={profile?.email ?? t('labels.notAvailable')}
                    className="h-12 w-full rounded-xl border border-grid-line/40 bg-black/20 px-4 font-mono text-sm text-muted-foreground"
                  />
                </label>
                <label className="space-y-2">
                  <span className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t('profile.displayName')}
                  </span>
                  <input
                    defaultValue={profile?.display_name ?? ''}
                    maxLength={80}
                    name="display_name"
                    className="h-12 w-full rounded-xl border border-neon-cyan/30 bg-terminal-bg/70 px-4 font-mono text-sm text-white outline-hidden transition focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
                    placeholder={t('profile.displayNamePlaceholder')}
                  />
                </label>
                <label className="space-y-2">
                  <span className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t('profile.language')}
                  </span>
                  <select
                    defaultValue={selectedLanguage}
                    name="language"
                    className="h-12 w-full rounded-xl border border-neon-purple/30 bg-terminal-bg/70 px-4 font-mono text-sm text-white outline-hidden transition focus:border-neon-purple focus:ring-2 focus:ring-neon-purple/30"
                  >
                    <option value="">{t('labels.notSet')}</option>
                    {PROFILE_LANGUAGE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2">
                  <span className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t('profile.timezone')}
                  </span>
                  <select
                    defaultValue={selectedTimezone}
                    name="timezone"
                    className="h-12 w-full rounded-xl border border-matrix-green/30 bg-terminal-bg/70 px-4 font-mono text-sm text-white outline-hidden transition focus:border-matrix-green focus:ring-2 focus:ring-matrix-green/30"
                  >
                    <option value="">{t('labels.notSet')}</option>
                    {timezoneOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="flex flex-col gap-3 rounded-2xl border border-grid-line/30 bg-black/20 p-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
                    {t('profile.accountId')}
                  </p>
                  <p className="mt-1 break-all font-mono text-sm text-white">{profile?.id}</p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">
                    {t('profile.updatedAt', {
                      date: formatDateTime(profile?.updated_at, locale),
                    })}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void copyAccountId()}
                  disabled={!profile?.id}
                  className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-grid-line/40 bg-terminal-bg/60 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-muted-foreground transition hover:border-neon-cyan/40 hover:text-neon-cyan disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Copy className="h-4 w-4" aria-hidden="true" />
                  {copyState === 'account' ? t('actions.copied') : t('actions.copyId')}
                </button>
              </div>

              <button
                type="submit"
                disabled={updateProfileMutation.isPending || !profile}
                className="inline-flex min-h-12 w-full items-center justify-center rounded-xl border border-matrix-green/40 bg-matrix-green/10 px-5 py-3 font-mono text-xs uppercase tracking-[0.16em] text-matrix-green transition hover:bg-matrix-green/15 disabled:cursor-not-allowed disabled:opacity-50 md:w-auto"
              >
                {updateProfileMutation.isPending ? t('actions.saving') : t('actions.saveProfile')}
              </button>
            </form>
          )}
        </article>

        <article className="rounded-[2rem] border border-neon-purple/25 bg-terminal-surface/55 p-6 backdrop-blur">
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-purple">
            {t('security.eyebrow')}
          </p>
          <h2 className="mt-3 text-2xl font-display text-white">{t('security.title')}</h2>
          <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
            {t('security.description')}
          </p>

          <div className="mt-6 grid gap-3">
            {[
              {
                action: () => openModal('twoFactor'),
                description:
                  twoFactorStatus?.status === 'enabled'
                    ? t('security.twoFactor.enabled')
                    : t('security.twoFactor.disabled'),
                icon: <Fingerprint className="h-5 w-5" aria-hidden="true" />,
                label: t('security.twoFactor.title'),
                tone: (twoFactorStatus?.status === 'enabled' ? 'green' : 'amber') as StatusTone,
              },
              {
                action: () => openModal('password'),
                description: t('security.password.description'),
                icon: <LockKeyhole className="h-5 w-5" aria-hidden="true" />,
                label: t('security.password.title'),
                tone: 'cyan' as StatusTone,
              },
              {
                action: () => openModal('antiphishing'),
                description: antiphishingCode?.code
                  ? t('security.antiphishing.enabled', {
                      code: maskAntiphishingCode(antiphishingCode.code),
                    })
                  : t('security.antiphishing.disabled'),
                icon: <ShieldAlert className="h-5 w-5" aria-hidden="true" />,
                label: t('security.antiphishing.title'),
                tone: (antiphishingCode?.code ? 'green' : 'amber') as StatusTone,
              },
            ].map((item) => (
              <button
                key={item.label}
                type="button"
                onClick={item.action}
                className="rounded-2xl border border-grid-line/30 bg-black/20 p-4 text-left transition hover:border-neon-cyan/30 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <div className={toneClasses[item.tone].text}>{item.icon}</div>
                    <div>
                      <p className="font-mono text-sm text-white">{item.label}</p>
                      <p className="mt-1 font-mono text-xs leading-6 text-muted-foreground">
                        {item.description}
                      </p>
                    </div>
                  </div>
                  <StatusPill tone={item.tone}>{t('actions.manage')}</StatusPill>
                </div>
              </button>
            ))}
          </div>

          <div className="mt-5 rounded-2xl border border-amber-400/25 bg-amber-400/10 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-300" aria-hidden="true" />
              <div>
                <p className="font-mono text-sm text-white">{t('security.recovery.title')}</p>
                <p className="mt-1 font-mono text-xs leading-6 text-muted-foreground">
                  {t('security.recovery.description')}
                </p>
                <a
                  href={`${publicSiteBaseUrl}/${locale}/help`}
                  className="mt-3 inline-flex min-h-10 items-center rounded-xl border border-amber-400/35 bg-amber-400/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-amber-200 transition hover:bg-amber-400/15"
                >
                  {t('security.recovery.cta')}
                </a>
              </div>
            </div>
          </div>
        </article>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
        <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-matrix-green">
            {t('notifications.eyebrow')}
          </p>
          <h2 className="mt-3 text-2xl font-display text-white">{t('notifications.title')}</h2>
          <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
            {t('notifications.description')}
          </p>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              <p className="font-mono text-xs uppercase tracking-[0.22em] text-neon-cyan">
                {t('notifications.core.title')}
              </p>
              {coreNotificationsQuery.isPending ? (
                <LoadingCard className="min-h-72" />
              ) : (
                CORE_NOTIFICATION_PREFERENCES.map((preference) => (
                  <PreferenceToggle
                    key={preference.key}
                    checked={Boolean(coreNotifications?.[preference.key])}
                    description={t(preference.descriptionKey)}
                    disabled={updateCoreNotificationMutation.isPending}
                    label={t(preference.titleKey)}
                    onToggle={(value) =>
                      updateCoreNotificationMutation.mutate({
                        key: preference.key,
                        value,
                      })
                    }
                  />
                ))
              )}
            </div>

            <div className="space-y-3">
              <p className="font-mono text-xs uppercase tracking-[0.22em] text-neon-purple">
                {t('notifications.growth.title')}
              </p>
              {growthNotificationsQuery.isPending ? (
                <LoadingCard className="min-h-72" />
              ) : (
                GROWTH_NOTIFICATION_PREFERENCES.map((preference) => (
                  <PreferenceToggle
                    key={preference.key}
                    checked={Boolean(growthNotifications?.[preference.key])}
                    description={t(preference.descriptionKey)}
                    disabled={updateGrowthNotificationMutation.isPending}
                    label={t(preference.titleKey)}
                    onToggle={(value) =>
                      updateGrowthNotificationMutation.mutate({
                        key: preference.key,
                        value,
                      })
                    }
                  />
                ))
              )}
            </div>
          </div>
        </article>

        <article
          id="devices"
          className="scroll-mt-24 rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur"
        >
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-pink">
                {t('devices.eyebrow')}
              </p>
              <h2 className="mt-3 text-2xl font-display text-white">{t('devices.title')}</h2>
              <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
                {t('devices.description')}
              </p>
            </div>
            <button
              type="button"
              onClick={() => revokeOtherDevicesMutation.mutate()}
              disabled={otherDevices.length === 0 || revokeOtherDevicesMutation.isPending}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-pink/35 bg-neon-pink/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-pink transition hover:bg-neon-pink/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {t('devices.revokeOthers')}
            </button>
          </div>

          <div className="mt-6 rounded-3xl border border-grid-line/30 bg-black/20 p-5">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
                  {t('devices.limitTitle')}
                </p>
                <p className="mt-2 text-3xl font-display text-white">{deviceLimitText}</p>
                <p className="mt-2 font-mono text-xs leading-6 text-muted-foreground">
                  {t('devices.limitDescription')}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusPill tone={deviceLimitSummary.tone}>
                  {t(`devices.limitStates.${deviceLimitSummary.state}`)}
                </StatusPill>
                <Link
                  href="/subscriptions"
                  className="inline-flex min-h-10 items-center justify-center rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-cyan transition hover:bg-neon-cyan/15"
                >
                  {t('devices.managePlan')}
                </Link>
              </div>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  {t('devices.activeCount')}
                </p>
                <p className="mt-2 font-mono text-xl text-white">{devices.length}</p>
              </div>
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  {t('devices.planLimit')}
                </p>
                <p className="mt-2 font-mono text-xl text-white">
                  {entitlementQuery.isPending
                    ? t('labels.loading')
                    : deviceLimitSummary.limit ?? t('labels.notAvailable')}
                </p>
              </div>
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  {t('devices.remainingSlots')}
                </p>
                <p className="mt-2 font-mono text-xl text-white">{deviceRemainingText}</p>
              </div>
            </div>

            <div className="mt-5 h-2 overflow-hidden rounded-full bg-grid-line/30">
              <div
                className={`h-full rounded-full ${
                  deviceLimitSummary.tone === 'pink'
                    ? 'bg-neon-pink'
                    : deviceLimitSummary.tone === 'amber'
                      ? 'bg-amber-300'
                      : 'bg-matrix-green'
                }`}
                style={{ width: `${deviceLimitSummary.percent}%` }}
              />
            </div>
            <p className="mt-3 font-mono text-xs leading-6 text-muted-foreground">
              {deviceLimitHelp}
            </p>
          </div>

          {devicesQuery.isPending ? (
            <div className="mt-6 space-y-3">
              <LoadingCard />
              <LoadingCard />
            </div>
          ) : devices.length === 0 ? (
            <div className="mt-6 rounded-3xl border border-grid-line/30 bg-black/20 p-8 text-center">
              <Laptop className="mx-auto h-10 w-10 text-muted-foreground/60" aria-hidden="true" />
              <p className="mt-3 font-mono text-sm text-muted-foreground">{t('devices.empty')}</p>
            </div>
          ) : (
            <div className="mt-6 space-y-3">
              {devices.map((device) => {
                const deviceId = device.device_id ?? '';
                const deviceKind = getDeviceKind(device.user_agent);
                const Icon = getDeviceIcon(deviceKind);
                const isRevoking =
                  revokeDeviceMutation.isPending && revokeDeviceMutation.variables === deviceId;

                return (
                  <div
                    key={deviceId || `${device.user_agent}-${device.last_used_at}`}
                    className={`rounded-2xl border p-4 ${device.is_current ? 'border-matrix-green/35 bg-matrix-green/5' : 'border-grid-line/30 bg-black/20'}`}
                  >
                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                      <div className="flex items-start gap-3">
                        <div className={device.is_current ? 'text-matrix-green' : 'text-neon-cyan'}>
                          <Icon className="h-5 w-5" aria-hidden="true" />
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-mono text-sm text-white">
                              {parseDeviceLabel(device.user_agent)}
                            </p>
                            {device.is_current && (
                              <StatusPill tone="green">{t('devices.current')}</StatusPill>
                            )}
                          </div>
                          <p className="mt-2 font-mono text-xs leading-6 text-muted-foreground">
                            {t('devices.meta', {
                              date: formatDateTime(device.last_used_at, locale),
                              id: formatShortId(deviceId),
                              ip: device.ip_address ?? t('labels.notAvailable'),
                            })}
                          </p>
                          {currentDevice?.device_id === device.device_id && (
                            <p className="mt-1 font-mono text-xs text-matrix-green">
                              {t('devices.currentHint')}
                            </p>
                          )}
                        </div>
                      </div>
                      {!device.is_current && deviceId && (
                        <button
                          type="button"
                          onClick={() => revokeDeviceMutation.mutate(deviceId)}
                          disabled={isRevoking}
                          className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-neon-pink/35 bg-neon-pink/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-pink transition hover:bg-neon-pink/15 disabled:cursor-not-allowed disabled:opacity-50"
                          aria-label={t('devices.revokeDevice')}
                        >
                          <Trash2 className="h-4 w-4" aria-hidden="true" />
                          {isRevoking ? t('actions.revoking') : t('devices.revoke')}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </article>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <article className="rounded-[2rem] border border-neon-cyan/25 bg-terminal-surface/55 p-6 backdrop-blur">
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-neon-cyan">
            {t('identity.eyebrow')}
          </p>
          <h2 className="mt-3 text-2xl font-display text-white">{t('identity.title')}</h2>
          <p className="mt-3 font-mono text-sm leading-7 text-muted-foreground">
            {t('identity.description')}
          </p>

          <div className="mt-6 rounded-2xl border border-grid-line/30 bg-black/20 p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <Link2 className="mt-0.5 h-5 w-5 text-neon-cyan" aria-hidden="true" />
                <div>
                  <p className="font-mono text-sm text-white">Telegram</p>
                  <p className="mt-1 font-mono text-xs leading-6 text-muted-foreground">
                    {user?.telegram_id
                      ? t('identity.telegramLinked', { id: String(user.telegram_id) })
                      : t('identity.telegramMissing')}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => void startTelegramLink()}
                disabled={isStartingTelegramLink || authLoading}
                className="inline-flex min-h-10 items-center justify-center rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-cyan transition hover:bg-neon-cyan/15 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isStartingTelegramLink || authLoading ? t('actions.starting') : t('actions.manage')}
              </button>
            </div>
          </div>
        </article>

        <article className="rounded-[2rem] border border-grid-line/30 bg-terminal-surface/55 p-6 backdrop-blur">
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-matrix-green">
            {t('privacy.eyebrow')}
          </p>
          <h2 className="mt-3 text-2xl font-display text-white">{t('privacy.title')}</h2>
          <div className="mt-6 grid gap-3 md:grid-cols-2">
            {(['serverTruth', 'noSecretTelemetry', 'sessionRevocation', 'accountDeletion'] as const).map((item) => (
              <div key={item} className="rounded-2xl border border-grid-line/30 bg-black/20 p-4">
                <CheckCircle2 className="h-5 w-5 text-matrix-green" aria-hidden="true" />
                <p className="mt-3 font-mono text-sm text-white">{t(`privacy.items.${item}.title`)}</p>
                <p className="mt-2 font-mono text-xs leading-6 text-muted-foreground">
                  {t(`privacy.items.${item}.description`)}
                </p>
              </div>
            ))}
          </div>
        </article>
      </section>

      <TwoFactorModal
        isOpen={activeModal === 'twoFactor'}
        isEnabled={twoFactorStatus?.status === 'enabled'}
        onClose={() => setActiveModal(null)}
        onSuccess={() => {
          setActiveModal(null);
          void twoFactorQuery.refetch();
          setBanner({ tone: 'green', text: t('feedback.securityUpdated') });
        }}
      />
      <ChangePasswordModal
        isOpen={activeModal === 'password'}
        onClose={() => setActiveModal(null)}
        onSuccess={() => {
          setActiveModal(null);
          setBanner({ tone: 'green', text: t('feedback.securityUpdated') });
        }}
      />
      <AntiphishingModal
        isOpen={activeModal === 'antiphishing'}
        onClose={() => setActiveModal(null)}
        onSuccess={() => {
          setActiveModal(null);
          void antiphishingQuery.refetch();
          setBanner({ tone: 'green', text: t('feedback.securityUpdated') });
        }}
      />
    </div>
  );
}

function PreferenceToggle({
  checked,
  description,
  disabled,
  label,
  onToggle,
}: {
  checked: boolean;
  description: string;
  disabled?: boolean;
  label: string;
  onToggle: (value: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onToggle(!checked)}
      disabled={disabled}
      aria-pressed={checked}
      className="w-full rounded-2xl border border-grid-line/30 bg-black/20 p-4 text-left transition hover:border-neon-cyan/30 disabled:cursor-not-allowed disabled:opacity-60"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-sm text-white">{label}</p>
          <p className="mt-1 font-mono text-xs leading-6 text-muted-foreground">{description}</p>
        </div>
        <span
          className={`mt-1 inline-flex h-6 w-11 shrink-0 items-center rounded-full border p-1 transition ${
            checked
              ? 'border-matrix-green/40 bg-matrix-green/20'
              : 'border-grid-line/40 bg-terminal-bg'
          }`}
        >
          <span
            className={`h-4 w-4 rounded-full transition ${
              checked ? 'translate-x-5 bg-matrix-green' : 'translate-x-0 bg-muted-foreground'
            }`}
          />
        </span>
      </div>
    </button>
  );
}

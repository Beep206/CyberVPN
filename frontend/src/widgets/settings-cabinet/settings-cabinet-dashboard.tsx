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
  Pencil,
  Plus,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  Trash2,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@/i18n/navigation';
import { useAuthStore } from '@/stores/auth-store';
import {
  clearTelegramAccountLinkSession,
  saveTelegramAccountLinkSession,
} from '@/features/auth/lib/telegram-account-link-session';
import {
  authApi,
  growthNotificationsApi,
  passkeysApi,
  profileApi,
  securityApi,
  twofaApi,
  type PasskeyCredential,
} from '@/lib/api';
import { markPerformance } from '@/shared/lib/web-vitals';
import { formatCustomerPublicUid } from '@/shared/lib/public-account-id';
import { AntiphishingModal } from '@/app/[locale]/(dashboard)/settings/components/AntiphishingModal';
import { ChangePasswordModal } from '@/app/[locale]/(dashboard)/settings/components/ChangePasswordModal';
import { TwoFactorModal } from '@/app/[locale]/(dashboard)/settings/components/TwoFactorModal';
import { requestPasskeyFreshAuthGrant } from '@/features/auth/lib/passkey-fresh-auth';
import {
  completePasskeyRegistration,
  getPasskeyErrorMessageKey,
} from '@/features/auth/lib/passkey-webauthn';
import {
  buildCoreNotificationPatch,
  buildGrowthNotificationPatch,
  CORE_NOTIFICATION_PREFERENCES,
  formatDateTime,
  formatShortId,
  getDeviceKind,
  getEnabledCount,
  getSecurityPosture,
  GROWTH_NOTIFICATION_PREFERENCES,
  getProfileTimezoneOptions,
  maskAntiphishingCode,
  parseDeviceLabel,
  readDeviceListTotal,
  PROFILE_LANGUAGE_OPTIONS,
  type CoreNotificationPreferenceKey,
  type GrowthNotificationPreferenceKey,
  type ProfileUpdate,
  type StatusTone,
} from './settings-cabinet-model';

const PROFILE_STALE_MS = 5 * 60_000;
const SECURITY_STALE_MS = 45_000;
const TELEGRAM_ACCOUNT_LINK_POLL_INTERVAL_MS = 2_000;
const TELEGRAM_ACCOUNT_LINK_MAX_POLLS = 150;

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

type PasskeyRenameDraft = {
  id: string;
  label: string;
} | null;

type SettingsCabinetView = 'overview' | 'security';

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

function getPasskeyRenameAction(credentialId: string): string {
  return `passkey.credential.rename:${credentialId}`;
}

function getPasskeyRevokeAction(credentialId: string): string {
  return `passkey.credential.revoke:${credentialId}`;
}

function getHttpStatus(error: unknown): number | null {
  if (!error || typeof error !== 'object') {
    return null;
  }

  const response = (error as { response?: { status?: unknown } }).response;
  return typeof response?.status === 'number' ? response.status : null;
}

export function SettingsCabinetDashboard({
  view = 'overview',
}: {
  view?: SettingsCabinetView;
} = {}) {
  const t = useTranslations('Settings.cabinet');
  const authT = useTranslations('Auth.login');
  const locale = useLocale();
  const queryClient = useQueryClient();
  const authLoading = useAuthStore((state) => state.isLoading);
  const telegramLinkPollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const telegramLinkPollAttemptRef = useRef(0);
  const [activeModal, setActiveModal] = useState<SensitiveModal>(null);
  const [banner, setBanner] = useState<{ tone: StatusTone; text: string } | null>(null);
  const [copyState, setCopyState] = useState<'account' | 'idle'>('idle');
  const [newPasskeyLabel, setNewPasskeyLabel] = useState('');
  const [passkeyRenameDraft, setPasskeyRenameDraft] = useState<PasskeyRenameDraft>(null);
  const [isStartingTelegramLink, setIsStartingTelegramLink] = useState(false);
  const [timezoneReferenceDate] = useState(() => new Date());
  const isSecurityView = view === 'security';
  const primaryPanelLayoutClassName = isSecurityView
    ? 'grid gap-6 xl:col-span-2'
    : 'contents';

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
      const response = await authApi.customerMe();
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

  const passkeyPolicyQuery = useQuery({
    queryKey: ['settings', 'passkey-policy'],
    queryFn: async () => {
      const response = await passkeysApi.getPolicy();
      return response.data;
    },
    refetchOnWindowFocus: false,
    staleTime: SECURITY_STALE_MS,
  });

  const passkeysQuery = useQuery({
    queryKey: ['settings', 'passkeys'],
    queryFn: async () => {
      const response = await passkeysApi.list();
      return response.data;
    },
    enabled: passkeyPolicyQuery.data?.enabled === true,
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

  const profile = profileQuery.data ?? null;
  const user = userQuery.data ?? null;
  const twoFactorStatus = twoFactorQuery.data ?? null;
  const antiphishingCode = antiphishingQuery.data ?? null;
  const passkeyPolicy = passkeyPolicyQuery.data ?? null;
  const passkeyCredentials = passkeysQuery.data?.credentials ?? [];
  const activePasskeys = passkeyCredentials.filter(
    (credential) => credential.status !== 'revoked' && !credential.revokedAt,
  );
  const coreNotifications = coreNotificationsQuery.data ?? null;
  const growthNotifications = growthNotificationsQuery.data ?? null;
  const deviceList = devicesQuery.data ?? null;
  const devices = deviceList?.devices ?? [];
  const timezoneOptions = getProfileTimezoneOptions(timezoneReferenceDate);
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
  const publicAccountId = formatCustomerPublicUid(user?.public_uid ?? profile?.public_uid);
  const currentDeviceIndex = devices.findIndex((device) => device.is_current);
  const currentDevice = currentDeviceIndex >= 0 ? devices[currentDeviceIndex] : null;
  const activeDeviceCount = readDeviceListTotal(deviceList);
  const otherDeviceCount = Math.max(0, activeDeviceCount - (currentDevice ? 1 : 0));
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
    passkeyPolicyQuery.isError ||
    passkeysQuery.isError ||
    coreNotificationsQuery.isError ||
    growthNotificationsQuery.isError ||
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
      const response = await authApi.logoutOtherDevices();
      return response.data.sessions_revoked;
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

  const addPasskeyMutation = useMutation({
    mutationFn: async (label: string) => {
      const response = await completePasskeyRegistration(label);
      return response.data;
    },
    onSuccess: (credential) => {
      queryClient.setQueryData(['settings', 'passkeys'], (current?: { credentials: PasskeyCredential[] }) => ({
        credentials: [
          credential,
          ...(current?.credentials ?? []).filter((item) => item.id !== credential.id),
        ],
      }));
      setNewPasskeyLabel('');
      markPerformance('settings-passkey-add', {
        credential: formatShortId(credential.id),
      });
      setBanner({ tone: 'green', text: t('feedback.passkeyAdded') });
    },
    onError: () => {
      setBanner({ tone: 'pink', text: t('feedback.passkeyFailed') });
    },
  });

  const setPasskeyFailureBanner = (error: unknown) => {
    const messageKey = getPasskeyErrorMessageKey(error);

    if (messageKey === 'passkeyCancelled' || messageKey === 'passkeyUnsupported') {
      setBanner({ tone: 'amber', text: authT(messageKey as never) });
      return;
    }

    setBanner({ tone: 'pink', text: t('feedback.passkeyFailed') });
  };

  const renamePasskeyMutation = useMutation({
    mutationFn: async ({ credentialId, label }: { credentialId: string; label: string }) => {
      const freshAuthGrantId = await requestPasskeyFreshAuthGrant(
        getPasskeyRenameAction(credentialId),
      );
      const response = await passkeysApi.rename(credentialId, label, {
        freshAuthGrantId,
      });
      return response.data;
    },
    onSuccess: (credential) => {
      queryClient.setQueryData(['settings', 'passkeys'], (current?: { credentials: PasskeyCredential[] }) => ({
        credentials: (current?.credentials ?? []).map((item) =>
          item.id === credential.id ? credential : item,
        ),
      }));
      setPasskeyRenameDraft(null);
      markPerformance('settings-passkey-rename', {
        credential: formatShortId(credential.id),
      });
      setBanner({ tone: 'green', text: t('feedback.passkeyRenamed') });
    },
    onError: (error) => {
      setPasskeyFailureBanner(error);
    },
  });

  const deletePasskeyMutation = useMutation({
    mutationFn: async (credentialId: string) => {
      const freshAuthGrantId = await requestPasskeyFreshAuthGrant(
        getPasskeyRevokeAction(credentialId),
      );
      const response = await passkeysApi.delete(credentialId, {
        freshAuthGrantId,
      });
      return response.data;
    },
    onSuccess: (result) => {
      queryClient.setQueryData(['settings', 'passkeys'], (current?: { credentials: PasskeyCredential[] }) => ({
        credentials: (current?.credentials ?? []).filter((item) => item.id !== result.id),
      }));
      markPerformance('settings-passkey-delete', {
        credential: formatShortId(result.id),
      });
      setBanner({ tone: 'green', text: t('feedback.passkeyDeleted') });
    },
    onError: (error) => {
      setPasskeyFailureBanner(error);
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
      passkeyPolicyQuery.refetch(),
      ...(passkeyPolicy?.enabled ? [passkeysQuery.refetch()] : []),
      coreNotificationsQuery.refetch(),
      growthNotificationsQuery.refetch(),
      devicesQuery.refetch(),
    ]);

  const clearTelegramLinkPoll = useCallback(() => {
    if (telegramLinkPollTimeoutRef.current) {
      clearTimeout(telegramLinkPollTimeoutRef.current);
      telegramLinkPollTimeoutRef.current = null;
    }
  }, []);

  useEffect(() => clearTelegramLinkPoll, [clearTelegramLinkPoll]);

  const failTelegramAccountLink = useCallback(() => {
    clearTelegramLinkPoll();
    clearTelegramAccountLinkSession();
    setIsStartingTelegramLink(false);
    setBanner({ tone: 'pink', text: t('feedback.telegramLinkFailed') });
  }, [clearTelegramLinkPoll, t]);

  const pollTelegramAccountLink = useCallback(
    (token: string, originalUserId: string | null) => {
      clearTelegramLinkPoll();

      const poll = async () => {
        telegramLinkPollAttemptRef.current += 1;
        if (telegramLinkPollAttemptRef.current > TELEGRAM_ACCOUNT_LINK_MAX_POLLS) {
          failTelegramAccountLink();
          return;
        }

        try {
          const response = await authApi.pollTelegramAccountLinkStatus(token);
          const status = response.data.status;

          if (status === 'pending') {
            telegramLinkPollTimeoutRef.current = setTimeout(
              () => {
                void poll();
              },
              TELEGRAM_ACCOUNT_LINK_POLL_INTERVAL_MS,
            );
            return;
          }

          if (status === 'linked') {
            clearTelegramLinkPoll();
            clearTelegramAccountLinkSession();
            await queryClient.invalidateQueries({ queryKey: ['settings', 'auth-user'] });
            const refreshedUser = await userQuery.refetch();
            if (originalUserId && refreshedUser.data?.id !== originalUserId) {
              setBanner({ tone: 'pink', text: t('feedback.telegramLinkFailed') });
            } else {
              setBanner({ tone: 'green', text: t('feedback.securityUpdated') });
            }
            setIsStartingTelegramLink(false);
            return;
          }

          failTelegramAccountLink();
        } catch (error) {
          if (getHttpStatus(error) === 409) {
            failTelegramAccountLink();
            return;
          }

          failTelegramAccountLink();
        }
      };

      void poll();
    },
    [
      clearTelegramLinkPoll,
      failTelegramAccountLink,
      queryClient,
      t,
      userQuery,
    ],
  );

  const copyAccountId = async () => {
    const clipboard = typeof navigator === 'undefined' ? undefined : navigator.clipboard;
    if (!publicAccountId || typeof clipboard?.writeText !== 'function') {
      return;
    }

    try {
      await clipboard.writeText(publicAccountId);
      markPerformance('settings-account-id-copy');
      setCopyState('account');
      window.setTimeout(() => setCopyState('idle'), 1600);
    } catch {
      setBanner({ tone: 'pink', text: t('feedback.copyFailed') });
    }
  };

  const startTelegramLink = async () => {
    if (isStartingTelegramLink) {
      return;
    }

    setIsStartingTelegramLink(true);
    try {
      const originalUserId = user?.id ?? null;
      const response = await authApi.requestTelegramAccountLink();
      const session = {
        token: response.data.token,
        botUrl: response.data.bot_url,
        deepLinkUrl: response.data.deep_link_url ?? undefined,
        requestedAt: Date.now(),
      };
      saveTelegramAccountLinkSession(session);
      telegramLinkPollAttemptRef.current = 0;

      if (typeof window !== 'undefined') {
        window.open(session.deepLinkUrl ?? session.botUrl, '_blank', 'noopener,noreferrer');
      }

      pollTelegramAccountLink(session.token, originalUserId);
    } catch {
      failTelegramAccountLink();
    }
  };

  const startPasskeyRename = (credential: PasskeyCredential) => {
    setPasskeyRenameDraft({
      id: credential.id,
      label: credential.label,
    });
  };

  const submitPasskeyRename = () => {
    if (!passkeyRenameDraft?.id) {
      return;
    }

    const label = passkeyRenameDraft.label.trim();
    if (!label) {
      setBanner({ tone: 'amber', text: t('security.passkeys.renameRequired') });
      return;
    }

    renamePasskeyMutation.mutate({
      credentialId: passkeyRenameDraft.id,
      label,
    });
  };

  const requestPasskeyDelete = (credential: PasskeyCredential) => {
    if (activePasskeys.length <= 1 && twoFactorStatus?.status !== 'enabled') {
      setBanner({ tone: 'amber', text: t('security.passkeys.lastRecoveryWarning') });
      return;
    }

    deletePasskeyMutation.mutate(credential.id);
  };

  return (
    <div className="grid gap-8 xl:grid-cols-2">
      <section className="relative overflow-hidden rounded-[2rem] border border-neon-cyan/25 bg-terminal-surface/55 p-6 shadow-[0_0_70px_rgba(0,255,255,0.08)] backdrop-blur md:p-8 xl:col-span-2">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(0,255,255,0.18),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(255,0,255,0.13),transparent_32%)]" />
        <div className="relative grid gap-6 xl:grid-cols-[1.1fr_0.9fr] xl:items-end">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.34em] text-neon-cyan">
              {isSecurityView ? t('security.eyebrow') : t('hero.eyebrow')}
            </p>
            <h1 className="mt-4 max-w-4xl text-4xl font-display tracking-[0.08em] text-white md:text-5xl">
              {isSecurityView ? t('security.title') : t('title')}
            </h1>
            <p className="mt-4 max-w-3xl font-mono text-sm leading-7 text-muted-foreground">
              {isSecurityView ? t('security.description') : t('subtitle')}
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
              {isSecurityView ? (
                <Link
                  href="/settings"
                  className="inline-flex min-h-11 items-center justify-center rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-cyan transition hover:bg-neon-cyan/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
                >
                  {t('actions.profileSettings')}
                </Link>
              ) : (
                <Link
                  href="/settings/security"
                  className="inline-flex min-h-11 items-center justify-center rounded-xl border border-matrix-green/35 bg-matrix-green/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-matrix-green transition hover:bg-matrix-green/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-matrix-green focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
                >
                  {t('actions.openSecurity')}
                </Link>
              )}
              <Link
                href="/settings/delete-account"
                className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-pink/35 bg-neon-pink/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-pink transition hover:bg-neon-pink/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
                {t('actions.deleteAccount')}
              </Link>
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
          className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-4 font-mono text-sm text-amber-200 xl:col-span-2"
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
          className={`rounded-2xl border p-4 font-mono text-sm xl:col-span-2 ${toneClasses[banner.tone].border} ${toneClasses[banner.tone].fill} ${toneClasses[banner.tone].text}`}
          role="status"
        >
          {banner.text}
        </section>
      )}

      {isSecurityView && (
        <section className="grid gap-4 md:grid-cols-4 xl:col-span-2" aria-label={t('summary.ariaLabel')}>
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
            tone="cyan"
            value={String(activeDeviceCount)}
          />
        </section>
      )}

      <section className={primaryPanelLayoutClassName}>
        {!isSecurityView && (
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
                  <p className="mt-1 break-all font-mono text-sm text-white">
                    {publicAccountId ?? t('labels.notAvailable')}
                  </p>
                  <p className="mt-1 font-mono text-xs text-muted-foreground">
                    {t('profile.updatedAt', {
                      date: formatDateTime(profile?.updated_at, locale),
                    })}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void copyAccountId()}
                  disabled={!publicAccountId}
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
        )}

        {isSecurityView && (
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

          <div className="mt-5 rounded-2xl border border-matrix-green/25 bg-black/20 p-4">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <p className="font-mono text-sm text-white">{t('security.passkeys.title')}</p>
                <p className="mt-1 font-mono text-xs leading-6 text-muted-foreground">
                  {t('security.passkeys.description')}
                </p>
                <p className="mt-2 font-mono text-xs leading-6 text-muted-foreground">
                  {t('security.passkeys.privacyNote')}
                </p>
              </div>
              <StatusPill
                tone={
                  passkeyPolicyQuery.isPending
                    ? 'muted'
                    : passkeyPolicy?.enabled
                      ? 'green'
                      : 'amber'
                }
              >
                {passkeyPolicyQuery.isPending
                  ? t('labels.loading')
                  : passkeyPolicy?.enabled
                    ? t('labels.enabled')
                    : t('labels.disabled')}
              </StatusPill>
            </div>

            {passkeyPolicyQuery.isPending ? (
              <div className="mt-4">
                <LoadingCard className="min-h-28" />
              </div>
            ) : !passkeyPolicy?.enabled ? (
              <p className="mt-4 rounded-xl border border-grid-line/30 bg-terminal-bg/50 p-3 font-mono text-xs leading-6 text-muted-foreground">
                {t('security.passkeys.disabled')}
              </p>
            ) : (
              <>
                <div className="mt-4 grid gap-3 md:grid-cols-[1fr_auto]">
                  <label className="space-y-2">
                    <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                      {t('security.passkeys.label')}
                    </span>
                    <input
                      value={newPasskeyLabel}
                      maxLength={120}
                      onChange={(event) => setNewPasskeyLabel(event.target.value)}
                      placeholder={t('security.passkeys.labelPlaceholder')}
                      className="h-11 w-full rounded-xl border border-matrix-green/30 bg-terminal-bg/70 px-4 font-mono text-sm text-white outline-hidden transition focus:border-matrix-green focus:ring-2 focus:ring-matrix-green/30"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => addPasskeyMutation.mutate(newPasskeyLabel)}
                    disabled={
                      addPasskeyMutation.isPending ||
                      passkeyPolicy.registrationEnabled === false
                    }
                    className="inline-flex min-h-11 items-center justify-center gap-2 self-end rounded-xl border border-matrix-green/40 bg-matrix-green/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-matrix-green transition hover:bg-matrix-green/15 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {addPasskeyMutation.isPending ? (
                      <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <Plus className="h-4 w-4" aria-hidden="true" />
                    )}
                    {addPasskeyMutation.isPending
                      ? t('security.passkeys.adding')
                      : t('security.passkeys.addAction')}
                  </button>
                </div>

                {passkeysQuery.isPending ? (
                  <div className="mt-4 space-y-3">
                    <LoadingCard className="min-h-20" />
                    <LoadingCard className="min-h-20" />
                  </div>
                ) : passkeyCredentials.length === 0 ? (
                  <div className="mt-4 rounded-2xl border border-grid-line/30 bg-terminal-bg/50 p-5 text-center">
                    <KeyRound className="mx-auto h-8 w-8 text-muted-foreground/60" aria-hidden="true" />
                    <p className="mt-3 font-mono text-sm text-muted-foreground">
                      {t('security.passkeys.empty')}
                    </p>
                  </div>
                ) : (
                  <div className="mt-4 space-y-3">
                    {passkeyCredentials.map((credential) => {
                      const isEditing = passkeyRenameDraft?.id === credential.id;
                      const isDeleting =
                        deletePasskeyMutation.isPending &&
                        deletePasskeyMutation.variables === credential.id;
                      const isRenaming =
                        renamePasskeyMutation.isPending &&
                        renamePasskeyMutation.variables?.credentialId === credential.id;
                      const credentialTone: StatusTone = credential.revokedAt || credential.status === 'revoked'
                        ? 'pink'
                        : credential.backedUp
                          ? 'green'
                          : 'cyan';

                      return (
                        <div
                          key={credential.id}
                          className="rounded-2xl border border-grid-line/30 bg-terminal-bg/50 p-4"
                        >
                          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                            <div className="min-w-0 flex-1">
                              {isEditing ? (
                                <label className="block space-y-2">
                                  <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                                    {t('security.passkeys.renameLabel')}
                                  </span>
                                  <input
                                    value={passkeyRenameDraft.label}
                                    maxLength={120}
                                    onChange={(event) =>
                                      setPasskeyRenameDraft({
                                        id: credential.id,
                                        label: event.target.value,
                                      })
                                    }
                                    className="h-11 w-full rounded-xl border border-neon-cyan/30 bg-black/30 px-4 font-mono text-sm text-white outline-hidden transition focus:border-neon-cyan focus:ring-2 focus:ring-neon-cyan/30"
                                  />
                                </label>
                              ) : (
                                <>
                                  <div className="flex flex-wrap items-center gap-2">
                                    <p className="truncate font-mono text-sm text-white">
                                      {credential.label}
                                    </p>
                                    <StatusPill tone={credentialTone}>
                                      {credential.backedUp
                                        ? t('security.passkeys.synced')
                                        : credential.credentialType || t('labels.notAvailable')}
                                    </StatusPill>
                                  </div>
                                  <p className="mt-2 font-mono text-xs leading-6 text-muted-foreground">
                                    {t('security.passkeys.metadata', {
                                      created: formatDateTime(credential.createdAt, locale),
                                      id: formatShortId(credential.id),
                                      lastUsed: credential.lastUsedAt
                                        ? formatDateTime(credential.lastUsedAt, locale)
                                        : t('security.passkeys.neverUsed'),
                                    })}
                                  </p>
                                </>
                              )}
                            </div>

                            <div className="flex flex-wrap gap-2">
                              {isEditing ? (
                                <>
                                  <button
                                    type="button"
                                    onClick={submitPasskeyRename}
                                    disabled={isRenaming}
                                    className="inline-flex min-h-10 items-center justify-center rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-cyan transition hover:bg-neon-cyan/15 disabled:cursor-not-allowed disabled:opacity-50"
                                  >
                                    {isRenaming
                                      ? t('security.passkeys.saving')
                                      : t('security.passkeys.saveRename')}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => setPasskeyRenameDraft(null)}
                                    disabled={isRenaming}
                                    className="inline-flex min-h-10 items-center justify-center rounded-xl border border-grid-line/35 bg-black/20 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-muted-foreground transition hover:border-grid-line/60 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                                  >
                                    {t('security.passkeys.cancelRename')}
                                  </button>
                                </>
                              ) : (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => startPasskeyRename(credential)}
                                    className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-neon-cyan/35 bg-neon-cyan/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-cyan transition hover:bg-neon-cyan/15"
                                  >
                                    <Pencil className="h-4 w-4" aria-hidden="true" />
                                    {t('security.passkeys.renameAction')}
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => requestPasskeyDelete(credential)}
                                    disabled={isDeleting}
                                    className="inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border border-neon-pink/35 bg-neon-pink/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-neon-pink transition hover:bg-neon-pink/15 disabled:cursor-not-allowed disabled:opacity-50"
                                  >
                                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                                    {isDeleting
                                      ? t('security.passkeys.deleting')
                                      : t('security.passkeys.deleteAction')}
                                  </button>
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}
          </div>

          <div className="mt-5 rounded-2xl border border-amber-400/25 bg-amber-400/10 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-300" aria-hidden="true" />
              <div>
                <p className="font-mono text-sm text-white">{t('security.recovery.title')}</p>
                <p className="mt-1 font-mono text-xs leading-6 text-muted-foreground">
                  {t('security.recovery.description')}
                </p>
                <Link
                  href="/support"
                  className="mt-3 inline-flex min-h-10 items-center rounded-xl border border-amber-400/35 bg-amber-400/10 px-3 py-2 font-mono text-xs uppercase tracking-[0.14em] text-amber-200 transition hover:bg-amber-400/15"
                >
                  {t('security.recovery.cta')}
                </Link>
              </div>
            </div>
          </div>
        </article>
        )}
      </section>

      <section className={primaryPanelLayoutClassName}>
        {!isSecurityView && (
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
        )}

        {isSecurityView && (
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
              disabled={otherDeviceCount === 0 || revokeOtherDevicesMutation.isPending}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-pink/35 bg-neon-pink/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-pink transition hover:bg-neon-pink/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
              {t('devices.revokeOthers')}
            </button>
          </div>

          <div className="mt-6 rounded-3xl border border-grid-line/30 bg-black/20 p-5">
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  {t('devices.activeCount')}
                </p>
                <p className="mt-2 font-mono text-xl text-white">{activeDeviceCount}</p>
              </div>
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  {t('devices.current')}
                </p>
                <p className="mt-2 min-w-0 truncate font-mono text-xl text-white">
                  {currentDevice ? parseDeviceLabel(currentDevice.user_agent) : t('labels.notAvailable')}
                </p>
              </div>
              <div>
                <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                  {t('devices.otherSessions')}
                </p>
                <p className="mt-2 font-mono text-xl text-white">{otherDeviceCount}</p>
              </div>
            </div>
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
              {devices.map((device, index) => {
                const deviceId = device.device_id ?? '';
                const isCurrentDevice = index === currentDeviceIndex;
                const deviceKind = getDeviceKind(device.user_agent);
                const Icon = getDeviceIcon(deviceKind);
                const isRevoking =
                  revokeDeviceMutation.isPending && revokeDeviceMutation.variables === deviceId;

                return (
                  <div
                    key={deviceId || `${device.user_agent ?? 'unknown'}-${device.last_used_at}-${index}`}
                    className={`rounded-2xl border p-4 ${isCurrentDevice ? 'border-matrix-green/35 bg-matrix-green/5' : 'border-grid-line/30 bg-black/20'}`}
                  >
                    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                      <div className="flex items-start gap-3">
                        <div className={isCurrentDevice ? 'text-matrix-green' : 'text-neon-cyan'}>
                          <Icon className="h-5 w-5" aria-hidden="true" />
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="font-mono text-sm text-white">
                              {parseDeviceLabel(device.user_agent)}
                            </p>
                            {isCurrentDevice && (
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
                          {currentDevice?.device_id === deviceId && isCurrentDevice && (
                            <p className="mt-1 font-mono text-xs text-matrix-green">
                              {t('devices.currentHint')}
                            </p>
                          )}
                        </div>
                      </div>
                      {!isCurrentDevice && deviceId && (
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
        )}
      </section>

      {!isSecurityView && (
      <section className="grid gap-6 xl:col-span-2 xl:grid-cols-[0.95fr_1.05fr]">
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
          <Link
            href="/settings/delete-account"
            className="mt-5 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl border border-neon-pink/35 bg-neon-pink/10 px-4 py-2 font-mono text-xs uppercase tracking-[0.16em] text-neon-pink transition hover:bg-neon-pink/15 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-pink focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            {t('actions.deleteAccount')}
          </Link>
        </article>
      </section>
      )}

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
      role="switch"
      aria-checked={checked}
      className="w-full rounded-2xl border border-grid-line/30 bg-black/20 p-4 text-left transition hover:border-neon-cyan/30 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-bg disabled:cursor-not-allowed disabled:opacity-60"
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
              : 'border-grid-line/70 bg-black/40'
          }`}
        >
          <span
            className={`h-4 w-4 rounded-full shadow-sm transition ${
              checked
                ? 'translate-x-5 bg-matrix-green shadow-[0_0_10px_rgba(0,255,136,0.45)]'
                : 'translate-x-0 bg-white shadow-[0_0_0_1px_rgba(148,163,184,0.55)]'
            }`}
          />
        </span>
      </div>
    </button>
  );
}

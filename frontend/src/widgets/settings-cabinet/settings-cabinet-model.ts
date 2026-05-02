import type { components } from '@/lib/api/generated/types';
import type {
  GrowthNotificationPreferences,
  UpdateGrowthNotificationPreferencesRequest,
} from '@/lib/api/growth-notifications';

export type Profile = components['schemas']['ProfileResponse'];
export type ProfileUpdate = components['schemas']['ProfileUpdateRequest'];
export type CoreNotificationPreferences = components['schemas']['NotificationPreferencesResponse'];
export type CoreNotificationPreferenceUpdate =
  components['schemas']['NotificationPreferencesUpdateRequest'];
export type TwoFactorStatus = components['schemas']['TwoFactorStatusResponse'];
export type AntiphishingCode = components['schemas']['AntiPhishingCodeResponse'];
export type DeviceSession =
  components['schemas']['src__presentation__api__v1__auth__schemas__DeviceSessionResponse'];

export type CoreNotificationPreferenceKey = keyof CoreNotificationPreferences;
export type GrowthNotificationPreferenceKey = keyof GrowthNotificationPreferences;
export type StatusTone = 'amber' | 'cyan' | 'green' | 'muted' | 'pink' | 'purple';

export type PreferenceDescriptor<T extends string> = {
  key: T;
  titleKey: string;
  descriptionKey: string;
};

export const CORE_NOTIFICATION_PREFERENCES: Array<
  PreferenceDescriptor<CoreNotificationPreferenceKey>
> = [
  {
    descriptionKey: 'notifications.core.emailSecurity.description',
    key: 'email_security',
    titleKey: 'notifications.core.emailSecurity.title',
  },
  {
    descriptionKey: 'notifications.core.emailMarketing.description',
    key: 'email_marketing',
    titleKey: 'notifications.core.emailMarketing.title',
  },
  {
    descriptionKey: 'notifications.core.pushConnection.description',
    key: 'push_connection',
    titleKey: 'notifications.core.pushConnection.title',
  },
  {
    descriptionKey: 'notifications.core.pushPayment.description',
    key: 'push_payment',
    titleKey: 'notifications.core.pushPayment.title',
  },
  {
    descriptionKey: 'notifications.core.pushSubscription.description',
    key: 'push_subscription',
    titleKey: 'notifications.core.pushSubscription.title',
  },
];

export const GROWTH_NOTIFICATION_PREFERENCES: Array<
  PreferenceDescriptor<GrowthNotificationPreferenceKey>
> = [
  {
    descriptionKey: 'notifications.growth.inAppInvites.description',
    key: 'growth_in_app_invites',
    titleKey: 'notifications.growth.inAppInvites.title',
  },
  {
    descriptionKey: 'notifications.growth.emailRewards.description',
    key: 'growth_email_referral_rewards',
    titleKey: 'notifications.growth.emailRewards.title',
  },
  {
    descriptionKey: 'notifications.growth.telegramRewards.description',
    key: 'growth_telegram_referral_rewards',
    titleKey: 'notifications.growth.telegramRewards.title',
  },
  {
    descriptionKey: 'notifications.growth.emailGifts.description',
    key: 'growth_email_gifts',
    titleKey: 'notifications.growth.emailGifts.title',
  },
  {
    descriptionKey: 'notifications.growth.adminUpdates.description',
    key: 'growth_telegram_admin_updates',
    titleKey: 'notifications.growth.adminUpdates.title',
  },
];

const MOBILE_PATTERNS = ['android', 'iphone', 'mobile'];
const TABLET_PATTERNS = ['ipad', 'tablet'];

export function formatDateTime(value: string | null | undefined, locale = 'en-EN'): string {
  if (!value) {
    return 'n/a';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return 'n/a';
  }

  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  } catch {
    return date.toISOString();
  }
}

export function formatShortId(value: string | null | undefined): string {
  const normalized = value?.trim();
  if (!normalized) {
    return 'n/a';
  }

  return normalized.length <= 12 ? normalized : `${normalized.slice(0, 8)}...`;
}

export function maskAntiphishingCode(code: string | null | undefined): string {
  const normalized = code?.trim();
  if (!normalized) {
    return 'not-set';
  }

  if (normalized.length <= 4) {
    return '*'.repeat(normalized.length);
  }

  return `${normalized.slice(0, 2)}${'*'.repeat(Math.max(4, normalized.length - 4))}${normalized.slice(-2)}`;
}

export function getDeviceKind(userAgent: string | null | undefined): 'desktop' | 'mobile' | 'tablet' {
  const normalized = userAgent?.toLowerCase() ?? '';

  if (TABLET_PATTERNS.some((pattern) => normalized.includes(pattern))) {
    return 'tablet';
  }

  if (MOBILE_PATTERNS.some((pattern) => normalized.includes(pattern))) {
    return 'mobile';
  }

  return 'desktop';
}

export function parseDeviceLabel(userAgent: string | null | undefined): string {
  const normalized = userAgent?.trim();
  if (!normalized) {
    return 'Unknown device';
  }

  const browser =
    normalized.match(/(Edg|Edge|Firefox|Chrome|CriOS|Safari)\/[\d.]+/)?.[1] ?? 'Browser';
  const os =
    normalized.match(/Windows NT [\d.]+/)?.[0] ??
    normalized.match(/Mac OS X [\d_]+/)?.[0]?.replaceAll('_', '.') ??
    normalized.match(/Android [\d.]+/)?.[0] ??
    normalized.match(/iPhone OS [\d_]+/)?.[0]?.replaceAll('_', '.') ??
    normalized.match(/CPU OS [\d_]+/)?.[0]?.replaceAll('_', '.') ??
    normalized.match(/Linux/)?.[0] ??
    'Unknown OS';

  return `${browser} / ${os}`.replace('Edg', 'Edge').replace('CriOS', 'Chrome');
}

export function getEnabledCount(preferences: object | null | undefined): number {
  if (!preferences) {
    return 0;
  }

  return Object.values(preferences).filter((value) => value === true).length;
}

export function getSecurityPosture({
  antiPhishingCode,
  devices,
  notificationPreferences,
  twoFactorStatus,
}: {
  antiPhishingCode?: AntiphishingCode | null;
  devices?: Array<{ is_current: boolean }> | null;
  notificationPreferences?: CoreNotificationPreferences | null;
  twoFactorStatus?: TwoFactorStatus | null;
}) {
  const signals = [
    twoFactorStatus?.status === 'enabled',
    Boolean(antiPhishingCode?.code),
    Boolean(notificationPreferences?.email_security),
    (devices ?? []).filter((device) => !device.is_current).length <= 2,
  ];
  const passed = signals.filter(Boolean).length;
  const score = Math.round((passed / signals.length) * 100);

  if (score >= 80) {
    return { score, state: 'hardened' as const, tone: 'green' as StatusTone };
  }

  if (score >= 50) {
    return { score, state: 'attention' as const, tone: 'amber' as StatusTone };
  }

  return { score, state: 'exposed' as const, tone: 'pink' as StatusTone };
}

export function buildCoreNotificationPatch(
  key: CoreNotificationPreferenceKey,
  value: boolean,
): CoreNotificationPreferenceUpdate {
  return { [key]: value };
}

export function buildGrowthNotificationPatch(
  key: GrowthNotificationPreferenceKey,
  value: boolean,
): UpdateGrowthNotificationPreferencesRequest {
  return { [key]: value };
}

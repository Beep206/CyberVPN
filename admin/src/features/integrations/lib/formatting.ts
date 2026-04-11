import type {
  NotificationPreferencesResponse,
  TelegramBotUserResponse,
} from '@/lib/api/integrations';

export function humanizeToken(value: string | null | undefined) {
  if (!value) return 'Unknown';

  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function formatCompactNumber(value: number | null | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--';
  }

  return new Intl.NumberFormat('en', {
    notation: 'compact',
    maximumFractionDigits: value >= 100 ? 0 : 1,
  }).format(value);
}

export function formatBytes(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--';
  }

  if (value === 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let current = value;
  let unitIndex = 0;

  while (current >= 1024 && unitIndex < units.length - 1) {
    current /= 1024;
    unitIndex += 1;
  }

  const precision = current >= 100 ? 0 : current >= 10 ? 1 : 2;
  return `${current.toFixed(precision)} ${units[unitIndex]}`;
}

export function formatDateTime(
  value: string | null | undefined,
  locale = 'en-EN',
) {
  if (!value) return '--';

  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function stringifyJson(value: unknown) {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function countEnabledChannels(
  prefs: NotificationPreferencesResponse | undefined,
) {
  if (!prefs) return 0;

  return [
    prefs.email_security,
    prefs.email_marketing,
    prefs.push_connection,
    prefs.push_payment,
    prefs.push_subscription,
  ].filter(Boolean).length;
}

export function getErrorMessage(error: unknown) {
  if (
    error
    && typeof error === 'object'
    && 'response' in error
    && error.response
    && typeof error.response === 'object'
    && 'data' in error.response
  ) {
    const responseData = error.response.data;
    if (
      responseData
      && typeof responseData === 'object'
      && 'detail' in responseData
      && typeof responseData.detail === 'string'
    ) {
      return responseData.detail;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Unknown error';
}

export function statusTone(
  status: string | null | undefined,
): 'neutral' | 'success' | 'info' | 'warning' | 'danger' {
  if (!status) return 'neutral';

  const normalized = status.toLowerCase();

  if (
    normalized === 'active'
    || normalized === 'open'
    || normalized === 'healthy'
    || normalized === 'connected'
    || normalized === 'eligible'
    || normalized === 'valid'
  ) {
    return 'success';
  }

  if (
    normalized === 'pending'
    || normalized === 'none'
    || normalized === 'idle'
  ) {
    return 'warning';
  }

  if (
    normalized === 'unhealthy'
    || normalized === 'offline'
    || normalized === 'error'
    || normalized === 'closed'
    || normalized === 'invalid'
  ) {
    return 'danger';
  }

  return 'info';
}

export function socketStateTone(
  state: 'idle' | 'connecting' | 'open' | 'closed' | 'error',
) {
  if (state === 'open') return 'success' as const;
  if (state === 'connecting') return 'warning' as const;
  if (state === 'error') return 'danger' as const;
  if (state === 'closed') return 'neutral' as const;
  return 'info' as const;
}

export function summarizeBotUser(
  user: TelegramBotUserResponse | undefined,
) {
  if (!user) return '--';

  return user.username ?? user.first_name ?? user.uuid;
}

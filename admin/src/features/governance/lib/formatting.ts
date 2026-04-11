import { AxiosError } from 'axios';
import { RateLimitError } from '@/lib/api/client';
import {
  ADMIN_PERMISSION_MATRIX,
  type AdminRole,
} from '@/shared/lib/admin-rbac';

const GOVERNANCE_ROLE_ORDER: readonly AdminRole[] = [
  'super_admin',
  'admin',
  'operator',
  'support',
  'viewer',
];

export const GOVERNANCE_ROLE_PERMISSION_MATRIX = GOVERNANCE_ROLE_ORDER.map(
  (role) => ({
    role,
    permissions: [...ADMIN_PERMISSION_MATRIX[role]],
  }),
);

export function formatDateTime(
  value: string | null | undefined,
  locale = 'ru-RU',
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

export function humanizeToken(value: string | null | undefined) {
  if (!value) return 'Unknown';

  return value
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function shortId(value: string | null | undefined, size = 8) {
  if (!value) return '--';
  if (value.length <= size) return value;
  return value.slice(0, size);
}

export function stringifyJson(value: unknown) {
  if (value === undefined) return '--';
  if (value === null) return 'null';
  if (typeof value === 'string') return value;

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function summarizeJsonValue(value: unknown, maxLength = 72) {
  const summary = stringifyJson(value).replace(/\s+/g, ' ').trim();
  if (summary.length <= maxLength) {
    return summary;
  }

  return `${summary.slice(0, Math.max(0, maxLength - 1))}…`;
}

export function getErrorMessage(error: unknown, fallback: string) {
  if (error instanceof RateLimitError) {
    return error.message;
  }

  if (error instanceof AxiosError) {
    const detail =
      (error.response?.data as { detail?: string } | undefined)?.detail;
    return detail || fallback;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}

export function matchesSearch(fields: unknown[], search: string) {
  const normalizedSearch = search.trim().toLowerCase();
  if (!normalizedSearch) {
    return true;
  }

  return fields.some((field) =>
    stringifyJson(field).toLowerCase().includes(normalizedSearch),
  );
}

export function formatTtl(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined || seconds < 0) return '--';
  if (seconds < 60) return `${seconds}s`;

  const days = Math.floor(seconds / 86_400);
  const hours = Math.floor((seconds % 86_400) / 3_600);
  const minutes = Math.floor((seconds % 3_600) / 60);

  const parts = [
    days ? `${days}d` : null,
    hours ? `${hours}h` : null,
    minutes ? `${minutes}m` : null,
  ].filter(Boolean);

  return parts.slice(0, 2).join(' ') || '0m';
}

export function toneForWebhookState(entry: {
  is_valid?: boolean | null;
  processed_at?: string | null;
}) {
  if (entry.is_valid === false) return 'danger' as const;
  if (entry.processed_at) return 'success' as const;
  return 'warning' as const;
}

export function toneForInviteRole(role: string) {
  if (role === 'super_admin') return 'danger' as const;
  if (role === 'admin') return 'warning' as const;
  if (role === 'operator' || role === 'support') return 'info' as const;
  return 'neutral' as const;
}

export function settingFamily(key: string) {
  return key.split(/[._-]/)[0] ?? key;
}

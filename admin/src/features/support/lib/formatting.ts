import { AxiosError } from 'axios';
import { RateLimitError } from '@/lib/api/client';
import type {
  SupportMessageVisibility,
  SupportTicketPriority,
  SupportTicketStatus,
} from '@/lib/api/support';

export function formatSupportDateTime(
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

export function humanizeSupportToken(value: string | null | undefined) {
  if (!value) {
    return '--';
  }

  return value
    .split(/[_-]+/g)
    .filter(Boolean)
    .map((chunk) => `${chunk.slice(0, 1).toUpperCase()}${chunk.slice(1)}`)
    .join(' ');
}

export function shortSupportId(value: string | null | undefined, size = 8) {
  if (!value) return '--';
  if (value.length <= size) return value;
  return value.slice(0, size);
}

export function supportStatusTone(status: SupportTicketStatus) {
  if (status === 'resolved') return 'success' as const;
  if (status === 'closed') return 'neutral' as const;
  if (status === 'pending_support') return 'danger' as const;
  if (status === 'pending_customer') return 'warning' as const;
  return 'info' as const;
}

export function supportPriorityTone(priority: SupportTicketPriority) {
  if (priority === 'urgent') return 'danger' as const;
  if (priority === 'high') return 'warning' as const;
  if (priority === 'normal') return 'info' as const;
  return 'neutral' as const;
}

export function supportVisibilityTone(visibility: SupportMessageVisibility) {
  return visibility === 'internal' ? 'warning' : 'info';
}

export function getSupportErrorMessage(error: unknown, fallback: string) {
  if (error instanceof RateLimitError) {
    return error.message;
  }

  if (error instanceof AxiosError) {
    const data = error.response?.data as
      | { detail?: string; message?: string }
      | undefined;
    return data?.detail || data?.message || fallback;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}

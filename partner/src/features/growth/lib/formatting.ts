import { AxiosError } from 'axios';
import { RateLimitError } from '@/lib/api/client';

export function formatCurrencyAmount(
  amount: number | undefined,
  currency = 'USD',
  locale = 'ru-RU',
) {
  if (typeof amount !== 'number' || Number.isNaN(amount)) {
    return '--';
  }

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatCompactNumber(
  value: number | undefined,
  locale = 'ru-RU',
) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--';
  }

  return new Intl.NumberFormat(locale, {
    notation: 'compact',
    maximumFractionDigits: value >= 1000 ? 1 : 0,
  }).format(value);
}

export function formatDateTime(
  value: string | null | undefined,
  locale = 'ru-RU',
) {
  if (!value) {
    return '--';
  }

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
  if (!value) {
    return 'Unknown';
  }

  return value
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function shortId(value: string | null | undefined, size = 8) {
  if (!value) {
    return '--';
  }

  return value.slice(0, size);
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

export function toIsoDateTime(value: string) {
  if (!value) {
    return undefined;
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return undefined;
  }

  return parsed.toISOString();
}

export function toLocalDateTimeInputValue(value: string | null | undefined) {
  if (!value) {
    return '';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return '';
  }

  const timezoneOffset = parsed.getTimezoneOffset();
  const localTime = new Date(parsed.getTime() - timezoneOffset * 60_000);
  return localTime.toISOString().slice(0, 16);
}

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

function formatLocation(value: unknown): string {
  if (Array.isArray(value)) {
    return value.map(String).join('.');
  }

  return typeof value === 'string' ? value : '';
}

function stringifyApiDetail(value: unknown): string | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }

  if (typeof value === 'string') {
    return value.trim() || null;
  }

  if (Array.isArray(value)) {
    const messages = value
      .map((item) => stringifyApiDetail(item))
      .filter((item): item is string => Boolean(item));

    return messages.length > 0 ? messages.join('; ') : null;
  }

  if (typeof value === 'object') {
    const record = value as {
      loc?: unknown;
      msg?: unknown;
      message?: unknown;
      detail?: unknown;
      error?: unknown;
      code?: unknown;
      type?: unknown;
    };

    const nested =
      stringifyApiDetail(record.detail)
      ?? stringifyApiDetail(record.message)
      ?? stringifyApiDetail(record.error)
      ?? stringifyApiDetail(record.msg);

    if (nested) {
      const location = formatLocation(record.loc);
      return location ? `${location}: ${nested}` : nested;
    }

    if (typeof record.code === 'string' && record.code.trim()) {
      return record.code.trim();
    }

    if (typeof record.type === 'string' && record.type.trim()) {
      const location = formatLocation(record.loc);
      return location ? `${location}: ${record.type.trim()}` : record.type.trim();
    }

    try {
      return JSON.stringify(value);
    } catch {
      return null;
    }
  }

  return String(value);
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof RateLimitError) {
    return error.message;
  }

  if (error instanceof AxiosError) {
    const data = error.response?.data as
      | {
          detail?: unknown;
          message?: unknown;
          error?: unknown;
          code?: unknown;
        }
      | undefined;

    return (
      stringifyApiDetail(data?.detail)
      ?? stringifyApiDetail(data?.message)
      ?? stringifyApiDetail(data?.error)
      ?? stringifyApiDetail(data?.code)
      ?? fallback
    );
  }

  if (error instanceof Error) {
    return error.message || fallback;
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

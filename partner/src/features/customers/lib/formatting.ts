import { AxiosError } from 'axios';
import { RateLimitError } from '@/lib/api/client';

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

export function formatCurrencyAmount(
  amount: number | null | undefined,
  currency = 'USD',
  locale = 'ru-RU',
) {
  if (amount === null || amount === undefined || Number.isNaN(amount)) {
    return '--';
  }

  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${amount} ${currency}`;
  }
}

export function formatBytes(value: number | null | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '--';
  }

  if (value === 0) {
    return '0 B';
  }

  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const power = Math.min(
    Math.floor(Math.log(value) / Math.log(1024)),
    units.length - 1,
  );
  const scaled = value / 1024 ** power;

  return `${scaled.toFixed(scaled >= 100 || power === 0 ? 0 : 1)} ${units[power]}`;
}

export function shortId(value: string | null | undefined, size = 8) {
  if (!value) return '--';
  if (value.length <= size) return value;
  return value.slice(0, size);
}

export function humanizeToken(value: string | null | undefined) {
  if (!value) {
    return '--';
  }

  return value
    .replace(/[_-]/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
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

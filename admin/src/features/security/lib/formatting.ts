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

export function shortId(value: string | null | undefined, size = 8) {
  if (!value) return '--';
  if (value.length <= size) return value;
  return value.slice(0, size);
}

export function maskSensitiveCode(value: string | null | undefined) {
  if (!value) return '--';
  if (value.length <= 4) return value;
  return `${value.slice(0, 2)}${'*'.repeat(Math.max(4, value.length - 4))}${value.slice(-2)}`;
}

export function getDeviceKind(userAgent: string | null | undefined) {
  const normalized = userAgent?.toLowerCase() ?? '';
  if (
    normalized.includes('mobile') ||
    normalized.includes('android') ||
    normalized.includes('iphone')
  ) {
    return 'mobile' as const;
  }
  if (normalized.includes('ipad') || normalized.includes('tablet')) {
    return 'tablet' as const;
  }
  return 'desktop' as const;
}

export function describeUserAgent(userAgent: string | null | undefined) {
  if (!userAgent) return '--';

  const normalized = userAgent.toLowerCase();
  const browser =
    (normalized.includes('edge') && 'Edge') ||
    (normalized.includes('chrome') && 'Chrome') ||
    (normalized.includes('firefox') && 'Firefox') ||
    (normalized.includes('safari') && 'Safari') ||
    'Browser';

  const os =
    (normalized.includes('windows') && 'Windows') ||
    (normalized.includes('android') && 'Android') ||
    (normalized.includes('iphone') && 'iOS') ||
    (normalized.includes('ipad') && 'iPadOS') ||
    (normalized.includes('mac os') && 'macOS') ||
    (normalized.includes('linux') && 'Linux') ||
    'Unknown OS';

  return `${browser} on ${os}`;
}

export interface SecurityPostureInput {
  deviceCount: number;
  hasAntiPhishing: boolean;
  isActive: boolean;
  isEmailVerified: boolean;
  isTwoFactorEnabled: boolean;
}

export function calculateSecurityScore(input: SecurityPostureInput) {
  let score = 0;

  if (input.isActive) score += 15;
  if (input.isEmailVerified) score += 20;
  if (input.isTwoFactorEnabled) score += 35;
  if (input.hasAntiPhishing) score += 15;
  if (input.deviceCount === 1) score += 15;
  else if (input.deviceCount <= 3) score += 10;
  else if (input.deviceCount <= 5) score += 5;

  return Math.min(score, 100);
}

export function getSecurityTier(score: number) {
  if (score >= 85) return 'strong' as const;
  if (score >= 60) return 'moderate' as const;
  return 'weak' as const;
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

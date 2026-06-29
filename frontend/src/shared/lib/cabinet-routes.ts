import { locales } from '@/i18n/config';

export const CABINET_ROUTE_SEGMENTS = [
  'analytics',
  'dashboard',
  'delete-account',
  'messages',
  'monitoring',
  'onboarding',
  'partner',
  'payment-history',
  'referral',
  'rewards',
  'servers',
  'settings',
  'subscriptions',
  'support',
  'users',
  'wallet',
] as const;

export const CABINET_ALLOWED_PREFIXES = [
  '/dashboard',
  '/subscriptions',
  '/payment-history',
  '/referral',
  '/rewards',
  '/rewards/referral',
  '/rewards/gifts',
  '/rewards/invites',
  '/rewards/codes',
  '/rewards/notifications',
  '/messages',
  '/wallet',
  '/settings',
  '/support',
  '/servers',
  '/onboarding',
  '/monitoring',
  '/analytics',
  '/users',
  '/partner',
] as const;

const CABINET_ROUTE_SEGMENT_SET = new Set<string>(CABINET_ROUTE_SEGMENTS);

export function getLocalizedRouteSegment(pathname: string): string {
  const segments = pathname.split('/').filter(Boolean);
  const firstSegment = segments[0];
  const hasLocale = locales.includes(firstSegment as (typeof locales)[number]);

  return hasLocale ? segments[1] ?? '' : firstSegment ?? '';
}

export function isCabinetRouteSegment(segment: string): boolean {
  return CABINET_ROUTE_SEGMENT_SET.has(segment);
}

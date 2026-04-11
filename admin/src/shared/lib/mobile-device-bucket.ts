import {
  MOBILE_BREAKPOINTS,
  MOBILE_ROUTE_PERFORMANCE_BUDGETS,
  type MobileRouteGroup,
} from '@/shared/config/mobile-standards';

const DASHBOARD_SEGMENTS = new Set([
  'dashboard',
  'servers',
  'users',
  'subscriptions',
  'wallet',
  'payment-history',
  'referral',
  'partner',
  'analytics',
  'monitoring',
  'settings',
]);

const AUTH_SEGMENTS = new Set([
  'login',
  'register',
  'forgot-password',
  'reset-password',
  'magic-link',
  'telegram-link',
  'oauth',
]);

const LOCALE_SEGMENT_RE = /^\/([a-z]{2,3}-[A-Z]{2})(?=\/|$)/;
const LOW_BANDWIDTH_TYPES = new Set(['slow-2g', '2g', '3g']);

export type DeviceBucket =
  | 'mobile-low-power'
  | 'mobile-touch'
  | 'tablet-touch'
  | 'desktop';

export type ViewportBucket =
  | 'mobile-compact'
  | 'mobile-regular'
  | 'tablet'
  | 'desktop';

export interface DeviceCapabilitySnapshot {
  width: number;
  finePointer: boolean;
  prefersReducedMotion: boolean;
  hardwareConcurrency: number;
  deviceMemory: number;
  saveData: boolean;
  effectiveType: string;
}

interface NavigatorConnectionLike {
  effectiveType?: string;
  saveData?: boolean;
}

interface NavigatorWithDeviceHints extends Navigator {
  connection?: NavigatorConnectionLike;
  deviceMemory?: number;
}

export interface MobileTelemetryContext {
  deviceBucket: DeviceBucket;
  viewportBucket: ViewportBucket;
  routeGroup: MobileRouteGroup;
  reducedMotion: 'reduce' | 'no-preference';
  connectionType: string;
  saveData: 'on' | 'off';
}

export const DEFAULT_DEVICE_CAPABILITY_SNAPSHOT: DeviceCapabilitySnapshot = {
  width: 1280,
  finePointer: true,
  prefersReducedMotion: false,
  hardwareConcurrency: 8,
  deviceMemory: 8,
  saveData: false,
  effectiveType: '4g',
};

export function getViewportBucket(width: number): ViewportBucket {
  if (width <= MOBILE_BREAKPOINTS.compactPhoneMax) {
    return 'mobile-compact';
  }

  if (width <= MOBILE_BREAKPOINTS.mobileMax) {
    return 'mobile-regular';
  }

  if (width <= MOBILE_BREAKPOINTS.tabletMax) {
    return 'tablet';
  }

  return 'desktop';
}

function isLowPowerDevice(snapshot: DeviceCapabilitySnapshot): boolean {
  return (
    snapshot.prefersReducedMotion ||
    snapshot.saveData ||
    LOW_BANDWIDTH_TYPES.has(snapshot.effectiveType) ||
    snapshot.hardwareConcurrency < 4 ||
    (snapshot.deviceMemory > 0 && snapshot.deviceMemory < 4)
  );
}

export function getDeviceBucket(
  snapshot: DeviceCapabilitySnapshot,
): DeviceBucket {
  const viewportBucket = getViewportBucket(snapshot.width);

  if (viewportBucket === 'desktop' && snapshot.finePointer) {
    return 'desktop';
  }

  if (viewportBucket === 'tablet') {
    return 'tablet-touch';
  }

  return isLowPowerDevice(snapshot) ? 'mobile-low-power' : 'mobile-touch';
}

function stripLocaleSegment(pathname: string): string {
  const withoutLocale = pathname.replace(LOCALE_SEGMENT_RE, '');
  return withoutLocale === '' ? '/' : withoutLocale;
}

export function getRouteGroup(pathname: string): MobileRouteGroup {
  const normalizedPath = stripLocaleSegment(pathname);
  const [firstSegment = ''] = normalizedPath.split('/').filter(Boolean);

  if (firstSegment === 'miniapp') {
    return 'miniapp';
  }

  if (DASHBOARD_SEGMENTS.has(firstSegment)) {
    return 'dashboard';
  }

  if (AUTH_SEGMENTS.has(firstSegment)) {
    return 'auth';
  }

  return 'marketing';
}

function matchesMedia(query: string): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia(query).matches
  );
}

export function readDeviceCapabilitySnapshot(): DeviceCapabilitySnapshot {
  if (typeof window === 'undefined') {
    return DEFAULT_DEVICE_CAPABILITY_SNAPSHOT;
  }

  const nav = navigator as NavigatorWithDeviceHints;

  return {
    width: window.innerWidth,
    finePointer: matchesMedia('(hover: hover) and (pointer: fine)'),
    prefersReducedMotion: matchesMedia('(prefers-reduced-motion: reduce)'),
    hardwareConcurrency: nav.hardwareConcurrency ?? 0,
    deviceMemory: nav.deviceMemory ?? 0,
    saveData: nav.connection?.saveData ?? false,
    effectiveType: nav.connection?.effectiveType ?? 'unknown',
  };
}

export function getMobileTelemetryContext(
  pathname: string = typeof window !== 'undefined' ? window.location.pathname : '/',
): MobileTelemetryContext {
  const snapshot = readDeviceCapabilitySnapshot();

  return {
    deviceBucket: getDeviceBucket(snapshot),
    viewportBucket: getViewportBucket(snapshot.width),
    routeGroup: getRouteGroup(pathname),
    reducedMotion: snapshot.prefersReducedMotion ? 'reduce' : 'no-preference',
    connectionType: snapshot.effectiveType,
    saveData: snapshot.saveData ? 'on' : 'off',
  };
}

export function getMobilePerformanceBudget(
  routeGroup: MobileRouteGroup,
): (typeof MOBILE_ROUTE_PERFORMANCE_BUDGETS)[MobileRouteGroup] {
  return MOBILE_ROUTE_PERFORMANCE_BUDGETS[routeGroup];
}

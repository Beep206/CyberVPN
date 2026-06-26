import type { CustomerOnboardingAuthSummary } from '@/lib/api/auth';

type OnboardingSurface = 'web' | 'miniapp';

const WEB_ONBOARDING_PATH = '/onboarding/code';
const MINIAPP_ONBOARDING_PATH = '/miniapp/onboarding/code';

const WEB_FALLBACK_PATH = '/dashboard';
const MINIAPP_FALLBACK_PATH = '/miniapp/home';

const MINIAPP_DESTINATION_MAP: Record<string, string> = {
  '/dashboard': MINIAPP_FALLBACK_PATH,
  '/subscriptions': '/miniapp/plans',
  '/rewards': '/miniapp/rewards',
};

export function shouldRouteToPostRegistrationOnboarding(
  onboarding: CustomerOnboardingAuthSummary | null | undefined,
): boolean {
  return onboarding?.required === true && onboarding.status === 'pending';
}

export function getPostRegistrationOnboardingPath(surface: OnboardingSurface): string {
  return surface === 'miniapp' ? MINIAPP_ONBOARDING_PATH : WEB_ONBOARDING_PATH;
}

export function getPostAuthDestination({
  onboarding,
  surface,
}: {
  onboarding: CustomerOnboardingAuthSummary | null | undefined;
  surface: OnboardingSurface;
}): string {
  if (shouldRouteToPostRegistrationOnboarding(onboarding)) {
    return getPostRegistrationOnboardingPath(surface);
  }

  return surface === 'miniapp' ? MINIAPP_FALLBACK_PATH : WEB_FALLBACK_PATH;
}

export function normalizeOnboardingDestination(
  destination: string | null | undefined,
  surface: OnboardingSurface,
): string {
  const fallback = surface === 'miniapp' ? MINIAPP_FALLBACK_PATH : WEB_FALLBACK_PATH;
  const normalized = destination?.trim();
  if (!normalized || !normalized.startsWith('/') || normalized.startsWith('//')) {
    return fallback;
  }

  const pathOnly = normalized.split(/[?#]/u, 1)[0] || fallback;
  if (surface === 'miniapp') {
    return MINIAPP_DESTINATION_MAP[pathOnly] ?? (pathOnly.startsWith('/miniapp/') ? pathOnly : fallback);
  }

  if (pathOnly.startsWith('/miniapp/')) {
    return fallback;
  }

  return normalized;
}

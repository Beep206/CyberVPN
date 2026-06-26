import { describe, expect, it } from 'vitest';
import {
  getPostAuthDestination,
  normalizeOnboardingDestination,
  shouldRouteToPostRegistrationOnboarding,
} from '../routing';

const pendingOnboarding = {
  required: true,
  status: 'pending' as const,
  flow_key: 'post_registration_growth_code_v1',
  version: 1,
  allowed_code_types: ['promo' as const],
  flow_token: 'flow-token',
  message_key: 'onboarding.required',
  server_state_available: true,
  referral_already_attributed: false,
};

describe('customer onboarding routing', () => {
  it('routes only pending required onboarding responses to the prompt', () => {
    expect(shouldRouteToPostRegistrationOnboarding(pendingOnboarding)).toBe(true);
    expect(getPostAuthDestination({
      onboarding: pendingOnboarding,
      surface: 'web',
    })).toBe('/onboarding/code');
    expect(getPostAuthDestination({
      onboarding: { ...pendingOnboarding, status: 'completed', required: false },
      surface: 'web',
    })).toBe('/dashboard');
  });

  it('maps dashboard destinations into miniapp-safe routes', () => {
    expect(normalizeOnboardingDestination('/dashboard', 'miniapp')).toBe('/miniapp/home');
    expect(normalizeOnboardingDestination('/subscriptions', 'miniapp')).toBe('/miniapp/plans');
    expect(normalizeOnboardingDestination('https://evil.example/cb', 'miniapp')).toBe('/miniapp/home');
    expect(normalizeOnboardingDestination('//evil.example/cb', 'web')).toBe('/dashboard');
  });
});

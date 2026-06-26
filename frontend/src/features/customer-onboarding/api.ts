import { apiClient, CANONICAL_IDEMPOTENCY_HEADER } from '@/lib/api/client';
import type { components } from '@/lib/api/generated/types';

export type CustomerOnboardingCurrentResponse =
  components['schemas']['CustomerOnboardingCurrentResponse'];
export type CustomerOnboardingApplyRequest =
  components['schemas']['CustomerOnboardingApplyRequest'];
export type CustomerOnboardingApplyResponse =
  components['schemas']['CustomerOnboardingApplyResponse'];
export type CustomerOnboardingSkipRequest =
  components['schemas']['CustomerOnboardingSkipRequest'];
export type CustomerOnboardingSkipResponse =
  components['schemas']['CustomerOnboardingSkipResponse'];

function createIdempotencyKey(): string {
  if (typeof globalThis.crypto?.randomUUID === 'function') {
    return globalThis.crypto.randomUUID();
  }

  const suffix = Math.random().toString(16).slice(2, 14).padEnd(12, '0');
  return `00000000-0000-4000-8000-${suffix}`;
}

function withIdempotencyKey<T extends { idempotency_key?: string | null }>(
  payload: T,
): { payload: T & { idempotency_key: string }; idempotencyKey: string } {
  const idempotencyKey = payload.idempotency_key?.trim() || createIdempotencyKey();
  return {
    idempotencyKey,
    payload: {
      ...payload,
      idempotency_key: idempotencyKey,
    },
  };
}

export const CUSTOMER_ONBOARDING_CURRENT_QUERY_KEY = ['customer-onboarding', 'current'] as const;

export const customerOnboardingApi = {
  current: () =>
    apiClient.get<CustomerOnboardingCurrentResponse>('/customer/onboarding/current'),

  applyGrowthCode: (request: CustomerOnboardingApplyRequest) => {
    const { payload, idempotencyKey } = withIdempotencyKey(request);
    return apiClient.post<CustomerOnboardingApplyResponse>(
      '/customer/onboarding/growth-code/apply',
      payload,
      {
        headers: {
          [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey,
        },
      },
    );
  },

  skipGrowthCode: (request: CustomerOnboardingSkipRequest) => {
    const { payload, idempotencyKey } = withIdempotencyKey(request);
    return apiClient.post<CustomerOnboardingSkipResponse>(
      '/customer/onboarding/growth-code/skip',
      payload,
      {
        headers: {
          [CANONICAL_IDEMPOTENCY_HEADER]: idempotencyKey,
        },
      },
    );
  },
};

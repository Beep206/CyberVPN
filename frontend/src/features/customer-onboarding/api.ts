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
export type CustomerOnboardingPreviewRequest =
  components['schemas']['CustomerOnboardingPreviewRequest'];
export type CustomerOnboardingPreviewResponse =
  components['schemas']['CustomerOnboardingPreviewResponse'];
export type CustomerOnboardingConnectionInstructionStep =
  components['schemas']['CustomerOnboardingConnectionInstructionStep'];
export type CustomerOnboardingConnectionAppRecommendation =
  components['schemas']['CustomerOnboardingConnectionAppRecommendation'];
export type CustomerOnboardingConnectionInstruction =
  components['schemas']['CustomerOnboardingConnectionInstruction'];
export type CustomerOnboardingConnectionBootstrapResponse =
  components['schemas']['CustomerOnboardingConnectionBootstrapResponse'];
export type MarkOnboardingConnectionConnectedRequest =
  components['schemas']['MarkOnboardingConnectionConnectedRequest'];
export type MarkOnboardingConnectionConnectedResponse =
  components['schemas']['MarkOnboardingConnectionConnectedResponse'];
export type OnboardingConnectionSurface =
  CustomerOnboardingConnectionBootstrapResponse['surface'];
export type OnboardingConnectionPlatform =
  Exclude<MarkOnboardingConnectionConnectedRequest['platform'], null>;

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

  previewGrowthCode: (request: CustomerOnboardingPreviewRequest) =>
    apiClient.post<CustomerOnboardingPreviewResponse>(
      '/customer/onboarding/growth-code/preview',
      request,
    ),

  connectionBootstrap: (params: {
    surface: OnboardingConnectionSurface;
    platform_hint?: OnboardingConnectionPlatform;
  }) =>
    apiClient.get<CustomerOnboardingConnectionBootstrapResponse>(
      '/customer/onboarding/connection/bootstrap',
      { params },
    ),

  markConnected: (request: MarkOnboardingConnectionConnectedRequest) =>
    apiClient.post<MarkOnboardingConnectionConnectedResponse>(
      '/customer/onboarding/connection/mark-connected',
      request,
    ),
};

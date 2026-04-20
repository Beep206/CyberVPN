// @vitest-environment node

import { describe, expect, it } from 'vitest';
import type { components, paths } from '../generated/types';

const PHASE6_FRONTEND_PATHS = [
  '/api/v1/quotes/',
  '/api/v1/checkout-sessions/',
  '/api/v1/orders/',
  '/api/v1/orders/commit',
  '/api/v1/payment-attempts/',
  '/api/v1/entitlements/current',
  '/api/v1/access-delivery-channels/current/service-state',
] as const satisfies readonly (keyof paths)[];

type Phase6QuoteSessionResponse = components['schemas']['QuoteSessionResponse'];
type Phase6CheckoutSessionResponse = components['schemas']['CheckoutSessionResponse'];
type Phase6OrderResponse = components['schemas']['OrderResponse'];
type Phase6PaymentAttemptResponse = components['schemas']['PaymentAttemptResponse'];
type Phase6CurrentEntitlementStateResponse = components['schemas']['CurrentEntitlementStateResponse'];
type Phase6CurrentServiceStateResponse = components['schemas']['CurrentServiceStateResponse'];

describe('Phase 6 generated API contract', () => {
  it('includes the frozen official-web commerce and service-access path families', () => {
    expect(PHASE6_FRONTEND_PATHS).toContain('/api/v1/orders/commit');
    expect(PHASE6_FRONTEND_PATHS).toContain('/api/v1/access-delivery-channels/current/service-state');
  });

  it('exposes the required official-web schemas', () => {
    const compileGuard: {
      quote: Phase6QuoteSessionResponse | null;
      checkout: Phase6CheckoutSessionResponse | null;
      order: Phase6OrderResponse | null;
      paymentAttempt: Phase6PaymentAttemptResponse | null;
      currentEntitlementState: Phase6CurrentEntitlementStateResponse | null;
      currentServiceState: Phase6CurrentServiceStateResponse | null;
    } = {
      quote: null,
      checkout: null,
      order: null,
      paymentAttempt: null,
      currentEntitlementState: null,
      currentServiceState: null,
    };

    expect(compileGuard).toEqual({
      quote: null,
      checkout: null,
      order: null,
      paymentAttempt: null,
      currentEntitlementState: null,
      currentServiceState: null,
    });
  });
});

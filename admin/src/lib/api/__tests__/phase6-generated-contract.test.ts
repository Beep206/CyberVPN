// @vitest-environment node

import { describe, expect, it } from 'vitest';
import type { components, paths } from '../generated/types';

const PHASE6_ADMIN_PATHS = [
  '/api/v1/admin/mobile-users/{user_id}/operations-insight',
  '/api/v1/orders/{order_id}/explainability',
  '/api/v1/payment-disputes/',
  '/api/v1/partner-statements/',
  '/api/v1/payouts/',
  '/api/v1/service-identities/inspect/service-state',
] as const satisfies readonly (keyof paths)[];

type Phase6AdminCustomerOperationsInsightResponse =
  components['schemas']['AdminCustomerOperationsInsightResponse'];
type Phase6OrderExplainabilityResponse = components['schemas']['OrderExplainabilityResponse'];
type Phase6PaymentDisputeResponse = components['schemas']['PaymentDisputeResponse'];
type Phase6PartnerStatementResponse = components['schemas']['PartnerStatementResponse'];
type Phase6PayoutInstructionResponse = components['schemas']['PayoutInstructionResponse'];
type Phase6ServiceAccessObservabilityResponse =
  components['schemas']['ServiceAccessObservabilityResponse'];

describe('Phase 6 generated API contract', () => {
  it('includes the frozen admin operator path families', () => {
    expect(PHASE6_ADMIN_PATHS).toContain('/api/v1/admin/mobile-users/{user_id}/operations-insight');
    expect(PHASE6_ADMIN_PATHS).toContain('/api/v1/service-identities/inspect/service-state');
  });

  it('exposes the required admin operator schemas', () => {
    const compileGuard: {
      operationsInsight: Phase6AdminCustomerOperationsInsightResponse | null;
      orderExplainability: Phase6OrderExplainabilityResponse | null;
      paymentDispute: Phase6PaymentDisputeResponse | null;
      partnerStatement: Phase6PartnerStatementResponse | null;
      payoutInstruction: Phase6PayoutInstructionResponse | null;
      serviceAccessObservability: Phase6ServiceAccessObservabilityResponse | null;
    } = {
      operationsInsight: null,
      orderExplainability: null,
      paymentDispute: null,
      partnerStatement: null,
      payoutInstruction: null,
      serviceAccessObservability: null,
    };

    expect(compileGuard).toEqual({
      operationsInsight: null,
      orderExplainability: null,
      paymentDispute: null,
      partnerStatement: null,
      payoutInstruction: null,
      serviceAccessObservability: null,
    });
  });
});

// @vitest-environment node

import { describe, expect, it } from 'vitest';
import {
  PRODUCT_DASHBOARD_CONTRACTS,
  validateProductDashboardContracts,
} from '@/lib/product-intelligence/dashboard-contracts';

describe('product dashboard contracts', () => {
  it('freezes the four canonical P3.7 dashboard slices', () => {
    expect(Object.keys(PRODUCT_DASHBOARD_CONTRACTS)).toEqual([
      'checkout_funnel_v1',
      'onboarding_funnel_v1',
      'partner_workspace_usage_v1',
      'retention_lifecycle_v1',
    ]);
  });

  it('keeps all active required events inside the governed product analytics contract set', () => {
    expect(validateProductDashboardContracts().missingActiveEvents).toEqual({
      checkout_funnel_v1: [],
      onboarding_funnel_v1: [],
      partner_workspace_usage_v1: [],
      retention_lifecycle_v1: [],
    });
  });

  it('marks renewal and cancellation as reserved retention follow-ups instead of pretending they are live', () => {
    expect(PRODUCT_DASHBOARD_CONTRACTS.retention_lifecycle_v1.reservedEvents).toEqual([
      'subscription_renewed',
      'subscription_cancelled',
    ]);
  });
});

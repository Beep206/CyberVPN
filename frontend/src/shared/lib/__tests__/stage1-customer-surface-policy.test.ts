import { describe, expect, it } from 'vitest';
import {
  canStage1CustomerDashboardSurfaceAccess,
  getStage1CustomerDashboardSurfacePolicy,
  STAGE1_CUSTOMER_DASHBOARD_OPERATOR_ROUTE_HREFS,
  STAGE1_CUSTOMER_DASHBOARD_OPERATOR_SURFACES,
  STAGE1_CUSTOMER_SERVER_OPERATOR_METRICS_VISIBLE,
} from '../stage1-customer-surface-policy';

describe('stage1 customer surface policy', () => {
  it('allows customer cabinet and enabled growth surfaces by default', () => {
    expect(getStage1CustomerDashboardSurfacePolicy()).toMatchObject({
      analytics: false,
      dashboard: true,
      monitoring: false,
      partner: false,
      paymentHistory: true,
      referral: true,
      servers: true,
      settings: true,
      subscriptions: true,
      users: false,
      wallet: true,
    });
  });

  it('keeps operator/admin route hrefs out of the S1 customer dashboard', () => {
    expect(STAGE1_CUSTOMER_DASHBOARD_OPERATOR_SURFACES).toEqual([
      'analytics',
      'monitoring',
      'partner',
      'users',
    ]);
    expect(STAGE1_CUSTOMER_DASHBOARD_OPERATOR_ROUTE_HREFS).toEqual([
      '/analytics',
      '/monitoring',
      '/partner',
      '/users',
    ]);
    expect(
      STAGE1_CUSTOMER_DASHBOARD_OPERATOR_SURFACES.every(
        (surface) => !canStage1CustomerDashboardSurfaceAccess(surface),
      ),
    ).toBe(true);
  });

  it('keeps server operator metrics hidden on customer node access surfaces', () => {
    expect(STAGE1_CUSTOMER_SERVER_OPERATOR_METRICS_VISIBLE).toBe(false);
  });
});

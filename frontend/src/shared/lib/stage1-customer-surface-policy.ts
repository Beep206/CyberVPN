import { STAGE1_REFERRAL_UI_ENABLED } from './stage1-growth-flags';

export type Stage1CustomerDashboardSurface =
  | 'analytics'
  | 'dashboard'
  | 'monitoring'
  | 'partner'
  | 'paymentHistory'
  | 'referral'
  | 'servers'
  | 'settings'
  | 'subscriptions'
  | 'users'
  | 'wallet';

export const STAGE1_CUSTOMER_DASHBOARD_OPERATOR_SURFACES = [
  'analytics',
  'monitoring',
  'partner',
  'users',
] as const satisfies readonly Stage1CustomerDashboardSurface[];

export const STAGE1_CUSTOMER_DASHBOARD_OPERATOR_ROUTE_HREFS = [
  '/analytics',
  '/monitoring',
  '/partner',
  '/users',
] as const;

export const STAGE1_CUSTOMER_SERVER_OPERATOR_METRICS_VISIBLE = false;

export function getStage1CustomerDashboardSurfacePolicy(): Record<
  Stage1CustomerDashboardSurface,
  boolean
> {
  return {
    analytics: false,
    dashboard: true,
    monitoring: false,
    partner: false,
    paymentHistory: true,
    referral: STAGE1_REFERRAL_UI_ENABLED,
    servers: true,
    settings: true,
    subscriptions: true,
    users: false,
    wallet: true,
  };
}

export function canStage1CustomerDashboardSurfaceAccess(
  surface: Stage1CustomerDashboardSurface,
): boolean {
  return getStage1CustomerDashboardSurfacePolicy()[surface];
}

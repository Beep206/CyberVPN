import {
  PRODUCT_ANALYTICS_EVENT_DEFINITIONS,
  type ProductAnalyticsEventName,
} from './contracts';

export type ProductDashboardKey =
  | 'checkout_funnel_v1'
  | 'onboarding_funnel_v1'
  | 'partner_workspace_usage_v1'
  | 'retention_lifecycle_v1';

export type ReservedProductAnalyticsEventName =
  | 'subscription_cancelled'
  | 'subscription_renewed';

type ProductDashboardContract = {
  owner: string;
  title: string;
  description: string;
  primaryMetric: string;
  guardrailMetrics: readonly string[];
  requiredEvents: readonly ProductAnalyticsEventName[];
  authoritativeEvents: readonly ProductAnalyticsEventName[];
  reservedEvents?: readonly ReservedProductAnalyticsEventName[];
};

export const PRODUCT_DASHBOARD_CONTRACTS: Record<ProductDashboardKey, ProductDashboardContract> = {
  checkout_funnel_v1: {
    owner: 'growth-platform',
    title: 'Checkout funnel',
    description: 'Storefront checkout entry, progression, and payment capture posture for branded commerce.',
    primaryMetric: 'checkout_payment_captured / checkout_started',
    guardrailMetrics: ['checkout_payment_submitted / checkout_started', 'checkout_step_completed / checkout_started'],
    requiredEvents: [
      'checkout_started',
      'checkout_step_viewed',
      'checkout_step_completed',
      'checkout_payment_submitted',
      'checkout_payment_captured',
    ],
    authoritativeEvents: ['checkout_payment_captured'],
  },
  onboarding_funnel_v1: {
    owner: 'growth-platform',
    title: 'Onboarding funnel',
    description: 'Partner application onboarding progression from draft entry to first authoritative activation milestone.',
    primaryMetric: 'partner_user_activated / onboarding_started',
    guardrailMetrics: ['onboarding_step_completed / onboarding_started'],
    requiredEvents: [
      'onboarding_started',
      'onboarding_step_completed',
      'partner_user_activated',
    ],
    authoritativeEvents: ['partner_user_activated'],
  },
  partner_workspace_usage_v1: {
    owner: 'growth-platform',
    title: 'Partner workspace usage',
    description: 'Dashboard usage, governed feature-flag exposures, and experiment visibility for partner-facing product surfaces.',
    primaryMetric: 'partner_dashboard_viewed',
    guardrailMetrics: ['feature_flag_evaluated', 'experiment_exposure_recorded'],
    requiredEvents: [
      'partner_dashboard_viewed',
      'feature_flag_evaluated',
      'experiment_exposure_recorded',
    ],
    authoritativeEvents: ['feature_flag_evaluated', 'experiment_exposure_recorded'],
  },
  retention_lifecycle_v1: {
    owner: 'growth-platform',
    title: 'Retention lifecycle',
    description: 'First authoritative activation and payment-capture anchors for lifecycle and retention dashboards.',
    primaryMetric: 'subscription_activated / checkout_payment_captured',
    guardrailMetrics: ['checkout_payment_captured', 'subscription_activated'],
    requiredEvents: [
      'checkout_payment_captured',
      'subscription_activated',
    ],
    authoritativeEvents: [
      'checkout_payment_captured',
      'subscription_activated',
    ],
    reservedEvents: ['subscription_renewed', 'subscription_cancelled'],
  },
};

export function validateProductDashboardContracts(): {
  activeEventCoverage: Record<ProductDashboardKey, readonly ProductAnalyticsEventName[]>;
  missingActiveEvents: Record<ProductDashboardKey, readonly ProductAnalyticsEventName[]>;
} {
  const entries = Object.entries(PRODUCT_DASHBOARD_CONTRACTS).map(([dashboardKey, contract]) => {
    const missing = contract.requiredEvents.filter((eventName) => !(eventName in PRODUCT_ANALYTICS_EVENT_DEFINITIONS));
    return [
      dashboardKey as ProductDashboardKey,
      {
        activeEventCoverage: contract.requiredEvents,
        missingActiveEvents: missing,
      },
    ] as const;
  });

  const activeEventCoverage = {} as Record<ProductDashboardKey, readonly ProductAnalyticsEventName[]>;
  const missingActiveEvents = {} as Record<ProductDashboardKey, readonly ProductAnalyticsEventName[]>;

  entries.forEach(([key, value]) => {
    activeEventCoverage[key] = value.activeEventCoverage;
    missingActiveEvents[key] = value.missingActiveEvents;
  });

  return {
    activeEventCoverage,
    missingActiveEvents,
  };
}

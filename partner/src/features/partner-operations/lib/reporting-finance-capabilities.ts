import type { PartnerPortalState } from '@/features/partner-portal-state/lib/portal-state';

export type PartnerAnalyticsSurfaceMode =
  | 'review'
  | 'lite'
  | 'full'
  | 'history_only';

export type PartnerFinanceSurfaceMode =
  | 'review'
  | 'onboarding'
  | 'full'
  | 'blocked'
  | 'history_only';

export type PartnerCasesSurfaceMode =
  | 'applicant'
  | 'operational'
  | 'dispute'
  | 'history_only';

export type PartnerOperationalCapabilityAvailability =
  | 'enabled'
  | 'conditional'
  | 'blocked';

export type PartnerAnalyticsCapabilityKey =
  | 'overview_dashboards'
  | 'code_level_reporting'
  | 'exports'
  | 'statement_exports'
  | 'payout_status_exports'
  | 'explainability';

export type PartnerFinanceCapabilityKey =
  | 'payout_accounts'
  | 'statement_visibility'
  | 'reserve_visibility'
  | 'payout_forecast'
  | 'adjustment_history'
  | 'payout_actions';

export type PartnerCasesCapabilityKey =
  | 'applicant_messages'
  | 'finance_cases'
  | 'attribution_disputes'
  | 'payout_disputes'
  | 'technical_support'
  | 'attachment_handoffs';

export interface PartnerOperationalCapability<TKey extends string> {
  key: TKey;
  availability: PartnerOperationalCapabilityAvailability;
}

function mapCapabilities<TKey extends string>(
  keys: readonly TKey[],
  availabilityMap: Partial<Record<TKey, PartnerOperationalCapabilityAvailability>>,
  fallback: PartnerOperationalCapabilityAvailability = 'blocked',
): PartnerOperationalCapability<TKey>[] {
  return keys.map((key) => ({
    key,
    availability: availabilityMap[key] ?? fallback,
  }));
}

const ANALYTICS_KEYS: readonly PartnerAnalyticsCapabilityKey[] = [
  'overview_dashboards',
  'code_level_reporting',
  'exports',
  'statement_exports',
  'payout_status_exports',
  'explainability',
];

const FINANCE_KEYS: readonly PartnerFinanceCapabilityKey[] = [
  'payout_accounts',
  'statement_visibility',
  'reserve_visibility',
  'payout_forecast',
  'adjustment_history',
  'payout_actions',
];

const CASES_KEYS: readonly PartnerCasesCapabilityKey[] = [
  'applicant_messages',
  'finance_cases',
  'attribution_disputes',
  'payout_disputes',
  'technical_support',
  'attachment_handoffs',
];

export function getPartnerAnalyticsSurfaceMode(
  state: PartnerPortalState,
): PartnerAnalyticsSurfaceMode {
  if (
    state.workspaceStatus === 'draft'
    || state.workspaceStatus === 'email_verified'
    || state.workspaceStatus === 'submitted'
    || state.workspaceStatus === 'needs_info'
    || state.workspaceStatus === 'under_review'
    || state.workspaceStatus === 'waitlisted'
  ) {
    return 'review';
  }

  if (state.workspaceStatus === 'approved_probation') {
    return 'lite';
  }

  if (
    state.workspaceStatus === 'restricted'
    || state.workspaceStatus === 'suspended'
    || state.workspaceStatus === 'terminated'
  ) {
    return 'history_only';
  }

  return 'full';
}

export function getPartnerFinanceSurfaceMode(
  state: PartnerPortalState,
): PartnerFinanceSurfaceMode {
  if (
    state.workspaceStatus === 'draft'
    || state.workspaceStatus === 'email_verified'
    || state.workspaceStatus === 'submitted'
    || state.workspaceStatus === 'needs_info'
    || state.workspaceStatus === 'under_review'
    || state.workspaceStatus === 'waitlisted'
  ) {
    return 'review';
  }

  if (state.workspaceStatus === 'approved_probation') {
    return 'onboarding';
  }

  if (state.workspaceStatus === 'terminated') {
    return 'history_only';
  }

  if (
    state.workspaceStatus === 'restricted'
    || state.workspaceStatus === 'suspended'
    || state.financeReadiness === 'blocked'
  ) {
    return 'blocked';
  }

  return 'full';
}

export function getPartnerCasesSurfaceMode(
  state: PartnerPortalState,
): PartnerCasesSurfaceMode {
  if (
    state.workspaceStatus === 'draft'
    || state.workspaceStatus === 'email_verified'
    || state.workspaceStatus === 'submitted'
    || state.workspaceStatus === 'needs_info'
    || state.workspaceStatus === 'under_review'
    || state.workspaceStatus === 'waitlisted'
  ) {
    return 'applicant';
  }

  if (state.workspaceStatus === 'terminated') {
    return 'history_only';
  }

  if (
    state.workspaceStatus === 'restricted'
    || state.workspaceStatus === 'suspended'
    || state.governanceState === 'limited'
    || state.financeReadiness === 'blocked'
  ) {
    return 'dispute';
  }

  return 'operational';
}

export function getPartnerAnalyticsCapabilities(
  state: PartnerPortalState,
): PartnerOperationalCapability<PartnerAnalyticsCapabilityKey>[] {
  const mode = getPartnerAnalyticsSurfaceMode(state);

  if (mode === 'review') {
    return mapCapabilities(ANALYTICS_KEYS, {});
  }

  if (mode === 'lite') {
    return mapCapabilities(ANALYTICS_KEYS, {
      overview_dashboards: 'enabled',
      code_level_reporting: 'conditional',
      exports: 'conditional',
      statement_exports: 'blocked',
      payout_status_exports: 'blocked',
      explainability: 'enabled',
    });
  }

  if (mode === 'history_only') {
    return mapCapabilities(ANALYTICS_KEYS, {
      overview_dashboards: 'enabled',
      code_level_reporting: 'enabled',
      exports: 'enabled',
      statement_exports: 'enabled',
      payout_status_exports: 'conditional',
      explainability: 'enabled',
    });
  }

  return mapCapabilities(ANALYTICS_KEYS, {
    overview_dashboards: 'enabled',
    code_level_reporting: 'enabled',
    exports: 'enabled',
    statement_exports: 'enabled',
    payout_status_exports: 'enabled',
    explainability: 'enabled',
  });
}

export function getPartnerFinanceCapabilities(
  state: PartnerPortalState,
): PartnerOperationalCapability<PartnerFinanceCapabilityKey>[] {
  const mode = getPartnerFinanceSurfaceMode(state);

  if (mode === 'review') {
    return mapCapabilities(FINANCE_KEYS, {});
  }

  if (mode === 'onboarding') {
    return mapCapabilities(FINANCE_KEYS, {
      payout_accounts: 'enabled',
      statement_visibility: 'conditional',
      reserve_visibility: 'conditional',
      payout_forecast: 'conditional',
      adjustment_history: 'conditional',
      payout_actions: 'blocked',
    });
  }

  if (mode === 'blocked') {
    return mapCapabilities(FINANCE_KEYS, {
      payout_accounts: 'conditional',
      statement_visibility: 'enabled',
      reserve_visibility: 'enabled',
      payout_forecast: 'blocked',
      adjustment_history: 'enabled',
      payout_actions: 'blocked',
    });
  }

  if (mode === 'history_only') {
    return mapCapabilities(FINANCE_KEYS, {
      payout_accounts: 'blocked',
      statement_visibility: 'enabled',
      reserve_visibility: 'enabled',
      payout_forecast: 'blocked',
      adjustment_history: 'enabled',
      payout_actions: 'blocked',
    });
  }

  return mapCapabilities(FINANCE_KEYS, {
    payout_accounts: 'enabled',
    statement_visibility: 'enabled',
    reserve_visibility: 'enabled',
    payout_forecast: 'enabled',
    adjustment_history: 'enabled',
    payout_actions: 'blocked',
  });
}

export function getPartnerCasesCapabilities(
  state: PartnerPortalState,
): PartnerOperationalCapability<PartnerCasesCapabilityKey>[] {
  const mode = getPartnerCasesSurfaceMode(state);

  if (mode === 'applicant') {
    return mapCapabilities(CASES_KEYS, {
      applicant_messages: 'enabled',
      attachment_handoffs: 'conditional',
    });
  }

  if (mode === 'dispute') {
    return mapCapabilities(CASES_KEYS, {
      applicant_messages: 'enabled',
      finance_cases: 'enabled',
      attribution_disputes: 'enabled',
      payout_disputes: 'enabled',
      technical_support: 'conditional',
      attachment_handoffs: 'enabled',
    });
  }

  if (mode === 'history_only') {
    return mapCapabilities(CASES_KEYS, {
      finance_cases: 'enabled',
      attribution_disputes: 'enabled',
      payout_disputes: 'enabled',
      technical_support: 'conditional',
      attachment_handoffs: 'conditional',
    });
  }

  return mapCapabilities(CASES_KEYS, {
    applicant_messages: 'enabled',
    finance_cases: 'enabled',
    attribution_disputes: 'enabled',
    payout_disputes: 'enabled',
    technical_support: 'enabled',
    attachment_handoffs: 'enabled',
  });
}

import {
  doesPartnerReleaseRingMeetRequirement,
  getPartnerRouteRequiredReleaseRing,
  type PartnerSectionSlug,
} from '@/features/partner-shell/config/section-registry';
import type {
  PartnerPortalState,
  PartnerWorkspaceStatus,
} from '@/features/partner-portal-state/lib/portal-state';

export type PartnerVisibilityBand =
  | 'pre_submit'
  | 'review'
  | 'probation'
  | 'active'
  | 'constrained'
  | 'terminal';

export type PartnerSectionVisibility =
  | 'hidden'
  | 'read'
  | 'task'
  | 'limited'
  | 'full';

export type PartnerRouteBlockReason = 'release_ring' | 'status' | null;

export type PartnerRouteKey = 'dashboard' | PartnerSectionSlug;

const PARTNER_VISIBILITY_MATRIX: Record<
  PartnerRouteKey,
  Record<PartnerVisibilityBand, PartnerSectionVisibility>
> = {
  dashboard: {
    pre_submit: 'task',
    review: 'task',
    probation: 'limited',
    active: 'full',
    constrained: 'read',
    terminal: 'read',
  },
  application: {
    pre_submit: 'full',
    review: 'full',
    probation: 'task',
    active: 'read',
    constrained: 'read',
    terminal: 'read',
  },
  organization: {
    pre_submit: 'full',
    review: 'full',
    probation: 'full',
    active: 'full',
    constrained: 'read',
    terminal: 'read',
  },
  team: {
    pre_submit: 'hidden',
    review: 'hidden',
    probation: 'limited',
    active: 'full',
    constrained: 'read',
    terminal: 'hidden',
  },
  programs: {
    pre_submit: 'hidden',
    review: 'read',
    probation: 'limited',
    active: 'full',
    constrained: 'read',
    terminal: 'read',
  },
  legal: {
    pre_submit: 'read',
    review: 'read',
    probation: 'full',
    active: 'full',
    constrained: 'read',
    terminal: 'read',
  },
  codes: {
    pre_submit: 'hidden',
    review: 'hidden',
    probation: 'limited',
    active: 'full',
    constrained: 'read',
    terminal: 'hidden',
  },
  campaigns: {
    pre_submit: 'hidden',
    review: 'hidden',
    probation: 'limited',
    active: 'full',
    constrained: 'read',
    terminal: 'hidden',
  },
  conversions: {
    pre_submit: 'hidden',
    review: 'hidden',
    probation: 'limited',
    active: 'full',
    constrained: 'read',
    terminal: 'hidden',
  },
  analytics: {
    pre_submit: 'hidden',
    review: 'hidden',
    probation: 'limited',
    active: 'full',
    constrained: 'read',
    terminal: 'read',
  },
  finance: {
    pre_submit: 'hidden',
    review: 'hidden',
    probation: 'task',
    active: 'full',
    constrained: 'read',
    terminal: 'read',
  },
  compliance: {
    pre_submit: 'hidden',
    review: 'task',
    probation: 'limited',
    active: 'full',
    constrained: 'read',
    terminal: 'read',
  },
  integrations: {
    pre_submit: 'hidden',
    review: 'hidden',
    probation: 'hidden',
    active: 'full',
    constrained: 'read',
    terminal: 'hidden',
  },
  cases: {
    pre_submit: 'task',
    review: 'limited',
    probation: 'limited',
    active: 'full',
    constrained: 'full',
    terminal: 'read',
  },
  notifications: {
    pre_submit: 'full',
    review: 'full',
    probation: 'full',
    active: 'full',
    constrained: 'full',
    terminal: 'read',
  },
  settings: {
    pre_submit: 'full',
    review: 'full',
    probation: 'full',
    active: 'full',
    constrained: 'full',
    terminal: 'read',
  },
  reseller: {
    pre_submit: 'hidden',
    review: 'hidden',
    probation: 'hidden',
    active: 'full',
    constrained: 'read',
    terminal: 'hidden',
  },
};

export function getPartnerVisibilityBand(
  workspaceStatus: PartnerWorkspaceStatus,
): PartnerVisibilityBand {
  if (workspaceStatus === 'draft' || workspaceStatus === 'email_verified') {
    return 'pre_submit';
  }
  if (
    workspaceStatus === 'submitted'
    || workspaceStatus === 'needs_info'
    || workspaceStatus === 'under_review'
    || workspaceStatus === 'waitlisted'
  ) {
    return 'review';
  }
  if (workspaceStatus === 'approved_probation') {
    return 'probation';
  }
  if (workspaceStatus === 'active') {
    return 'active';
  }
  if (workspaceStatus === 'restricted' || workspaceStatus === 'suspended') {
    return 'constrained';
  }

  return 'terminal';
}

function hasResellerRouteVisibility(state: PartnerPortalState): boolean {
  const resellerEligible = state.primaryLane === 'reseller_api';
  const workspaceAllowsReseller =
    state.workspaceStatus === 'active'
    || state.workspaceStatus === 'restricted'
    || state.workspaceStatus === 'suspended';

  return resellerEligible && workspaceAllowsReseller;
}

function getPartnerBaseRouteVisibility(
  route: PartnerRouteKey,
  state: PartnerPortalState,
): PartnerSectionVisibility {
  const visibilityBand = getPartnerVisibilityBand(state.workspaceStatus);
  return PARTNER_VISIBILITY_MATRIX[route][visibilityBand];
}

export function getPartnerRouteBlockReason(
  route: PartnerRouteKey,
  state: PartnerPortalState,
): PartnerRouteBlockReason {
  const requiredReleaseRing = getPartnerRouteRequiredReleaseRing(route);
  const releaseRingReady = doesPartnerReleaseRingMeetRequirement(
    state.releaseRing,
    requiredReleaseRing,
  );

  if (!releaseRingReady) {
    return 'release_ring';
  }

  if (route === 'reseller' && !hasResellerRouteVisibility(state)) {
    return 'status';
  }

  return getPartnerBaseRouteVisibility(route, state) === 'hidden'
    ? 'status'
    : null;
}

export function getPartnerRouteVisibility(
  route: PartnerRouteKey,
  state: PartnerPortalState,
): PartnerSectionVisibility {
  if (getPartnerRouteBlockReason(route, state) === 'release_ring') {
    return 'hidden';
  }

  let visibility = getPartnerBaseRouteVisibility(route, state);

  if (route === 'reseller' && !hasResellerRouteVisibility(state)) {
    return 'hidden';
  }

  if (
    route === 'finance'
    && visibility === 'full'
    && state.financeReadiness === 'blocked'
  ) {
    visibility = 'read';
  }

  if (
    route === 'compliance'
    && visibility === 'full'
    && state.complianceReadiness === 'evidence_requested'
  ) {
    visibility = 'task';
  }

  if (
    (route === 'codes' || route === 'campaigns' || route === 'integrations')
    && visibility !== 'hidden'
    && (state.governanceState === 'limited' || state.governanceState === 'frozen')
  ) {
    visibility = 'read';
  }

  return visibility;
}

export function isPartnerRouteVisible(
  route: PartnerRouteKey,
  state: PartnerPortalState,
): boolean {
  return getPartnerRouteVisibility(route, state) !== 'hidden';
}

import type { PartnerPortalState } from '@/features/partner-portal-state/lib/portal-state';

export type PartnerCommercialSurface =
  | 'codes'
  | 'campaigns'
  | 'compliance';

export type PartnerCommercialSurfaceMode =
  | 'review'
  | 'starter'
  | 'controlled'
  | 'full'
  | 'read_only';

export type PartnerCapabilityAvailability =
  | 'enabled'
  | 'conditional'
  | 'blocked';

export type PartnerCodeCapabilityKey =
  | 'starter_code'
  | 'additional_codes'
  | 'deep_links'
  | 'qr_bundles'
  | 'vanity_links'
  | 'sub_id_macros';

export type PartnerCampaignCapabilityKey =
  | 'creative_library'
  | 'promo_calendar'
  | 'landing_pages'
  | 'creative_submission'
  | 'approval_comments'
  | 'disclosure_templates';

export type PartnerComplianceCapabilityKey =
  | 'disclosure_attestations'
  | 'approved_sources'
  | 'creative_approvals'
  | 'evidence_uploads'
  | 'postback_readiness'
  | 'support_ownership';

export interface PartnerCapabilityState<TKey extends string> {
  key: TKey;
  availability: PartnerCapabilityAvailability;
}

const CODE_CAPABILITIES: readonly PartnerCodeCapabilityKey[] = [
  'starter_code',
  'additional_codes',
  'deep_links',
  'qr_bundles',
  'vanity_links',
  'sub_id_macros',
];

const CAMPAIGN_CAPABILITIES: readonly PartnerCampaignCapabilityKey[] = [
  'creative_library',
  'promo_calendar',
  'landing_pages',
  'creative_submission',
  'approval_comments',
  'disclosure_templates',
];

const COMPLIANCE_CAPABILITIES: readonly PartnerComplianceCapabilityKey[] = [
  'disclosure_attestations',
  'approved_sources',
  'creative_approvals',
  'evidence_uploads',
  'postback_readiness',
  'support_ownership',
];

function mapCapabilities<TKey extends string>(
  keys: readonly TKey[],
  availabilityMap: Partial<Record<TKey, PartnerCapabilityAvailability>>,
  fallback: PartnerCapabilityAvailability = 'blocked',
): PartnerCapabilityState<TKey>[] {
  return keys.map((key) => ({
    key,
    availability: availabilityMap[key] ?? fallback,
  }));
}

function hasReadOnlyCommercialState(
  surface: PartnerCommercialSurface,
  state: PartnerPortalState,
): boolean {
  if (state.workspaceStatus === 'restricted' || state.workspaceStatus === 'suspended') {
    return true;
  }

  if (
    (surface === 'codes' || surface === 'campaigns')
    && (state.governanceState === 'limited' || state.governanceState === 'frozen')
  ) {
    return true;
  }

  return false;
}

export function getPartnerCommercialSurfaceMode(
  surface: PartnerCommercialSurface,
  state: PartnerPortalState,
): PartnerCommercialSurfaceMode {
  if (hasReadOnlyCommercialState(surface, state)) {
    return 'read_only';
  }

  if (
    state.workspaceStatus === 'draft'
    || state.workspaceStatus === 'email_verified'
    || state.workspaceStatus === 'submitted'
    || state.workspaceStatus === 'needs_info'
    || state.workspaceStatus === 'under_review'
    || state.workspaceStatus === 'waitlisted'
    || !state.primaryLane
  ) {
    return 'review';
  }

  if (state.workspaceStatus === 'approved_probation') {
    return state.primaryLane === 'creator_affiliate' ? 'starter' : 'controlled';
  }

  if (surface === 'compliance' && state.primaryLane === 'creator_affiliate') {
    return 'controlled';
  }

  if (
    (surface === 'codes' || surface === 'campaigns')
    && state.primaryLane === 'reseller_api'
  ) {
    return 'controlled';
  }

  return 'full';
}

export function getPartnerCodeCapabilities(
  state: PartnerPortalState,
): PartnerCapabilityState<PartnerCodeCapabilityKey>[] {
  const mode = getPartnerCommercialSurfaceMode('codes', state);

  if (mode === 'read_only' || mode === 'review') {
    return mapCapabilities(CODE_CAPABILITIES, {});
  }

  if (state.primaryLane === 'creator_affiliate') {
    return mapCapabilities(CODE_CAPABILITIES, {
      starter_code: 'enabled',
      additional_codes: mode === 'full' ? 'enabled' : 'conditional',
      deep_links: 'enabled',
      qr_bundles: mode === 'full' ? 'enabled' : 'conditional',
      vanity_links: mode === 'full' ? 'enabled' : 'conditional',
      sub_id_macros: 'enabled',
    });
  }

  if (state.primaryLane === 'performance_media') {
    return mapCapabilities(CODE_CAPABILITIES, {
      starter_code: mode === 'controlled' ? 'conditional' : 'enabled',
      additional_codes: mode === 'full' ? 'enabled' : 'blocked',
      deep_links: mode === 'full' ? 'enabled' : 'conditional',
      qr_bundles: mode === 'full' ? 'enabled' : 'blocked',
      vanity_links: mode === 'full' ? 'enabled' : 'conditional',
      sub_id_macros: 'enabled',
    });
  }

  return mapCapabilities(CODE_CAPABILITIES, {
    starter_code: mode === 'controlled' ? 'conditional' : 'enabled',
    additional_codes: mode === 'full' ? 'enabled' : 'blocked',
    deep_links: 'conditional',
    qr_bundles: 'blocked',
    vanity_links: mode === 'full' ? 'conditional' : 'blocked',
    sub_id_macros: mode === 'full' ? 'enabled' : 'conditional',
  });
}

export function getPartnerCampaignCapabilities(
  state: PartnerPortalState,
): PartnerCapabilityState<PartnerCampaignCapabilityKey>[] {
  const mode = getPartnerCommercialSurfaceMode('campaigns', state);

  if (mode === 'read_only' || mode === 'review') {
    return mapCapabilities(CAMPAIGN_CAPABILITIES, {});
  }

  if (state.primaryLane === 'creator_affiliate') {
    return mapCapabilities(CAMPAIGN_CAPABILITIES, {
      creative_library: 'enabled',
      promo_calendar: mode === 'full' ? 'enabled' : 'conditional',
      landing_pages: mode === 'full' ? 'enabled' : 'conditional',
      creative_submission: mode === 'full' ? 'enabled' : 'conditional',
      approval_comments: mode === 'full' ? 'enabled' : 'conditional',
      disclosure_templates: 'enabled',
    });
  }

  if (state.primaryLane === 'performance_media') {
    return mapCapabilities(CAMPAIGN_CAPABILITIES, {
      creative_library: 'enabled',
      promo_calendar: mode === 'full' ? 'enabled' : 'conditional',
      landing_pages: mode === 'full' ? 'enabled' : 'conditional',
      creative_submission: 'enabled',
      approval_comments: 'enabled',
      disclosure_templates: 'enabled',
    });
  }

  return mapCapabilities(CAMPAIGN_CAPABILITIES, {
    creative_library: mode === 'full' ? 'enabled' : 'conditional',
    promo_calendar: 'blocked',
    landing_pages: mode === 'full' ? 'conditional' : 'blocked',
    creative_submission: 'conditional',
    approval_comments: 'conditional',
    disclosure_templates: 'enabled',
  });
}

export function getPartnerComplianceCapabilities(
  state: PartnerPortalState,
): PartnerCapabilityState<PartnerComplianceCapabilityKey>[] {
  const mode = getPartnerCommercialSurfaceMode('compliance', state);

  if (mode === 'read_only') {
    return mapCapabilities(COMPLIANCE_CAPABILITIES, {
      evidence_uploads: 'conditional',
    });
  }

  if (mode === 'review') {
    return mapCapabilities(COMPLIANCE_CAPABILITIES, {
      disclosure_attestations: 'conditional',
      approved_sources: 'conditional',
      evidence_uploads: 'conditional',
    });
  }

  if (state.primaryLane === 'creator_affiliate') {
    return mapCapabilities(COMPLIANCE_CAPABILITIES, {
      disclosure_attestations: 'enabled',
      approved_sources: mode === 'controlled' ? 'enabled' : 'conditional',
      creative_approvals: 'conditional',
      evidence_uploads: 'conditional',
      postback_readiness: 'blocked',
      support_ownership: 'blocked',
    });
  }

  if (state.primaryLane === 'performance_media') {
    return mapCapabilities(COMPLIANCE_CAPABILITIES, {
      disclosure_attestations: 'enabled',
      approved_sources: 'enabled',
      creative_approvals: 'enabled',
      evidence_uploads: 'enabled',
      postback_readiness: 'enabled',
      support_ownership: 'blocked',
    });
  }

  return mapCapabilities(COMPLIANCE_CAPABILITIES, {
    disclosure_attestations: 'enabled',
    approved_sources: 'conditional',
    creative_approvals: 'conditional',
    evidence_uploads: 'enabled',
    postback_readiness: mode === 'full' ? 'conditional' : 'blocked',
    support_ownership: 'enabled',
  });
}

import type { PartnerPortalState } from '@/features/partner-portal-state/lib/portal-state';

export type PartnerConversionsSurfaceMode =
  | 'lite'
  | 'full'
  | 'dispute';

export type PartnerIntegrationsSurfaceMode =
  | 'selected'
  | 'technical'
  | 'blocked';

export type PartnerResellerSurfaceMode =
  | 'operational'
  | 'constrained';

export type PartnerOperationalCapabilityAvailability =
  | 'enabled'
  | 'conditional'
  | 'blocked';

export type PartnerConversionsCapabilityKey =
  | 'attribution_events'
  | 'order_visibility'
  | 'customer_scope'
  | 'refund_context'
  | 'dispute_handoffs'
  | 'explainability';

export type PartnerIntegrationsCapabilityKey =
  | 'reporting_tokens'
  | 'postback_credentials'
  | 'webhook_secrets'
  | 'delivery_logs'
  | 'replay_controls'
  | 'storefront_api_keys';

export type PartnerResellerCapabilityKey =
  | 'storefront_scope'
  | 'linked_domains'
  | 'pricebook_preview'
  | 'support_ownership'
  | 'customer_scope'
  | 'technical_health';

export interface PartnerOperationalCapability<TKey extends string> {
  key: TKey;
  availability: PartnerOperationalCapabilityAvailability;
}

const CONVERSIONS_KEYS: readonly PartnerConversionsCapabilityKey[] = [
  'attribution_events',
  'order_visibility',
  'customer_scope',
  'refund_context',
  'dispute_handoffs',
  'explainability',
];

const INTEGRATIONS_KEYS: readonly PartnerIntegrationsCapabilityKey[] = [
  'reporting_tokens',
  'postback_credentials',
  'webhook_secrets',
  'delivery_logs',
  'replay_controls',
  'storefront_api_keys',
];

const RESELLER_KEYS: readonly PartnerResellerCapabilityKey[] = [
  'storefront_scope',
  'linked_domains',
  'pricebook_preview',
  'support_ownership',
  'customer_scope',
  'technical_health',
];

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

export function getPartnerConversionsSurfaceMode(
  state: PartnerPortalState,
): PartnerConversionsSurfaceMode {
  if (state.workspaceStatus === 'approved_probation') {
    return 'lite';
  }

  if (
    state.workspaceStatus === 'restricted'
    || state.workspaceStatus === 'suspended'
    || state.governanceState === 'limited'
    || state.financeReadiness === 'blocked'
  ) {
    return 'dispute';
  }

  return 'full';
}

export function getPartnerIntegrationsSurfaceMode(
  state: PartnerPortalState,
): PartnerIntegrationsSurfaceMode {
  if (
    state.workspaceStatus === 'restricted'
    || state.workspaceStatus === 'suspended'
    || state.technicalReadiness === 'blocked'
    || state.governanceState === 'limited'
  ) {
    return 'blocked';
  }

  if (state.primaryLane === 'creator_affiliate') {
    return 'selected';
  }

  return 'technical';
}

export function getPartnerResellerSurfaceMode(
  state: PartnerPortalState,
): PartnerResellerSurfaceMode {
  if (
    state.workspaceStatus === 'restricted'
    || state.workspaceStatus === 'suspended'
    || state.governanceState === 'limited'
  ) {
    return 'constrained';
  }

  return 'operational';
}

export function getPartnerConversionsCapabilities(
  state: PartnerPortalState,
): PartnerOperationalCapability<PartnerConversionsCapabilityKey>[] {
  const mode = getPartnerConversionsSurfaceMode(state);
  const customerScope =
    state.primaryLane === 'creator_affiliate' ? 'conditional' : 'enabled';

  if (mode === 'lite') {
    return mapCapabilities(CONVERSIONS_KEYS, {
      attribution_events: 'enabled',
      order_visibility: 'enabled',
      customer_scope: customerScope,
      refund_context: 'conditional',
      dispute_handoffs: 'conditional',
      explainability: 'enabled',
    });
  }

  if (mode === 'dispute') {
    return mapCapabilities(CONVERSIONS_KEYS, {
      attribution_events: 'enabled',
      order_visibility: 'enabled',
      customer_scope: customerScope,
      refund_context: 'enabled',
      dispute_handoffs: 'enabled',
      explainability: 'enabled',
    });
  }

  return mapCapabilities(CONVERSIONS_KEYS, {
    attribution_events: 'enabled',
    order_visibility: 'enabled',
    customer_scope: customerScope,
    refund_context: 'enabled',
    dispute_handoffs: 'enabled',
    explainability: 'enabled',
  });
}

export function getPartnerIntegrationsCapabilities(
  state: PartnerPortalState,
): PartnerOperationalCapability<PartnerIntegrationsCapabilityKey>[] {
  const mode = getPartnerIntegrationsSurfaceMode(state);

  if (mode === 'selected') {
    return mapCapabilities(INTEGRATIONS_KEYS, {
      reporting_tokens: 'enabled',
      postback_credentials: 'blocked',
      webhook_secrets: 'conditional',
      delivery_logs: 'conditional',
      replay_controls: 'blocked',
      storefront_api_keys: 'blocked',
    });
  }

  if (mode === 'blocked') {
    return mapCapabilities(INTEGRATIONS_KEYS, {
      reporting_tokens: 'conditional',
      postback_credentials: state.primaryLane === 'performance_media'
        ? 'conditional'
        : 'blocked',
      webhook_secrets: 'conditional',
      delivery_logs: 'enabled',
      replay_controls: 'blocked',
      storefront_api_keys: state.primaryLane === 'reseller_api'
        ? 'conditional'
        : 'blocked',
    });
  }

  return mapCapabilities(INTEGRATIONS_KEYS, {
    reporting_tokens: 'enabled',
    postback_credentials: state.primaryLane === 'performance_media'
      ? 'enabled'
      : 'blocked',
    webhook_secrets: 'enabled',
    delivery_logs: 'enabled',
    replay_controls: 'conditional',
    storefront_api_keys: state.primaryLane === 'reseller_api'
      ? 'enabled'
      : 'blocked',
  });
}

export function getPartnerResellerCapabilities(
  state: PartnerPortalState,
): PartnerOperationalCapability<PartnerResellerCapabilityKey>[] {
  const mode = getPartnerResellerSurfaceMode(state);

  if (mode === 'constrained') {
    return mapCapabilities(RESELLER_KEYS, {
      storefront_scope: 'enabled',
      linked_domains: 'conditional',
      pricebook_preview: 'enabled',
      support_ownership: 'enabled',
      customer_scope: 'conditional',
      technical_health: 'conditional',
    });
  }

  return mapCapabilities(RESELLER_KEYS, {
    storefront_scope: 'enabled',
    linked_domains: 'enabled',
    pricebook_preview: 'enabled',
    support_ownership: 'enabled',
    customer_scope: 'enabled',
    technical_health: 'enabled',
  });
}

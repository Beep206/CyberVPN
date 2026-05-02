export type ProductAnalyticsScalar = string | number | boolean | null;
export type ProductAnalyticsProperties = Record<string, ProductAnalyticsScalar>;

export type ProductAnalyticsEventName =
  | 'checkout_started'
  | 'checkout_step_viewed'
  | 'checkout_step_completed'
  | 'checkout_payment_submitted'
  | 'onboarding_started'
  | 'onboarding_step_completed'
  | 'partner_dashboard_viewed'
  | 'feature_flag_evaluated'
  | 'experiment_exposure_recorded'
  | 'checkout_payment_captured'
  | 'partner_user_activated'
  | 'subscription_activated';

export type ProductAnalyticsSourceClass = 'frontend_sdk' | 'server_side' | 'nats_bridge';
export type ProductFeatureFlagEvaluationSource = 'fallback' | 'server_evaluated' | 'disabled';

type ProductAnalyticsEventDefinition = {
  owner: string;
  sourceClass: ProductAnalyticsSourceClass;
  allowedProperties: readonly string[];
};

export const PRODUCT_ANALYTICS_EVENT_DEFINITIONS: Record<
  ProductAnalyticsEventName,
  ProductAnalyticsEventDefinition
> = {
  checkout_started: {
    owner: 'growth-platform',
    sourceClass: 'frontend_sdk',
    allowedProperties: [
      'checkout_surface',
      'locale',
      'path',
      'pricebook_key',
      'route_group',
      'sale_channel',
      'storefront_key',
    ],
  },
  checkout_step_viewed: {
    owner: 'growth-platform',
    sourceClass: 'frontend_sdk',
    allowedProperties: [
      'checkout_surface',
      'locale',
      'path',
      'route_group',
      'step',
      'storefront_key',
    ],
  },
  checkout_step_completed: {
    owner: 'growth-platform',
    sourceClass: 'frontend_sdk',
    allowedProperties: [
      'checkout_surface',
      'locale',
      'path',
      'route_group',
      'step',
      'storefront_key',
    ],
  },
  checkout_payment_submitted: {
    owner: 'billing',
    sourceClass: 'frontend_sdk',
    allowedProperties: [
      'checkout_surface',
      'currency_code',
      'flow',
      'locale',
      'offer_key',
      'path',
      'pricebook_key',
      'route_group',
      'sale_channel',
      'storefront_key',
    ],
  },
  onboarding_started: {
    owner: 'growth-platform',
    sourceClass: 'frontend_sdk',
    allowedProperties: [
      'application_status',
      'locale',
      'path',
      'route_group',
      'surface',
      'workspace_status',
    ],
  },
  onboarding_step_completed: {
    owner: 'growth-platform',
    sourceClass: 'frontend_sdk',
    allowedProperties: [
      'application_status',
      'locale',
      'path',
      'route_group',
      'stage',
      'surface',
      'workspace_status',
    ],
  },
  partner_dashboard_viewed: {
    owner: 'growth-platform',
    sourceClass: 'frontend_sdk',
    allowedProperties: ['locale', 'path', 'release_ring', 'route_group', 'surface', 'workspace_status'],
  },
  feature_flag_evaluated: {
    owner: 'growth-platform',
    sourceClass: 'server_side',
    allowedProperties: ['evaluation_source', 'flag_key', 'flag_value', 'locale', 'path', 'route_group'],
  },
  experiment_exposure_recorded: {
    owner: 'growth-platform',
    sourceClass: 'server_side',
    allowedProperties: ['experiment_key', 'locale', 'path', 'route_group', 'variant'],
  },
  checkout_payment_captured: {
    owner: 'billing',
    sourceClass: 'nats_bridge',
    allowedProperties: [
      'occurred_at',
      'order_id',
      'settlement_status',
      'source_class',
      'source_event_key',
      'source_event_type',
      'source_event_version',
      'source_flow',
    ],
  },
  partner_user_activated: {
    owner: 'partner-admin',
    sourceClass: 'nats_bridge',
    allowedProperties: [
      'entitlement_grant_id',
      'free_days',
      'invite_code_id',
      'occurred_at',
      'source_class',
      'source_event_key',
      'source_event_type',
      'source_event_version',
      'source_flow',
    ],
  },
  subscription_activated: {
    owner: 'billing',
    sourceClass: 'nats_bridge',
    allowedProperties: [
      'entitlement_grant_id',
      'grant_status',
      'occurred_at',
      'source_class',
      'source_event_key',
      'source_event_type',
      'source_event_version',
      'source_type',
    ],
  },
};

export type ProductFeatureFlagKey =
  | 'partner_portal_dashboard_spotlight_v1'
  | 'partner_portal_realtime_workspace_feed_v1';

export type ProductFeatureFlagSnapshot = Record<ProductFeatureFlagKey, boolean>;

export type ProductFeatureFlagContract = {
  owner: string;
  purpose: string;
  createdAt: string;
  expectedRemovalDate: string;
  allowedContexts: 'server' | 'client' | 'both';
  fallbackBehavior: 'default_off';
  blastRadius: 'partner_dashboard';
  cleanupRule: string;
  documentationLink: string;
};

export const PRODUCT_FEATURE_FLAG_CONTRACTS: Record<
  ProductFeatureFlagKey,
  ProductFeatureFlagContract
> = {
  partner_portal_dashboard_spotlight_v1: {
    owner: 'growth-platform',
    purpose: 'Gate partner dashboard spotlight-card UX variants behind a typed product flag wrapper.',
    createdAt: '2026-04-22',
    expectedRemovalDate: '2026-08-31',
    allowedContexts: 'both',
    fallbackBehavior: 'default_off',
    blastRadius: 'partner_dashboard',
    cleanupRule: 'Remove after spotlight-card rollout converges or the experiment is retired.',
    documentationLink: '/docs/growth-platform/posthog-feature-flag-governance.md',
  },
  partner_portal_realtime_workspace_feed_v1: {
    owner: 'growth-platform',
    purpose: 'Control the product-facing realtime workspace feed UX entry without touching transport safety controls.',
    createdAt: '2026-04-22',
    expectedRemovalDate: '2026-09-30',
    allowedContexts: 'both',
    fallbackBehavior: 'default_off',
    blastRadius: 'partner_dashboard',
    cleanupRule: 'Remove when realtime workspace feed becomes the default dashboard behavior.',
    documentationLink: '/docs/growth-platform/posthog-feature-flag-governance.md',
  },
};

export interface ProductFeatureFlagBootstrap {
  distinctId: string | null;
  evaluatedAt: string;
  evaluationSource: ProductFeatureFlagEvaluationSource;
  flags: ProductFeatureFlagSnapshot;
}

export interface ProductAnalyticsCaptureInput {
  distinctId: string;
  event: ProductAnalyticsEventName;
  properties?: ProductAnalyticsProperties;
}

function sanitizeToken(value: string, maxLength: number): string | null {
  const normalized = value
    .trim()
    .replace(/[^a-zA-Z0-9._:/-]+/g, '_')
    .slice(0, maxLength);

  return normalized || null;
}

function sanitizeText(value: string, maxLength: number): string | null {
  const normalized = value.trim().replace(/\s+/g, ' ').slice(0, maxLength);
  return normalized || null;
}

function sanitizeScalar(value: unknown): ProductAnalyticsScalar | undefined {
  if (typeof value === 'boolean' || typeof value === 'number') {
    return Number.isFinite(value as number) || typeof value === 'boolean'
      ? (value as ProductAnalyticsScalar)
      : undefined;
  }

  if (value === null) {
    return null;
  }

  if (typeof value !== 'string') {
    return undefined;
  }

  return sanitizeText(value, 160) ?? undefined;
}

export function resolveProductDistinctId(value: unknown): string | null {
  if (typeof value !== 'string') {
    return null;
  }

  return sanitizeToken(value, 128);
}

export function buildDefaultFeatureFlagBootstrap(
  distinctId: string | null = null,
  evaluationSource: ProductFeatureFlagEvaluationSource = 'fallback',
): ProductFeatureFlagBootstrap {
  return {
    distinctId,
    evaluatedAt: new Date().toISOString(),
    evaluationSource,
    flags: {
      partner_portal_dashboard_spotlight_v1: false,
      partner_portal_realtime_workspace_feed_v1: false,
    },
  };
}

export function coerceProductFeatureFlagSnapshot(
  value: Record<string, unknown> | null | undefined,
): ProductFeatureFlagSnapshot {
  const fallback = buildDefaultFeatureFlagBootstrap().flags;
  if (!value) {
    return fallback;
  }

  return {
    partner_portal_dashboard_spotlight_v1:
      typeof value.partner_portal_dashboard_spotlight_v1 === 'boolean'
        ? value.partner_portal_dashboard_spotlight_v1
        : fallback.partner_portal_dashboard_spotlight_v1,
    partner_portal_realtime_workspace_feed_v1:
      typeof value.partner_portal_realtime_workspace_feed_v1 === 'boolean'
        ? value.partner_portal_realtime_workspace_feed_v1
        : fallback.partner_portal_realtime_workspace_feed_v1,
  };
}

export function sanitizeProductAnalyticsProperties(
  event: ProductAnalyticsEventName,
  properties: Record<string, unknown> | null | undefined,
): ProductAnalyticsProperties | undefined {
  if (!properties) {
    return undefined;
  }

  const definition = PRODUCT_ANALYTICS_EVENT_DEFINITIONS[event];
  const entries = definition.allowedProperties.flatMap((propertyKey) => {
    const sanitizedValue = sanitizeScalar(properties[propertyKey]);
    if (sanitizedValue === undefined) {
      return [];
    }

    return [[propertyKey, sanitizedValue] as const];
  });

  if (entries.length === 0) {
    return undefined;
  }

  return Object.fromEntries(entries);
}

export function sanitizeProductAnalyticsCapture(
  input: {
    distinctId?: unknown;
    event?: unknown;
    properties?: Record<string, unknown> | null;
  } | null
): ProductAnalyticsCaptureInput | null {
  if (!input || typeof input.event !== 'string' || !(input.event in PRODUCT_ANALYTICS_EVENT_DEFINITIONS)) {
    return null;
  }

  const distinctId = resolveProductDistinctId(input.distinctId);
  if (!distinctId) {
    return null;
  }

  const event = input.event as ProductAnalyticsEventName;

  return {
    distinctId,
    event,
    properties: sanitizeProductAnalyticsProperties(event, input.properties),
  };
}

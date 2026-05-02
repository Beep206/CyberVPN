import { PostHog } from 'posthog-node';
import {
  buildDefaultFeatureFlagBootstrap,
  coerceProductFeatureFlagSnapshot,
  resolveProductDistinctId,
  sanitizeProductAnalyticsCapture,
  type ProductAnalyticsCaptureInput,
  type ProductFeatureFlagBootstrap,
} from './contracts';

type PostHogServerConfig = {
  host: string;
  personalApiKey?: string;
  projectApiKey: string;
};

export type CapturePartnerProductEventResult =
  | { status: 'captured' }
  | { reason: string; status: 'disabled' | 'rejected' };

function getPostHogServerConfig(): PostHogServerConfig | null {
  const projectApiKey = process.env.POSTHOG_PROJECT_API_KEY?.trim()
    || process.env.NEXT_PUBLIC_POSTHOG_TOKEN?.trim();
  const host = process.env.POSTHOG_HOST?.trim()
    || process.env.NEXT_PUBLIC_POSTHOG_HOST?.trim();

  if (!projectApiKey || !host) {
    return null;
  }

  const personalApiKey = process.env.POSTHOG_PERSONAL_API_KEY?.trim() || undefined;

  return {
    host,
    personalApiKey,
    projectApiKey,
  };
}

async function withPostHogClient<T>(
  config: PostHogServerConfig,
  handler: (client: PostHog) => Promise<T>,
): Promise<T> {
  const client = new PostHog(config.projectApiKey, {
    disableGeoip: true,
    featureFlagsPollingInterval: 300000,
    flushAt: 1,
    flushInterval: 0,
    host: config.host,
    personalApiKey: config.personalApiKey,
  });

  try {
    return await handler(client);
  } finally {
    await client.shutdown();
  }
}

export async function capturePartnerProductEvent(
  input: ProductAnalyticsCaptureInput | null,
): Promise<CapturePartnerProductEventResult> {
  const capture = sanitizeProductAnalyticsCapture(input);
  if (!capture) {
    return { reason: 'invalid_capture', status: 'rejected' };
  }

  const config = getPostHogServerConfig();
  if (!config) {
    return { reason: 'missing_server_config', status: 'disabled' };
  }

  await withPostHogClient(config, async (client) => {
    client.capture({
      distinctId: capture.distinctId,
      event: capture.event,
      properties: capture.properties,
    });
  });

  return { status: 'captured' };
}

export async function buildPartnerProductIntelligenceBootstrap(input?: {
  distinctId?: string | null;
}): Promise<ProductFeatureFlagBootstrap> {
  const distinctId = resolveProductDistinctId(input?.distinctId);
  const config = getPostHogServerConfig();

  if (!config) {
    return buildDefaultFeatureFlagBootstrap(distinctId, 'disabled');
  }

  if (!distinctId) {
    return buildDefaultFeatureFlagBootstrap(null, 'fallback');
  }

  try {
    const flags = await withPostHogClient(config, async (client) => client.getAllFlags(distinctId));
    return {
      distinctId,
      evaluatedAt: new Date().toISOString(),
      evaluationSource: 'server_evaluated',
      flags: coerceProductFeatureFlagSnapshot(flags as Record<string, unknown>),
    };
  } catch {
    return buildDefaultFeatureFlagBootstrap(distinctId, 'fallback');
  }
}

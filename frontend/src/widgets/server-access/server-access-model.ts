import type { components } from '@/lib/api/generated/types';

export type RawServer = components['schemas']['ServerResponse'];
export type ServerStats = components['schemas']['ServerStatsResponse'];
export type CurrentServiceState = components['schemas']['CurrentServiceStateResponse'];
export type ProfileResponse = components['schemas']['ProfileResponse'];
export type UserConfig = components['schemas']['RemnawaveSubscriptionConfigResponse'];

export type ConfigAvailability =
  | 'missing_config'
  | 'missing_profile'
  | 'missing_service'
  | 'not_found'
  | 'ready';

export type ConfigLinkKind = 'config' | 'link' | 'shadowSocks' | 'subscription';

export type ConfigLink = {
  id: string;
  kind: ConfigLinkKind;
  label: string;
  value: string;
};

export type ConfigDeliveryBundle = {
  configFile: ConfigLink | null;
  fileName: string;
  qrLink: ConfigLink | null;
  rawConfigLink: ConfigLink | null;
  subscriptionLink: ConfigLink | null;
};

export type ServerAccessSummary = {
  connected: number;
  countries: string[];
  disabled: number;
  online: number;
  protocols: string[];
  total: number;
};

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'] as const;
const ACTIVE_STATUS_VALUES = new Set(['active', 'ready', 'provisioned', 'enabled']);

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

function normalizeLabel(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values));
}

function isStringRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function payloadString(payload: Record<string, unknown>, keys: string[]): string | null {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
  }

  return null;
}

function payloadStringArray(payload: Record<string, unknown>, keys: string[]): string[] {
  for (const key of keys) {
    const value = payload[key];
    if (Array.isArray(value)) {
      return value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim()));
    }
  }

  return [];
}

function payloadStringMap(payload: Record<string, unknown>, keys: string[]): Record<string, string> {
  for (const key of keys) {
    const value = payload[key];
    if (isStringRecord(value)) {
      return Object.fromEntries(
        Object.entries(value).filter((entry): entry is [string, string] => {
          const [, item] = entry;
          return typeof item === 'string' && Boolean(item.trim());
        }),
      );
    }
  }

  return {};
}

export function clampPercentage(value: number | null | undefined): number {
  if (!isFiniteNumber(value)) {
    return 0;
  }

  return Math.min(100, Math.max(0, Math.round(value)));
}

export function formatBytes(
  bytes: number | null | undefined,
  locale = 'en-EN',
): string {
  if (!isFiniteNumber(bytes) || bytes <= 0) {
    return `0 ${BYTE_UNITS[0]}`;
  }

  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    BYTE_UNITS.length - 1,
  );
  const value = bytes / 1024 ** exponent;

  try {
    const formatted = new Intl.NumberFormat(locale, {
      maximumFractionDigits: value >= 10 ? 0 : 1,
    }).format(value);

    return `${formatted} ${BYTE_UNITS[exponent]}`;
  } catch {
    return `${value.toFixed(value >= 10 ? 0 : 1)} ${BYTE_UNITS[exponent]}`;
  }
}

export function formatDateTime(
  value: string | null | undefined,
  locale = 'en-EN',
): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  try {
    return new Intl.DateTimeFormat(locale, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  } catch {
    return date.toISOString();
  }
}

export function getServerLoad(server: RawServer): number {
  return clampPercentage(server.users_online);
}

export function getServerLocation(server: RawServer): string {
  return normalizeLabel(server.country_code) ?? server.address;
}

export function getServerProtocol(server: RawServer): string {
  return normalizeLabel(server.vpn_protocol)?.toUpperCase() ?? 'AUTO';
}

export function isUsableServer(server: RawServer): boolean {
  return server.status === 'online' && server.is_connected && !server.is_disabled;
}

export function rankServers(servers: RawServer[]): RawServer[] {
  return [...servers].sort((first, second) => {
    const usableDelta = Number(isUsableServer(second)) - Number(isUsableServer(first));
    if (usableDelta !== 0) {
      return usableDelta;
    }

    const loadDelta = getServerLoad(first) - getServerLoad(second);
    if (loadDelta !== 0) {
      return loadDelta;
    }

    const trafficDelta = first.traffic_used_bytes - second.traffic_used_bytes;
    if (trafficDelta !== 0) {
      return trafficDelta;
    }

    return first.name.localeCompare(second.name);
  });
}

export function getRecommendedServer(servers: RawServer[]): RawServer | null {
  return rankServers(servers)[0] ?? null;
}

export function summarizeServers(servers: RawServer[]): ServerAccessSummary {
  const countries = unique(
    servers
      .map((server) => normalizeLabel(server.country_code))
      .filter((country): country is string => Boolean(country)),
  ).sort();
  const protocols = unique(
    servers
      .map((server) => normalizeLabel(server.vpn_protocol)?.toUpperCase())
      .filter((protocol): protocol is string => Boolean(protocol)),
  ).sort();

  return {
    connected: servers.filter((server) => server.is_connected).length,
    countries,
    disabled: servers.filter((server) => server.is_disabled).length,
    online: servers.filter((server) => server.status === 'online').length,
    protocols,
    total: servers.length,
  };
}

export function getConfigAvailability({
  config,
  profile,
  serviceState,
}: {
  config?: UserConfig | null;
  profile?: ProfileResponse | null;
  serviceState?: CurrentServiceState | null;
}): ConfigAvailability {
  if (!profile?.id) {
    return 'missing_profile';
  }

  if (config?.isFound === false) {
    return 'not_found';
  }

  const links = extractConfigLinks(config, serviceState);
  const rawConfigReady = Boolean(config?.config.trim());
  if (rawConfigReady || links.length > 0) {
    return 'ready';
  }

  if (
    !serviceState?.service_identity ||
    !serviceState.provisioning_profile ||
    !serviceState.device_credential ||
    !serviceState.access_delivery_channel
  ) {
    return 'missing_service';
  }

  return 'missing_config';
}

export function extractConfigLinks(
  config: UserConfig | null | undefined,
  serviceState?: CurrentServiceState | null,
): ConfigLink[] {
  const links: ConfigLink[] = [];
  const addLink = (link: ConfigLink) => {
    if (!link.value.trim() || links.some((existing) => existing.value === link.value)) {
      return;
    }

    links.push(link);
  };

  if (config?.subscriptionUrl) {
    addLink({
      id: 'subscription-url',
      kind: 'subscription',
      label: 'Subscription URL',
      value: config.subscriptionUrl,
    });
  }

  const payload = serviceState?.access_delivery_channel?.delivery_payload;

  if (isStringRecord(payload)) {
    const subscriptionUrl = payloadString(payload, [
      'subscription_url',
      'subscriptionUrl',
      'subscription_uri',
      'subscriptionUri',
      'delivery_url',
      'deliveryUrl',
    ]);

    if (subscriptionUrl) {
      addLink({
        id: 'delivery-subscription-url',
        kind: 'subscription',
        label: 'Subscription URL',
        value: subscriptionUrl,
      });
    }
  }

  config?.links?.forEach((value, index) => {
    addLink({
      id: `link-${index}`,
      kind: 'link',
      label: `Connection link ${index + 1}`,
      value,
    });
  });

  if (isStringRecord(payload)) {
    payloadStringArray(payload, ['links', 'connection_links', 'connectionLinks']).forEach(
      (value, index) => {
        addLink({
          id: `delivery-link-${index}`,
          kind: 'link',
          label: `Connection link ${index + 1}`,
          value,
        });
      },
    );
  }

  Object.entries(config?.ssConfLinks ?? {}).forEach(([label, value], index) => {
    addLink({
      id: `ss-${index}`,
      kind: 'shadowSocks',
      label: normalizeLabel(label) ?? `Shadowsocks ${index + 1}`,
      value,
    });
  });

  if (isStringRecord(payload)) {
    Object.entries(payloadStringMap(payload, ['ssConfLinks', 'ss_conf_links'])).forEach(
      ([label, value], index) => {
        addLink({
          id: `delivery-ss-${index}`,
          kind: 'shadowSocks',
          label: normalizeLabel(label) ?? `Shadowsocks ${index + 1}`,
          value,
        });
      },
    );
  }

  if (isStringRecord(payload)) {
    const connectionUri = payloadString(payload, [
      'connection_uri',
      'connectionUri',
      'client_uri',
      'clientUri',
      'vless_uri',
      'vlessUri',
    ]);

    if (connectionUri) {
      addLink({
        id: 'delivery-connection-uri',
        kind: 'link',
        label: 'Connection link',
        value: connectionUri,
      });
    }
  }

  if (config?.config.trim()) {
    addLink({
      id: 'raw-config',
      kind: 'config',
      label: 'Raw config',
      value: config.config,
    });
  }

  if (isStringRecord(payload)) {
    const rawConfig = payloadString(payload, [
      'config',
      'raw_config',
      'rawConfig',
      'client_config',
      'clientConfig',
      'config_file',
      'configFile',
    ]);

    if (rawConfig) {
      addLink({
        id: 'delivery-raw-config',
        kind: 'config',
        label: 'Raw config',
        value: rawConfig,
      });
    }
  }

  return links;
}

export function getConfigDeliveryBundle(links: ConfigLink[]): ConfigDeliveryBundle {
  const subscriptionLink = links.find((link) => link.kind === 'subscription') ?? null;
  const rawConfigLink = links.find((link) => link.kind === 'config') ?? null;
  const primaryLink = subscriptionLink ?? links[0] ?? null;
  const configFile =
    rawConfigLink ??
    links.find((link) => link.kind === 'link') ??
    subscriptionLink ??
    primaryLink ??
    null;

  return {
    configFile,
    fileName: 'cybervpn-access-config.txt',
    qrLink: subscriptionLink ?? primaryLink ?? configFile,
    rawConfigLink,
    subscriptionLink,
  };
}

export function maskConfigValue(value: string): string {
  const normalized = value.trim();

  if (!normalized) {
    return '********';
  }

  const schemeMatch = normalized.match(/^([a-z][a-z0-9+.-]*:\/\/)/i);
  if (schemeMatch && !/^https?:\/\//i.test(normalized)) {
    return `${schemeMatch[1]}...${normalized.slice(-6)}`;
  }

  try {
    const url = new URL(normalized);
    return `${url.protocol}//${url.host}/...`;
  } catch {
    if (normalized.length <= 12) {
      return '********';
    }

    return `${normalized.slice(0, 4)}...${normalized.slice(-4)}`;
  }
}

export function formatServiceStatus(
  value: string | null | undefined,
  fallback: string,
): string {
  const normalized = normalizeLabel(value);

  if (!normalized) {
    return fallback;
  }

  return normalized.replace(/[_-]+/g, ' ').toUpperCase();
}

export function isServiceStateActive(serviceState: CurrentServiceState | null | undefined): boolean {
  const identityStatus = serviceState?.service_identity?.identity_status;
  const credentialStatus = serviceState?.device_credential?.credential_status;
  const channelStatus = serviceState?.access_delivery_channel?.channel_status;

  return [identityStatus, credentialStatus, channelStatus].every((value) =>
    ACTIVE_STATUS_VALUES.has(String(value ?? '').toLowerCase()),
  );
}

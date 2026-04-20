import type { ProfileGroup, ProxyNode, Subscription } from "../../../shared/api/ipc";

export type DashboardProfileCollectionSource = "group" | "subscription" | "manual";
export type DashboardLatencyTier = "excellent" | "fast" | "stable" | "long" | "unknown";

export interface DashboardProfileCollection {
  key: string;
  source: DashboardProfileCollectionSource;
  sourceId: string | null;
  label: string;
  proxyCount: number;
  protocols: string[];
  updatedAt: number | null;
  proxies: ProxyNode[];
}

interface ResolveDashboardSelectionOptions {
  selectedCollectionKey: string | null;
  selectedProxyId: string | null;
  persistedProxyId: string | null;
}

export interface DashboardSmartRouteOptions {
  favoriteProfileIds?: ReadonlySet<string>;
  lastStableProfileId?: string | null;
  activeProfileId?: string | null;
}

export interface DashboardScoredProxy {
  proxy: ProxyNode;
  score: number;
}

export type DashboardSmartRouteSignalKind =
  | "latency"
  | "favorite"
  | "stable"
  | "active"
  | "relay"
  | "fallback";

export type DashboardSmartRouteSummaryKey =
  | "dashboard.smartRouteReasonTrusted"
  | "dashboard.smartRouteReasonStable"
  | "dashboard.smartRouteReasonPreferred"
  | "dashboard.smartRouteReasonLive"
  | "dashboard.smartRouteReasonRelay"
  | "dashboard.smartRouteReasonMeasured"
  | "dashboard.smartRouteReasonFallback";

export interface DashboardSmartRouteSignal {
  kind: DashboardSmartRouteSignalKind;
  active: boolean;
  weight: number;
}

export interface DashboardSmartRouteExplanation {
  score: number;
  latencyTier: DashboardLatencyTier;
  regionLabel: string;
  summaryKey: DashboardSmartRouteSummaryKey;
  signals: DashboardSmartRouteSignal[];
}

export interface DashboardRegionCluster {
  key: string;
  label: string;
  proxyCount: number;
  favoriteCount: number;
  bestLatency: number | null;
  measuredCount: number;
  dominantProtocol: string | null;
}

const COUNTRY_CODE_LABELS: Record<string, string> = {
  ae: "UAE",
  am: "Armenia",
  at: "Austria",
  au: "Australia",
  be: "Belgium",
  bg: "Bulgaria",
  br: "Brazil",
  ca: "Canada",
  ch: "Switzerland",
  cz: "Czechia",
  de: "Germany",
  es: "Spain",
  fi: "Finland",
  fr: "France",
  gb: "United Kingdom",
  hk: "Hong Kong",
  hu: "Hungary",
  id: "Indonesia",
  ie: "Ireland",
  il: "Israel",
  in: "India",
  it: "Italy",
  jp: "Japan",
  kz: "Kazakhstan",
  lt: "Lithuania",
  lv: "Latvia",
  md: "Moldova",
  nl: "Netherlands",
  no: "Norway",
  pl: "Poland",
  pt: "Portugal",
  ro: "Romania",
  rs: "Serbia",
  ru: "Russia",
  se: "Sweden",
  sg: "Singapore",
  tr: "Turkey",
  ua: "Ukraine",
  uk: "United Kingdom",
  us: "United States",
};

const REGION_ALIAS_COUNTRY_CODES: Record<string, string> = {
  amsterdam: "nl",
  berlin: "de",
  bucharest: "ro",
  chicago: "us",
  dallas: "us",
  frankfurt: "de",
  helsinki: "fi",
  istanbul: "tr",
  kiev: "ua",
  kyiv: "ua",
  lisbon: "pt",
  london: "gb",
  losangeles: "us",
  madrid: "es",
  melbourne: "au",
  miami: "us",
  milan: "it",
  moscow: "ru",
  newyork: "us",
  paris: "fr",
  prague: "cz",
  rome: "it",
  sanfrancisco: "us",
  seattle: "us",
  seoul: "kr",
  singapore: "sg",
  stockholm: "se",
  sydney: "au",
  tokyo: "jp",
  toronto: "ca",
  vienna: "at",
  warsaw: "pl",
};

const REGION_STOPWORDS = new Set([
  "best",
  "core",
  "direct",
  "edge",
  "exit",
  "fast",
  "free",
  "grpc",
  "http",
  "https",
  "manual",
  "node",
  "premium",
  "proxy",
  "reality",
  "relay",
  "route",
  "secure",
  "server",
  "session",
  "stack",
  "tcp",
  "tls",
  "trojan",
  "udp",
  "vless",
  "vmess",
  "vpn",
  "wg",
  "wireguard",
  "ws",
  "xray",
]);

export function hasMeasuredLatency(ping?: number | null): ping is number {
  return typeof ping === "number" && ping > 0;
}

function compareOptionalLatency(a?: number | null, b?: number | null) {
  if (hasMeasuredLatency(a) && hasMeasuredLatency(b)) {
    return a - b;
  }

  if (hasMeasuredLatency(a)) {
    return -1;
  }

  if (hasMeasuredLatency(b)) {
    return 1;
  }

  return 0;
}

function sortCollectionProxies(a: ProxyNode, b: ProxyNode) {
  const latencyCompare = compareOptionalLatency(a.ping, b.ping);
  if (latencyCompare !== 0) {
    return latencyCompare;
  }

  return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
}

function normalizeProtocol(protocol: string) {
  return protocol.trim().toUpperCase();
}

function normalizeHeuristicToken(token: string) {
  return token.replace(/\d+/g, "").replace(/[^a-z]/gi, "").toLowerCase();
}

function splitHeuristicTokens(value: string) {
  return value
    .split(/[\s._:-]+/)
    .map(normalizeHeuristicToken)
    .filter(Boolean);
}

function isIpv4Host(host: string) {
  return /^\d{1,3}(?:\.\d{1,3}){3}$/.test(host.trim());
}

function inferCountryCodeFromTokens(tokens: string[]) {
  for (const token of tokens) {
    if (COUNTRY_CODE_LABELS[token]) {
      return token;
    }
  }

  for (const token of tokens) {
    const aliasCountryCode = REGION_ALIAS_COUNTRY_CODES[token];

    if (aliasCountryCode) {
      return aliasCountryCode;
    }
  }

  return null;
}

function inferRegionFromTokens(tokens: string[]) {
  for (const token of tokens) {
    const countryLabel = COUNTRY_CODE_LABELS[token];

    if (countryLabel) {
      return countryLabel;
    }
  }

  for (const token of tokens) {
    if (REGION_STOPWORDS.has(token) || token.length < 4) {
      continue;
    }

    return token.charAt(0).toUpperCase() + token.slice(1);
  }

  return null;
}

function countryCodeToFlagEmoji(countryCode: string) {
  const normalized = countryCode.trim().toUpperCase();

  if (!/^[A-Z]{2}$/.test(normalized)) {
    return "🌐";
  }

  return String.fromCodePoint(
    ...normalized.split("").map((char) => 0x1f1e6 + char.charCodeAt(0) - 65)
  );
}

function dominantProtocol(proxies: ProxyNode[]) {
  const counts = new Map<string, number>();

  for (const proxy of proxies) {
    const protocol = normalizeProtocol(proxy.protocol);
    counts.set(protocol, (counts.get(protocol) ?? 0) + 1);
  }

  return Array.from(counts.entries()).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))[0]?.[0] ?? null;
}

function latencyScore(ping?: number | null) {
  if (!hasMeasuredLatency(ping)) {
    return -140;
  }

  const clamped = Math.min(ping, 320);
  return 320 - clamped;
}

function reliabilityScore(proxy: ProxyNode, options: DashboardSmartRouteOptions) {
  let score = 0;

  if (options.favoriteProfileIds?.has(proxy.id)) {
    score += 60;
  }

  if (options.lastStableProfileId === proxy.id) {
    score += 90;
  }

  if (options.activeProfileId === proxy.id) {
    score += 24;
  }

  if (proxy.nextHopId) {
    score -= 16;
  }

  return score;
}

export function sortDashboardVisibleProxies(
  proxies: ProxyNode[],
  favoriteProfileIds: ReadonlySet<string>
) {
  return [...proxies].sort((a, b) => {
    const aIsFavorite = favoriteProfileIds.has(a.id);
    const bIsFavorite = favoriteProfileIds.has(b.id);

    if (aIsFavorite !== bIsFavorite) {
      return aIsFavorite ? -1 : 1;
    }

    return sortCollectionProxies(a, b);
  });
}

export function sortPinnedFavoriteProxies(
  proxies: ProxyNode[],
  favoriteProfileIds: readonly string[]
) {
  const orderMap = new Map(favoriteProfileIds.map((id, index) => [id, index]));

  return [...proxies].sort((a, b) => {
    const explicitOrderCompare = (orderMap.get(a.id) ?? Number.MAX_SAFE_INTEGER) -
      (orderMap.get(b.id) ?? Number.MAX_SAFE_INTEGER);

    if (explicitOrderCompare !== 0) {
      return explicitOrderCompare;
    }

    return sortCollectionProxies(a, b);
  });
}

export function findBestLatencyProxy(proxies: ProxyNode[]) {
  return [...proxies].sort(sortCollectionProxies).find((proxy) => hasMeasuredLatency(proxy.ping)) ?? null;
}

export function getDashboardLatencyTier(ping?: number | null): DashboardLatencyTier {
  if (!hasMeasuredLatency(ping)) {
    return "unknown";
  }

  if (ping <= 60) {
    return "excellent";
  }

  if (ping <= 120) {
    return "fast";
  }

  if (ping <= 220) {
    return "stable";
  }

  return "long";
}

export function inferDashboardRegionLabel(proxy: ProxyNode) {
  const serverTokens = isIpv4Host(proxy.server) ? [] : splitHeuristicTokens(proxy.server);
  const nameTokens = splitHeuristicTokens(proxy.name);
  const label = inferRegionFromTokens([...serverTokens, ...nameTokens]);

  return label ?? "Global Mesh";
}

export function inferDashboardRegionCountryCode(proxy: ProxyNode) {
  const serverTokens = isIpv4Host(proxy.server) ? [] : splitHeuristicTokens(proxy.server);
  const nameTokens = splitHeuristicTokens(proxy.name);

  return inferCountryCodeFromTokens([...serverTokens, ...nameTokens]);
}

export function inferDashboardRegionFlag(proxy: ProxyNode) {
  const countryCode = inferDashboardRegionCountryCode(proxy);

  return countryCode ? countryCodeToFlagEmoji(countryCode) : "🌐";
}

export function scoreDashboardProxy(proxy: ProxyNode, options: DashboardSmartRouteOptions = {}) {
  return latencyScore(proxy.ping) + reliabilityScore(proxy, options);
}

function getDashboardSmartRouteSummaryKey(
  proxy: ProxyNode,
  options: DashboardSmartRouteOptions = {}
): DashboardSmartRouteSummaryKey {
  const isFavorite = options.favoriteProfileIds?.has(proxy.id) ?? false;
  const isStable = options.lastStableProfileId === proxy.id;
  const isActive = options.activeProfileId === proxy.id;

  if (isFavorite && isStable) {
    return "dashboard.smartRouteReasonTrusted";
  }

  if (isStable) {
    return "dashboard.smartRouteReasonStable";
  }

  if (isFavorite) {
    return "dashboard.smartRouteReasonPreferred";
  }

  if (isActive) {
    return "dashboard.smartRouteReasonLive";
  }

  if (proxy.nextHopId) {
    return "dashboard.smartRouteReasonRelay";
  }

  if (hasMeasuredLatency(proxy.ping)) {
    return "dashboard.smartRouteReasonMeasured";
  }

  return "dashboard.smartRouteReasonFallback";
}

export function explainDashboardSmartRoute(
  proxy: ProxyNode,
  options: DashboardSmartRouteOptions = {}
): DashboardSmartRouteExplanation {
  const signals: DashboardSmartRouteSignal[] = [
    {
      kind: "latency",
      active: hasMeasuredLatency(proxy.ping),
      weight: latencyScore(proxy.ping),
    },
    {
      kind: "favorite",
      active: options.favoriteProfileIds?.has(proxy.id) ?? false,
      weight: 60,
    },
    {
      kind: "stable",
      active: options.lastStableProfileId === proxy.id,
      weight: 90,
    },
    {
      kind: "active",
      active: options.activeProfileId === proxy.id,
      weight: 24,
    },
    {
      kind: "relay",
      active: Boolean(proxy.nextHopId),
      weight: -16,
    },
  ];

  if (!hasMeasuredLatency(proxy.ping)) {
    signals.push({
      kind: "fallback",
      active: true,
      weight: -140,
    });
  }

  return {
    score: scoreDashboardProxy(proxy, options),
    latencyTier: getDashboardLatencyTier(proxy.ping),
    regionLabel: inferDashboardRegionLabel(proxy),
    summaryKey: getDashboardSmartRouteSummaryKey(proxy, options),
    signals,
  };
}

export function rankDashboardSmartProxies(
  proxies: ProxyNode[],
  options: DashboardSmartRouteOptions = {}
) {
  return [...proxies]
    .map((proxy) => ({
      proxy,
      score: scoreDashboardProxy(proxy, options),
    }))
    .sort((a, b) => {
      const scoreCompare = b.score - a.score;

      if (scoreCompare !== 0) {
        return scoreCompare;
      }

      return sortCollectionProxies(a.proxy, b.proxy);
    });
}

export function findBestSmartRoute(
  proxies: ProxyNode[],
  options: DashboardSmartRouteOptions = {}
) {
  return rankDashboardSmartProxies(proxies, options)[0]?.proxy ?? null;
}

export function buildDashboardRegionClusters(
  proxies: ProxyNode[],
  favoriteProfileIds: ReadonlySet<string>
) {
  const clusters = new Map<
    string,
    {
      label: string;
      proxyCount: number;
      favoriteCount: number;
      bestLatency: number | null;
      measuredCount: number;
      proxies: ProxyNode[];
    }
  >();

  for (const proxy of proxies) {
    const label = inferDashboardRegionLabel(proxy);
    const key = label.toLowerCase();
    const existing = clusters.get(key);

    if (existing) {
      existing.proxyCount += 1;
      existing.favoriteCount += favoriteProfileIds.has(proxy.id) ? 1 : 0;
      existing.proxies.push(proxy);

      if (hasMeasuredLatency(proxy.ping)) {
        existing.measuredCount += 1;
        existing.bestLatency =
          existing.bestLatency == null ? proxy.ping : Math.min(existing.bestLatency, proxy.ping);
      }

      continue;
    }

    clusters.set(key, {
      label,
      proxyCount: 1,
      favoriteCount: favoriteProfileIds.has(proxy.id) ? 1 : 0,
      bestLatency: hasMeasuredLatency(proxy.ping) ? proxy.ping : null,
      measuredCount: hasMeasuredLatency(proxy.ping) ? 1 : 0,
      proxies: [proxy],
    });
  }

  return Array.from(clusters.entries())
    .map(([key, value]) => ({
      key,
      label: value.label,
      proxyCount: value.proxyCount,
      favoriteCount: value.favoriteCount,
      bestLatency: value.bestLatency,
      measuredCount: value.measuredCount,
      dominantProtocol: dominantProtocol(value.proxies),
    }))
    .sort((a, b) => {
      const favoriteCompare = b.favoriteCount - a.favoriteCount;

      if (favoriteCompare !== 0) {
        return favoriteCompare;
      }

      const latencyCompare = compareOptionalLatency(a.bestLatency, b.bestLatency);

      if (latencyCompare !== 0) {
        return latencyCompare;
      }

      const measuredCompare = b.measuredCount - a.measuredCount;

      if (measuredCompare !== 0) {
        return measuredCompare;
      }

      const inventoryCompare = b.proxyCount - a.proxyCount;

      if (inventoryCompare !== 0) {
        return inventoryCompare;
      }

      return a.label.localeCompare(b.label, undefined, { sensitivity: "base" });
    });
}

function getCollectionDescriptor(
  node: ProxyNode,
  subscriptions: Map<string, Subscription>,
  groups: Map<string, ProfileGroup>
) {
  if (node.groupId) {
    const group = groups.get(node.groupId);
    return {
      key: `group:${node.groupId}`,
      source: "group" as const,
      sourceId: node.groupId,
      label: group?.name?.trim() || `Group ${node.groupId.slice(0, 6)}`,
      updatedAt: null,
    };
  }

  if (node.subscriptionId) {
    const subscription = subscriptions.get(node.subscriptionId);
    return {
      key: `subscription:${node.subscriptionId}`,
      source: "subscription" as const,
      sourceId: node.subscriptionId,
      label: subscription?.name?.trim() || `Subscription ${node.subscriptionId.slice(0, 6)}`,
      updatedAt: subscription?.lastUpdated ?? null,
    };
  }

  return {
    key: "manual",
    source: "manual" as const,
    sourceId: null,
    label: "Manual Profiles",
    updatedAt: null,
  };
}

export function buildDashboardProfileCollections(
  profiles: ProxyNode[],
  subscriptions: Subscription[],
  groups: ProfileGroup[]
) {
  const subscriptionMap = new Map(subscriptions.map((subscription) => [subscription.id, subscription]));
  const groupMap = new Map(groups.map((group) => [group.id, group]));
  const collectionMap = new Map<string, DashboardProfileCollection>();

  for (const profile of profiles) {
    const descriptor = getCollectionDescriptor(profile, subscriptionMap, groupMap);
    const existing = collectionMap.get(descriptor.key);

    if (existing) {
      existing.proxies.push(profile);
      existing.proxyCount += 1;
      if (!existing.protocols.includes(normalizeProtocol(profile.protocol))) {
        existing.protocols.push(normalizeProtocol(profile.protocol));
      }
      if (descriptor.updatedAt && (!existing.updatedAt || descriptor.updatedAt > existing.updatedAt)) {
        existing.updatedAt = descriptor.updatedAt;
      }
      continue;
    }

    collectionMap.set(descriptor.key, {
      key: descriptor.key,
      source: descriptor.source,
      sourceId: descriptor.sourceId,
      label: descriptor.label,
      proxyCount: 1,
      protocols: [normalizeProtocol(profile.protocol)],
      updatedAt: descriptor.updatedAt,
      proxies: [profile],
    });
  }

  return Array.from(collectionMap.values())
    .map((collection) => ({
      ...collection,
      protocols: [...collection.protocols].sort((a, b) => a.localeCompare(b)),
      proxies: [...collection.proxies].sort(sortCollectionProxies),
    }))
    .sort((a, b) => {
      const sourceOrder =
        (a.source === "group" ? 0 : a.source === "subscription" ? 1 : 2) -
        (b.source === "group" ? 0 : b.source === "subscription" ? 1 : 2);

      if (sourceOrder !== 0) {
        return sourceOrder;
      }

      return a.label.localeCompare(b.label, undefined, { sensitivity: "base" });
    });
}

export function resolveDashboardSelection(
  collections: DashboardProfileCollection[],
  options: ResolveDashboardSelectionOptions
) {
  const proxyToCollection = new Map<string, string>();

  for (const collection of collections) {
    for (const proxy of collection.proxies) {
      proxyToCollection.set(proxy.id, collection.key);
    }
  }

  const selectedProxyCollectionKey = options.selectedProxyId
    ? proxyToCollection.get(options.selectedProxyId)
    : null;

  if (options.selectedProxyId && selectedProxyCollectionKey) {
    return {
      collectionKey: selectedProxyCollectionKey,
      proxyId: options.selectedProxyId,
    };
  }

  const persistedCollectionKey = options.persistedProxyId
    ? proxyToCollection.get(options.persistedProxyId)
    : null;

  if (options.persistedProxyId && persistedCollectionKey) {
    return {
      collectionKey: persistedCollectionKey,
      proxyId: options.persistedProxyId,
    };
  }

  if (options.selectedCollectionKey) {
    const selectedCollection = collections.find(
      (collection) => collection.key === options.selectedCollectionKey
    );

    if (selectedCollection) {
      return {
        collectionKey: selectedCollection.key,
        proxyId: selectedCollection.proxies[0]?.id ?? null,
      };
    }
  }

  const firstCollection = collections[0];

  return {
    collectionKey: firstCollection?.key ?? null,
    proxyId: firstCollection?.proxies[0]?.id ?? null,
  };
}

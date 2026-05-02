import { apiClient } from './client';

export type PublicNetworkEnvelope = {
  schemaVersion: string;
  generatedAt: string;
  expiresAt: string;
  freshnessStatus: 'fresh' | 'stale' | 'degraded';
};

export type PublicNetworkOverview = PublicNetworkEnvelope & {
  global: {
    status: 'online' | 'degraded' | 'major_outage';
    totalUsers: number;
    activeUsers: number;
    totalServers: number;
    onlineServers: number;
    totalNodes: number;
    distinctCountries: number;
    totalTrafficBytes: number;
    monthlyTrafficBytes: number;
    todayBytesIn: number;
    todayBytesOut: number;
  };
};

export type PublicNetworkRegion = {
  id: string;
  countryCode: string;
  publicName: string;
  status: 'online' | 'degraded' | 'offline';
  totalServers: number;
  onlineServers: number;
  activeUsers: number;
  totalTrafficBytes: number;
};

export type PublicNetworkRegionsResponse = PublicNetworkEnvelope & {
  regions: PublicNetworkRegion[];
};

export type PublicNetworkRegionDetailResponse = PublicNetworkEnvelope & {
  region: PublicNetworkRegion;
};

export type PublicNetworkLeaderboardEntry = PublicNetworkRegion & {
  rank: number;
};

export type PublicNetworkLeaderboardResponse = PublicNetworkEnvelope & {
  leaderboard: PublicNetworkLeaderboardEntry[];
};

export type PublicNetworkIncident = {
  id: string;
  severity: 'minor' | 'major' | 'critical';
  status: 'investigating' | 'identified' | 'monitoring' | 'resolved';
  publicTitle: string;
  publicSummary: string;
  affectedRegions: string[];
  startedAt: string;
  resolvedAt?: string | null;
};

export type PublicNetworkIncidentsResponse = PublicNetworkEnvelope & {
  incidents: PublicNetworkIncident[];
};

export type PublicNetworkUptimeHistoryDay = {
  date: string;
  status: 'nominal' | 'warning' | 'outage' | 'maintenance';
};

export type PublicNetworkUptimeResponse = PublicNetworkEnvelope & {
  summary: {
    status: 'online' | 'degraded' | 'major_outage';
    currentAvailabilityPct: number;
    historyAvailable: boolean;
    windowDays: number;
    coverageDays: number;
  };
  history: PublicNetworkUptimeHistoryDay[];
};

export type PublicNetworkWidgetType = 'network_card' | 'uptime_badge' | 'speed_badge';
export type PublicNetworkWidgetThemeVariant = 'cyber' | 'matrix' | 'graphite';

export type PublicNetworkWidgetResponse = PublicNetworkEnvelope & {
  widgetType: PublicNetworkWidgetType;
  locale: string;
  themeVariant: PublicNetworkWidgetThemeVariant;
  recommendedHeight: number;
  summary: {
    status: 'online' | 'degraded' | 'major_outage';
    currentAvailabilityPct: number;
    onlineServers: number;
    activeUsers: number;
    monthlyTrafficBytes: number;
    incidentsCount: number;
  };
  focusRegion?: PublicNetworkRegion | null;
  topRegions: PublicNetworkLeaderboardEntry[];
};

export type PublicNetworkDpiScoreResponse = PublicNetworkEnvelope & {
  methodologyVersion: string;
  measurementWindow: {
    hours: number;
    minimumProbeCount: number;
  };
  enabled: boolean;
  confidence: 'low' | 'medium' | 'high';
  lastUpdatedAt?: string | null;
  reasonCode?: string | null;
  countriesTracked: number;
  countries: Array<{
    countryCode: string;
    publicName: string;
    score: number;
    confidence: 'low' | 'medium' | 'high';
    lastUpdatedAt?: string | null;
    protocols: Array<{
      protocol: string;
      successRate: number;
      medianHandshakeMs?: number | null;
      httpsBaselineSuccessRate?: number | null;
      medianHttpsBaselineMs?: number | null;
      lastProbeAt?: string | null;
    }>;
  }>;
};

export type GetPublicNetworkWidgetParams = {
  locale?: string;
  themeVariant?: PublicNetworkWidgetThemeVariant;
  widgetType?: PublicNetworkWidgetType;
  regionId?: string;
};

function buildPublicNetworkWidgetQuery(params: GetPublicNetworkWidgetParams = {}) {
  const searchParams = new URLSearchParams();

  if (params.locale) searchParams.set('locale', params.locale);
  if (params.themeVariant) searchParams.set('themeVariant', params.themeVariant);
  if (params.widgetType) searchParams.set('widgetType', params.widgetType);
  if (params.regionId) searchParams.set('regionId', params.regionId);

  const query = searchParams.toString();
  return query ? `/public/network/widget?${query}` : '/public/network/widget';
}

export const publicNetworkApi = {
  getOverview: () =>
    apiClient.get<PublicNetworkOverview>('/public/network/overview'),
  getRegions: () =>
    apiClient.get<PublicNetworkRegionsResponse>('/public/network/regions'),
  getRegion: (regionId: string) =>
    apiClient.get<PublicNetworkRegionDetailResponse>(`/public/network/regions/${regionId}`),
  getLeaderboard: () =>
    apiClient.get<PublicNetworkLeaderboardResponse>('/public/network/leaderboard'),
  getUptime: () =>
    apiClient.get<PublicNetworkUptimeResponse>('/public/network/uptime'),
  getIncidents: () =>
    apiClient.get<PublicNetworkIncidentsResponse>('/public/network/incidents'),
  getWidget: (params: GetPublicNetworkWidgetParams = {}) =>
    apiClient.get<PublicNetworkWidgetResponse>(buildPublicNetworkWidgetQuery(params)),
  getDpiScore: () =>
    apiClient.get<PublicNetworkDpiScoreResponse>('/public/network/dpi-score'),
};

import { apiClient } from './client';

export type PublicNetworkWidgetType = 'network_card' | 'uptime_badge' | 'speed_badge';
export type PublicNetworkWidgetThemeVariant = 'cyber' | 'matrix' | 'graphite';

export type PublicNetworkWidgetResponse = {
  schemaVersion: string;
  generatedAt: string;
  expiresAt: string;
  freshnessStatus: 'fresh' | 'stale' | 'degraded';
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
  getWidget: (params: GetPublicNetworkWidgetParams = {}) =>
    apiClient.get<PublicNetworkWidgetResponse>(buildPublicNetworkWidgetQuery(params)),
};

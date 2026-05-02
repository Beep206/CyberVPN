import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiClientMock = vi.hoisted(() => ({
  get: vi.fn(),
}));

vi.mock('../client', () => ({
  apiClient: apiClientMock,
}));

import { publicNetworkApi } from '../public-network';

describe('publicNetworkApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('requests the dedicated public network overview endpoint', async () => {
    const response = {
      status: 200,
      data: {
        schemaVersion: 'public-network-overview.v1',
        freshnessStatus: 'fresh',
        global: {
          status: 'online',
          activeUsers: 278,
          onlineServers: 24,
          totalNodes: 24,
          monthlyTrafficBytes: 900_000_000_000,
        },
      },
    };
    apiClientMock.get.mockResolvedValue(response);

    const result = await publicNetworkApi.getOverview();

    expect(apiClientMock.get).toHaveBeenCalledWith('/public/network/overview');
    expect(result).toBe(response);
  });

  it('requests public network regions and region detail endpoints', async () => {
    const regionsResponse = {
      status: 200,
      data: {
        schemaVersion: 'public-network-regions.v1',
        freshnessStatus: 'fresh',
        regions: [],
      },
    };
    const regionDetailResponse = {
      status: 200,
      data: {
        schemaVersion: 'public-network-regions.v1',
        freshnessStatus: 'fresh',
        region: {
          id: 'de',
          countryCode: 'DE',
        },
      },
    };
    apiClientMock.get
      .mockResolvedValueOnce(regionsResponse)
      .mockResolvedValueOnce(regionDetailResponse);

    const regions = await publicNetworkApi.getRegions();
    const region = await publicNetworkApi.getRegion('de');

    expect(apiClientMock.get).toHaveBeenNthCalledWith(1, '/public/network/regions');
    expect(apiClientMock.get).toHaveBeenNthCalledWith(2, '/public/network/regions/de');
    expect(regions).toBe(regionsResponse);
    expect(region).toBe(regionDetailResponse);
  });

  it('requests leaderboard, uptime, and incidents from the dedicated namespace', async () => {
    const leaderboardResponse = { status: 200, data: { leaderboard: [] } };
    const uptimeResponse = { status: 200, data: { summary: { currentAvailabilityPct: 99.5 }, history: [] } };
    const incidentsResponse = { status: 200, data: { incidents: [] } };
    apiClientMock.get
      .mockResolvedValueOnce(leaderboardResponse)
      .mockResolvedValueOnce(uptimeResponse)
      .mockResolvedValueOnce(incidentsResponse);

    const leaderboard = await publicNetworkApi.getLeaderboard();
    const uptime = await publicNetworkApi.getUptime();
    const incidents = await publicNetworkApi.getIncidents();

    expect(apiClientMock.get).toHaveBeenNthCalledWith(1, '/public/network/leaderboard');
    expect(apiClientMock.get).toHaveBeenNthCalledWith(2, '/public/network/uptime');
    expect(apiClientMock.get).toHaveBeenNthCalledWith(3, '/public/network/incidents');
    expect(leaderboard).toBe(leaderboardResponse);
    expect(uptime).toBe(uptimeResponse);
    expect(incidents).toBe(incidentsResponse);
  });

  it('requests widget payloads with the dedicated public widget query params', async () => {
    const widgetResponse = {
      status: 200,
      data: {
        schemaVersion: 'public-network-widget.v1',
        freshnessStatus: 'fresh',
        widgetType: 'network_card',
        locale: 'en-EN',
        themeVariant: 'cyber',
        recommendedHeight: 420,
        summary: {
          status: 'online',
          currentAvailabilityPct: 100,
          onlineServers: 24,
          activeUsers: 278,
          monthlyTrafficBytes: 900_000_000_000,
          incidentsCount: 0,
        },
        topRegions: [],
      },
    };
    apiClientMock.get.mockResolvedValue(widgetResponse);

    const result = await publicNetworkApi.getWidget({
      locale: 'en-EN',
      themeVariant: 'cyber',
      widgetType: 'network_card',
      regionId: 'de',
    });

    expect(apiClientMock.get).toHaveBeenCalledWith(
      '/public/network/widget?locale=en-EN&themeVariant=cyber&widgetType=network_card&regionId=de',
    );
    expect(result).toBe(widgetResponse);
  });

  it('requests the dedicated dpi score endpoint', async () => {
    const response = {
      status: 200,
      data: {
        schemaVersion: 'public-network-dpi-score.v1',
        freshnessStatus: 'fresh',
        methodologyVersion: 'dpi-score.methodology.v1',
        enabled: false,
        confidence: 'low',
        countriesTracked: 12,
        countries: [],
      },
    };
    apiClientMock.get.mockResolvedValue(response);

    const result = await publicNetworkApi.getDpiScore();

    expect(apiClientMock.get).toHaveBeenCalledWith('/public/network/dpi-score');
    expect(result).toBe(response);
  });
});

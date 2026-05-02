import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiClientMock = vi.hoisted(() => ({
  get: vi.fn(),
}));

vi.mock('../client', () => ({
  apiClient: apiClientMock,
}));

import { publicNetworkApi } from '../public-network';

describe('partner publicNetworkApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('requests the widget payload through the dedicated public network namespace', async () => {
    const response = {
      status: 200,
      data: {
        schemaVersion: 'public-network-widget.v1',
        freshnessStatus: 'fresh',
        widgetType: 'network_card',
      },
    };
    apiClientMock.get.mockResolvedValue(response);

    const result = await publicNetworkApi.getWidget({
      locale: 'en-EN',
      themeVariant: 'cyber',
      widgetType: 'network_card',
      regionId: 'de',
    });

    expect(apiClientMock.get).toHaveBeenCalledWith(
      '/public/network/widget?locale=en-EN&themeVariant=cyber&widgetType=network_card&regionId=de',
    );
    expect(result).toBe(response);
  });
});

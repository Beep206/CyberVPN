import { describe, expect, it, vi } from 'vitest';

const transportGetMock = vi.fn();

vi.mock('../client', () => ({
  apiClient: {
    get: transportGetMock,
  },
}));

import {
  GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
  serversApi,
} from '../servers';

describe('customer global server topology client', () => {
  it('fails closed before transport for every retired read', async () => {
    await expect(serversApi.list()).rejects.toMatchObject({
      code: GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
    });
    await expect(serversApi.getStats()).rejects.toMatchObject({
      code: GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
    });
    await expect(serversApi.get('11111111-1111-4111-8111-111111111111')).rejects.toMatchObject({
      code: GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
    });

    expect(transportGetMock).not.toHaveBeenCalled();
  });
});

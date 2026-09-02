import { describe, expect, it, vi } from 'vitest';

const transportMock = vi.fn();

vi.mock('../client', () => ({
  apiClient: {
    delete: transportMock,
    get: transportMock,
    post: transportMock,
    put: transportMock,
  },
}));

import {
  GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
  serversApi,
} from '../servers';

describe('partner global server topology client', () => {
  it('fails closed before transport for reads and mutations', async () => {
    const serverId = '11111111-1111-4111-8111-111111111111';
    const createPayload = {
      address: 'node.example.test',
      name: 'retired',
      port: 443,
    };

    await expect(serversApi.list()).rejects.toMatchObject({
      code: GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
    });
    await expect(serversApi.getStats()).rejects.toMatchObject({
      code: GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
    });
    await expect(serversApi.get(serverId)).rejects.toMatchObject({
      code: GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
    });
    await expect(serversApi.create(createPayload)).rejects.toMatchObject({
      code: GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
    });
    await expect(serversApi.update(serverId, createPayload)).rejects.toMatchObject({
      code: GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
    });
    await expect(serversApi.remove(serverId)).rejects.toMatchObject({
      code: GLOBAL_SERVER_TOPOLOGY_UNAVAILABLE_CODE,
    });

    expect(transportMock).not.toHaveBeenCalled();
  });
});

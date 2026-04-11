import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { authApi } from '../auth';

const API_BASE = '*/api/v1';

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('authApi security session operations', () => {
  it('lists active devices for the current admin session', async () => {
    server.use(
      http.get(`${API_BASE}/auth/devices`, () =>
        HttpResponse.json({
          devices: [
            {
              device_id: 'dev_current',
              ip_address: '203.0.113.10',
              user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X)',
              last_used_at: '2026-04-10T08:00:00Z',
              created_at: '2026-04-09T08:00:00Z',
              is_current: true,
            },
            {
              device_id: 'dev_remote',
              ip_address: '198.51.100.77',
              user_agent: 'Mozilla/5.0 (Linux; Android 14)',
              last_used_at: '2026-04-10T07:30:00Z',
              created_at: '2026-04-08T10:00:00Z',
              is_current: false,
            },
          ],
          total: 2,
        }),
      ),
    );

    const response = await authApi.listDevices();

    expect(response.status).toBe(200);
    expect(response.data.total).toBe(2);
    expect(response.data.devices[0]?.device_id).toBe('dev_current');
    expect(response.data.devices[1]?.is_current).toBe(false);
  });

  it('revokes a specific device session by device id', async () => {
    let revokedDeviceId = '';

    server.use(
      http.delete(`${API_BASE}/auth/devices/:deviceId`, ({ params }) => {
        revokedDeviceId = String(params.deviceId);

        return HttpResponse.json({
          message: 'Device session revoked successfully',
          device_id: revokedDeviceId,
        });
      }),
    );

    const response = await authApi.logoutDevice('dev_remote');

    expect(response.status).toBe(200);
    expect(revokedDeviceId).toBe('dev_remote');
    expect(response.data.device_id).toBe('dev_remote');
  });

  it('logs out all active sessions and returns revoked session count', async () => {
    server.use(
      http.post(`${API_BASE}/auth/logout-all`, () =>
        HttpResponse.json({
          message: 'All sessions terminated',
          sessions_revoked: 4,
        }),
      ),
    );

    const response = await authApi.logoutAllDevices();

    expect(response.status).toBe(200);
    expect(response.data.message).toBe('All sessions terminated');
    expect(response.data.sessions_revoked).toBe(4);
  });
});

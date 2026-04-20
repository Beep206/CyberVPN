import { afterEach, describe, expect, it } from 'vitest';
import {
  buildMonitoringSocketUrl,
  resolveRealtimeBaseUrl,
} from '../realtime';

describe('realtime url helpers', () => {
  const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
  });

  it('builds ws urls from NEXT_PUBLIC_API_URL', () => {
    process.env.NEXT_PUBLIC_API_URL = 'https://api.ozoxy.ru';

    expect(resolveRealtimeBaseUrl()).toBe('wss://api.ozoxy.ru/api/v1');
    expect(buildMonitoringSocketUrl('ticket-001')).toBe(
      'wss://api.ozoxy.ru/api/v1/ws/monitoring?ticket=ticket-001',
    );
  });

  it('preserves existing /api/v1 path in configured base url', () => {
    process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000/api/v1';

    expect(resolveRealtimeBaseUrl()).toBe('ws://localhost:8000/api/v1');
    expect(buildMonitoringSocketUrl('ticket-002')).toBe(
      'ws://localhost:8000/api/v1/ws/monitoring?ticket=ticket-002',
    );
  });
});

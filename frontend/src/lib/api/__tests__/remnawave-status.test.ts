import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { remnawaveStatusApi } from '../remnawave-status';

const API_BASE = '*/api/v1';

describe('remnawaveStatusApi', () => {
  it('whitelists the own-scope customer availability contract', async () => {
    server.use(
      http.get(`${API_BASE}/customer/vpn-service-status`, () =>
        HttpResponse.json({
          connections_available: true,
          usage_available: false,
          devices_available: true,
          degraded: true,
          degraded_reason: 'safe_customer_reason',
          node_ip: '203.0.113.5',
          ssh_ticket: 'terminal-secret',
          subscription_url: 'https://secret.invalid/subscription',
        }),
      ),
    );

    const status = await remnawaveStatusApi.getCustomerStatus();

    expect(status).toEqual({
      connections_available: true,
      usage_available: false,
      devices_available: true,
      degraded: true,
      degraded_reason: 'safe_customer_reason',
    });
    expect(status).not.toHaveProperty('node_ip');
    expect(status).not.toHaveProperty('ssh_ticket');
    expect(status).not.toHaveProperty('subscription_url');
  });

  it('fails closed when the customer status shape is invalid', async () => {
    server.use(
      http.get(`${API_BASE}/customer/vpn-service-status`, () =>
        HttpResponse.json({
          connections_available: 'yes',
          usage_available: true,
          devices_available: true,
          degraded: false,
          degraded_reason: null,
        }),
      ),
    );

    await expect(remnawaveStatusApi.getCustomerStatus()).rejects.toThrow(
      'Invalid customer VPN service status response',
    );
  });

  it('creates and polls an own-scope connection read without retaining topology', async () => {
    const requestId = 'r'.repeat(43);
    const capabilities = {
      drop_connections: true,
      drop_outcome_may_be_unknown: true,
      drop_requires_idempotency_key: true,
      read_connections: true,
    };
    server.use(
      http.post(`${API_BASE}/customer/remnawave/connections/requests`, () =>
        HttpResponse.json({
          capabilities,
          expires_in_seconds: 300,
          poll_after_seconds: 1,
          request_id: requestId,
          upstream_job_token: 'must-not-leak',
        }, { status: 202 }),
      ),
      http.get(`${API_BASE}/customer/remnawave/connections/requests/${requestId}`, () =>
        HttpResponse.json({
          active_ip_count: 2,
          capabilities,
          connected: true,
          connected_node_count: 1,
          is_completed: true,
          is_failed: false,
          last_seen_at: '2026-08-31T08:00:00Z',
          progress: { completed: 2, percent: 100, total: 2 },
          success: true,
          ips: ['203.0.113.7'],
          node_names: ['private-node'],
        }),
      ),
    );

    const request = await remnawaveStatusApi.requestCustomerConnections();
    const status = await remnawaveStatusApi.getCustomerConnections(request.request_id);

    expect(request).not.toHaveProperty('upstream_job_token');
    expect(status).toEqual({
      active_ip_count: 2,
      capabilities,
      connected: true,
      connected_node_count: 1,
      is_completed: true,
      is_failed: false,
      last_seen_at: '2026-08-31T08:00:00Z',
      progress: { completed: 2, percent: 100, total: 2 },
      success: true,
    });
    expect(status).not.toHaveProperty('ips');
    expect(status).not.toHaveProperty('node_names');
  });

  it('sends a customer drop once with the caller idempotency key', async () => {
    const idempotencyKey = 'customer-drop-2026-08-31';
    let receivedIdempotencyKey: string | null = null;
    server.use(
      http.post(`${API_BASE}/customer/remnawave/connections/drop`, ({ request }) => {
        receivedIdempotencyKey = request.headers.get('Idempotency-Key');
        return HttpResponse.json({
          expires_at: null,
          expires_in_seconds: null,
          receipt_id: 'd'.repeat(43),
          requires_reconciliation: true,
          retry_allowed: false,
          state: 'outcome_unknown',
          upstream_error: 'private provider timeout',
        }, { status: 202 });
      }),
    );

    const receipt = await remnawaveStatusApi.dropCustomerConnections(idempotencyKey);

    expect(receivedIdempotencyKey).toBe(idempotencyKey);
    expect(receipt).toEqual({
      expires_at: null,
      expires_in_seconds: null,
      receipt_id: 'd'.repeat(43),
      requires_reconciliation: true,
      retry_allowed: false,
      state: 'outcome_unknown',
    });
    expect(receipt).not.toHaveProperty('upstream_error');
  });

  it('preserves a reconciled accepted receipt with its bounded expiry', async () => {
    server.use(
      http.post(`${API_BASE}/customer/remnawave/connections/drop`, () =>
        HttpResponse.json({
          expires_at: '2026-09-01T12:00:00Z',
          expires_in_seconds: 3_600,
          receipt_id: 'a'.repeat(43),
          requires_reconciliation: false,
          retry_allowed: false,
          state: 'accepted',
        }, { status: 202 }),
      ),
    );

    await expect(
      remnawaveStatusApi.dropCustomerConnections('customer-drop-accepted-0001'),
    ).resolves.toEqual({
      expires_at: '2026-09-01T12:00:00Z',
      expires_in_seconds: 3_600,
      receipt_id: 'a'.repeat(43),
      requires_reconciliation: false,
      retry_allowed: false,
      state: 'accepted',
    });
  });

  it.each([
    {
      expires_at: null,
      expires_in_seconds: null,
      requires_reconciliation: false,
      state: 'outcome_unknown',
    },
    {
      expires_at: '2026-09-01T12:00:00Z',
      expires_in_seconds: 3_600,
      requires_reconciliation: true,
      state: 'outcome_unknown',
    },
    {
      expires_at: null,
      expires_in_seconds: null,
      requires_reconciliation: false,
      state: 'accepted',
    },
    {
      expires_at: 'not-a-date',
      expires_in_seconds: 3_600,
      requires_reconciliation: false,
      state: 'accepted',
    },
  ])('fails closed on an inconsistent drop receipt lifecycle', async (lifecycle) => {
    server.use(
      http.post(`${API_BASE}/customer/remnawave/connections/drop`, () =>
        HttpResponse.json({
          ...lifecycle,
          receipt_id: 'i'.repeat(43),
          retry_allowed: false,
        }, { status: 202 }),
      ),
    );

    await expect(
      remnawaveStatusApi.dropCustomerConnections('customer-drop-invalid-0001'),
    ).rejects.toThrow('Invalid customer Remnawave connection drop receipt');
  });

  it('rejects an invalid drop idempotency key before network I/O', async () => {
    await expect(remnawaveStatusApi.dropCustomerConnections('short')).rejects.toThrow(
      'Customer connection drop idempotency key is invalid',
    );
  });

  it('fails closed on a malformed aggregate instead of exposing raw connection data', async () => {
    const requestId = 'x'.repeat(43);
    server.use(
      http.get(`${API_BASE}/customer/remnawave/connections/requests/${requestId}`, () =>
        HttpResponse.json({
          active_ip_count: 1,
          capabilities: {
            drop_connections: true,
            drop_outcome_may_be_unknown: true,
            drop_requires_idempotency_key: true,
            read_connections: true,
          },
          connected: true,
          connected_node_count: 1,
          is_completed: true,
          is_failed: false,
          last_seen_at: 'not-a-date',
          progress: { completed: 1, percent: 100, total: 1 },
          success: true,
          ips: ['203.0.113.8'],
        }),
      ),
    );

    await expect(remnawaveStatusApi.getCustomerConnections(requestId)).rejects.toThrow(
      'Invalid customer Remnawave connections status response',
    );
  });
});

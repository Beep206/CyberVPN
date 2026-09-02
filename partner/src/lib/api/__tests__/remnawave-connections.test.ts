import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { partnerRemnawaveConnectionsApi } from '../remnawave-connections';

const API_BASE = '*/api/v1';
const NODE_UUID = '11111111-1111-1111-1111-111111111111';
const SERVICE_IDENTITY_UUID = '22222222-2222-4222-8222-222222222222';
const REQUEST_ID = 'r'.repeat(43);
const RECEIPT_ID = 'p'.repeat(43);
const CAPABILITIES = {
  read_connections: true,
  drop_connections: true,
  drop_requires_idempotency_key: true,
  drop_outcome_may_be_unknown: true,
};

describe('partnerRemnawaveConnectionsApi', () => {
  it('requests and polls an exact granted node while allowlisting aggregate fields', async () => {
    const requestedPaths: string[] = [];
    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/requests`,
        ({ request }) => {
          requestedPaths.push(new URL(request.url).pathname);
          return HttpResponse.json({
            request_id: REQUEST_ID,
            poll_after_seconds: 1,
            expires_in_seconds: 300,
            capabilities: CAPABILITIES,
          }, { status: 201 });
        },
      ),
      http.get(
        `${API_BASE}/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/requests/${REQUEST_ID}`,
        ({ request }) => {
          requestedPaths.push(new URL(request.url).pathname);
          return HttpResponse.json({
            is_completed: true,
            is_failed: false,
            success: true,
            node_uuid: NODE_UUID,
            connected_user_count: 2,
            active_ip_count: 3,
            last_seen_at: '2026-08-31T08:30:00Z',
            capabilities: CAPABILITIES,
            users: [{ user_id: 42, ips: ['203.0.113.10'] }],
            node_ip: '203.0.113.11',
            topology: { upstream: 'private' },
            provider_token: 'must-not-reach-ui',
          });
        },
      ),
    );

    const request = await partnerRemnawaveConnectionsApi.requestNodeConnections(
      'workspace_001',
      NODE_UUID,
    );
    const status = await partnerRemnawaveConnectionsApi.getNodeConnections(
      'workspace_001',
      NODE_UUID,
      request.request_id,
    );

    expect(request).toEqual({
      request_id: REQUEST_ID,
      poll_after_seconds: 1,
      expires_in_seconds: 300,
      capabilities: CAPABILITIES,
    });
    expect(status).toEqual({
      is_completed: true,
      is_failed: false,
      success: true,
      node_uuid: NODE_UUID,
      connected_user_count: 2,
      active_ip_count: 3,
      last_seen_at: '2026-08-31T08:30:00Z',
      capabilities: CAPABILITIES,
    });
    expect(status).not.toHaveProperty('users');
    expect(status).not.toHaveProperty('node_ip');
    expect(status).not.toHaveProperty('topology');
    expect(status).not.toHaveProperty('provider_token');
    expect(requestedPaths).toEqual([
      `/api/v1/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/requests`,
      `/api/v1/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/requests/${REQUEST_ID}`,
    ]);
  });

  it('rejects a poll response for a different node or inconsistent aggregate counts', async () => {
    server.use(
      http.get(
        `${API_BASE}/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/requests/${REQUEST_ID}`,
        () => HttpResponse.json({
          is_completed: true,
          is_failed: false,
          success: true,
          node_uuid: '22222222-2222-2222-2222-222222222222',
          connected_user_count: 4,
          active_ip_count: 3,
          last_seen_at: null,
          capabilities: CAPABILITIES,
        }),
      ),
    );

    let rejection: unknown;
    try {
      await partnerRemnawaveConnectionsApi.getNodeConnections(
        'workspace_001',
        NODE_UUID,
        REQUEST_ID,
      );
    } catch (error) {
      rejection = error;
    }
    expect(rejection).toBeInstanceOf(Error);
    if (!(rejection instanceof Error)) throw new Error('Expected parser rejection');
    expect(rejection.message).toBe('Invalid partner Remnawave node connections response');
  });

  it('sends only an opaque service-identity UUID with the caller idempotency key', async () => {
    let capturedHeader: string | null = null;
    let capturedBody: unknown;
    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/drop`,
        async ({ request }) => {
          capturedHeader = request.headers.get('Idempotency-Key');
          capturedBody = await request.json();
          return HttpResponse.json({
            expires_at: null,
            expires_in_seconds: null,
            receipt_id: RECEIPT_ID,
            requires_reconciliation: true,
            state: 'outcome_unknown',
            retry_allowed: false,
            raw_provider_result: { accepted: true },
          }, { status: 202 });
        },
      ),
    );

    const receipt = await partnerRemnawaveConnectionsApi.dropNodeConnectionsByServiceIdentity(
      'workspace_001',
      NODE_UUID,
      SERVICE_IDENTITY_UUID,
      'partner-connections-0000000000000001',
    );

    expect(capturedHeader).toBe('partner-connections-0000000000000001');
    expect(capturedBody).toEqual({
      serviceIdentityUuid: SERVICE_IDENTITY_UUID,
    });
    expect(capturedBody).not.toHaveProperty('dropBy');
    expect(capturedBody).not.toHaveProperty('userIds');
    expect(capturedBody).not.toHaveProperty('ipAddresses');
    expect(receipt).toEqual({
      expires_at: null,
      expires_in_seconds: null,
      receipt_id: RECEIPT_ID,
      requires_reconciliation: true,
      state: 'outcome_unknown',
      retry_allowed: false,
    });
    expect(receipt).not.toHaveProperty('raw_provider_result');
    expect(partnerRemnawaveConnectionsApi).not.toHaveProperty('dropNodeConnectionsByUserIds');
    expect(partnerRemnawaveConnectionsApi).not.toHaveProperty('dropNodeConnectionsByIp');
  });

  it('fails closed on a malformed request id or mutable drop receipt', async () => {
    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/requests`,
        () => HttpResponse.json({
          request_id: 'provider-job-id',
          poll_after_seconds: 1,
          expires_in_seconds: 300,
          capabilities: CAPABILITIES,
        }, { status: 201 }),
      ),
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/drop`,
        () => HttpResponse.json({
          expires_at: '2026-09-01T12:00:00Z',
          expires_in_seconds: 86_400,
          receipt_id: RECEIPT_ID,
          requires_reconciliation: false,
          state: 'accepted',
          retry_allowed: true,
        }, { status: 202 }),
      ),
    );

    let requestRejection: unknown;
    try {
      await partnerRemnawaveConnectionsApi.requestNodeConnections('workspace_001', NODE_UUID);
    } catch (error) {
      requestRejection = error;
    }
    expect(requestRejection).toBeInstanceOf(Error);
    if (!(requestRejection instanceof Error)) throw new Error('Expected request parser rejection');
    expect(requestRejection.message).toBe('Invalid partner Remnawave connection request response');

    let receiptRejection: unknown;
    try {
      await partnerRemnawaveConnectionsApi.dropNodeConnectionsByServiceIdentity(
        'workspace_001',
        NODE_UUID,
        SERVICE_IDENTITY_UUID,
        'partner-connections-0000000000000001',
      );
    } catch (error) {
      receiptRejection = error;
    }
    expect(receiptRejection).toBeInstanceOf(Error);
    if (!(receiptRejection instanceof Error)) throw new Error('Expected receipt parser rejection');
    expect(receiptRejection.message).toBe('Invalid partner Remnawave connection drop receipt');
  });

  it('rejects invalid drop targets and idempotency keys before transport', async () => {
    let requestCount = 0;
    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/drop`,
        () => {
          requestCount += 1;
          return HttpResponse.json({
            expires_at: '2026-09-01T12:00:00Z',
            expires_in_seconds: 86_400,
            receipt_id: RECEIPT_ID,
            requires_reconciliation: false,
            state: 'accepted',
            retry_allowed: false,
          }, { status: 202 });
        },
      ),
    );

    for (const [serviceIdentityUuid, idempotencyKey] of [
      ['', 'partner-connections-0000000000000001'],
      ['not-a-uuid', 'partner-connections-0000000000000001'],
      ['00000000-0000-0000-0000-000000000000', 'partner-connections-0000000000000001'],
      [SERVICE_IDENTITY_UUID, 'short'],
    ]) {
      let rejection: unknown;
      try {
        await partnerRemnawaveConnectionsApi.dropNodeConnectionsByServiceIdentity(
          'workspace_001',
          NODE_UUID,
          serviceIdentityUuid,
          idempotencyKey,
        );
      } catch (error) {
        rejection = error;
      }
      expect(rejection).toBeInstanceOf(Error);
      if (!(rejection instanceof Error)) throw new Error('Expected drop request rejection');
      expect(rejection.message).toBe('Invalid partner Remnawave connection drop request');
    }
    expect(requestCount).toBe(0);
  });

  it('preserves a reconciled accepted receipt with its expiry', async () => {
    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/drop`,
        () => HttpResponse.json({
          expires_at: '2026-09-01T12:00:00Z',
          expires_in_seconds: 1_800,
          receipt_id: RECEIPT_ID,
          requires_reconciliation: false,
          retry_allowed: false,
          state: 'accepted',
        }, { status: 202 }),
      ),
    );

    await expect(partnerRemnawaveConnectionsApi.dropNodeConnectionsByServiceIdentity(
      'workspace_001',
      NODE_UUID,
      SERVICE_IDENTITY_UUID,
      'partner-connections-accepted-0001',
    )).resolves.toEqual({
      expires_at: '2026-09-01T12:00:00Z',
      expires_in_seconds: 1_800,
      receipt_id: RECEIPT_ID,
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
      expires_in_seconds: 1_800,
      requires_reconciliation: true,
      state: 'outcome_unknown',
    },
    {
      expires_at: null,
      expires_in_seconds: null,
      requires_reconciliation: false,
      state: 'accepted',
    },
  ])('fails closed on an inconsistent drop receipt lifecycle', async (lifecycle) => {
    server.use(
      http.post(
        `${API_BASE}/partner-workspaces/workspace_001/remnawave/connections/nodes/${NODE_UUID}/drop`,
        () => HttpResponse.json({
          ...lifecycle,
          receipt_id: RECEIPT_ID,
          retry_allowed: false,
        }, { status: 202 }),
      ),
    );

    let rejection: unknown;
    try {
      await partnerRemnawaveConnectionsApi.dropNodeConnectionsByServiceIdentity(
        'workspace_001',
        NODE_UUID,
        SERVICE_IDENTITY_UUID,
        'partner-connections-invalid-0001',
      );
    } catch (error) {
      rejection = error;
    }
    expect(rejection).toBeInstanceOf(Error);
    if (!(rejection instanceof Error)) throw new Error('Expected receipt parser rejection');
    expect(rejection.message).toBe('Invalid partner Remnawave connection drop receipt');
  });
});

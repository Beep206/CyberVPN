import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { adminRemnawaveConnectionsApi } from '../remnawave-connections';

const REQUEST_ID = 'a'.repeat(43);
const RECEIPT_ID = 'b'.repeat(43);
const NODE_UUID = '550e8400-e29b-41d4-a716-446655440000';
const RECONCILIATION_REFERENCE = 'CASE-ABC123';
const CAPABILITIES = {
  read_connections: true,
  drop_connections: true,
  drop_requires_idempotency_key: true,
  drop_outcome_may_be_unknown: true,
};

const MATCH_ANY_API_ORIGIN = {
  userRequest: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/remnawave\/connections\/users\/42\/requests$/,
  userStatus: new RegExp(`https?:\\/\\/localhost(?::\\d+)?\\/api\\/v1\\/admin\\/remnawave\\/connections\\/users\\/42\\/requests\\/${REQUEST_ID}$`),
  nodeRequest: new RegExp(`https?:\\/\\/localhost(?::\\d+)?\\/api\\/v1\\/admin\\/remnawave\\/connections\\/nodes\\/${NODE_UUID}\\/requests$`),
  drop: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/remnawave\/connections\/drop$/,
  unresolvedReceipts: /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/remnawave\/connections\/drop-receipts\/unresolved(?:\?.*)?$/,
  receipt: new RegExp(`https?:\\/\\/localhost(?::\\d+)?\\/api\\/v1\\/admin\\/remnawave\\/connections\\/drop-receipts\\/${RECEIPT_ID}$`),
  reconcileReceipt: new RegExp(`https?:\\/\\/localhost(?::\\d+)?\\/api\\/v1\\/admin\\/remnawave\\/connections\\/drop-receipts\\/${RECEIPT_ID}\\/reconcile$`),
};

const UNRESOLVED_RECEIPT = {
  receipt_id: RECEIPT_ID,
  state: 'outcome_unknown' as const,
  audience: 'admin' as const,
  created_at: '2026-08-31T10:00:00Z',
  updated_at: '2026-08-31T10:01:00Z',
  expires_at: null,
  expires_in_seconds: null,
  requires_reconciliation: true,
  reconciled_at: null,
  reconciliation_reason: null,
  reconciliation_reference: null,
};

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('adminRemnawaveConnectionsApi', () => {
  it('creates and validates an asynchronous numeric-user request', async () => {
    server.use(
      http.post(MATCH_ANY_API_ORIGIN.userRequest, () => HttpResponse.json({
        request_id: REQUEST_ID,
        poll_after_seconds: 1,
        expires_in_seconds: 300,
        capabilities: CAPABILITIES,
      }, { status: 201 })),
    );

    await expect(adminRemnawaveConnectionsApi.requestUserConnections(42)).resolves.toEqual({
      request_id: REQUEST_ID,
      poll_after_seconds: 1,
      expires_in_seconds: 300,
      capabilities: CAPABILITIES,
    });
  });

  it('validates the admin-only user topology returned by the polling route', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.userStatus, () => HttpResponse.json({
        is_completed: true,
        is_failed: false,
        progress: { total: 1, completed: 1, percent: 100 },
        result: {
          success: true,
          user_id: 42,
          nodes: [{
            node_uuid: NODE_UUID,
            node_name: 'Moscow edge',
            country_code: 'RU',
            ips: [{ ip: '203.0.113.10', last_seen: '2026-08-31T10:00:00Z' }],
          }],
        },
        capabilities: CAPABILITIES,
      })),
    );

    const result = await adminRemnawaveConnectionsApi.getUserConnections(42, REQUEST_ID);

    expect(result.result?.nodes[0]?.ips[0]?.ip).toBe('203.0.113.10');
    expect(result.result?.nodes[0]?.node_uuid).toBe(NODE_UUID);
  });

  it('rejects malformed provider data instead of exposing a partial topology', async () => {
    server.use(
      http.post(MATCH_ANY_API_ORIGIN.nodeRequest, () => HttpResponse.json({
        request_id: 'unsafe-request-id',
        poll_after_seconds: 1,
        expires_in_seconds: 300,
        capabilities: CAPABILITIES,
      }, { status: 201 })),
    );

    await expect(
      adminRemnawaveConnectionsApi.requestNodeConnections(NODE_UUID),
    ).rejects.toThrow('Invalid connection request ID response');
  });

  it('rejects a malformed polling result instead of returning partial admin IP data', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.userStatus, () => HttpResponse.json({
        is_completed: true,
        is_failed: false,
        progress: { total: 1, completed: 1, percent: 100 },
        result: {
          success: true,
          user_id: 42,
          nodes: [{
            node_uuid: 'not-a-uuid',
            node_name: 'Untrusted provider value',
            country_code: 'RU',
            ips: [{ ip: '203.0.113.10', last_seen: '2026-08-31T10:00:00Z' }],
          }],
        },
        capabilities: CAPABILITIES,
      })),
    );

    await expect(
      adminRemnawaveConnectionsApi.getUserConnections(42, REQUEST_ID),
    ).rejects.toThrow('Invalid connection node UUID response');
  });

  it('sends the exact drop shape once with the caller-owned idempotency key', async () => {
    let capturedBody: unknown;
    let capturedKey: string | null = null;
    server.use(
      http.post(MATCH_ANY_API_ORIGIN.drop, async ({ request }) => {
        capturedBody = await request.json();
        capturedKey = request.headers.get('Idempotency-Key');
        return HttpResponse.json({
          expires_at: null,
          expires_in_seconds: null,
          receipt_id: RECEIPT_ID,
          requires_reconciliation: true,
          state: 'outcome_unknown',
          retry_allowed: false,
        }, { status: 202 });
      }),
    );

    const receipt = await adminRemnawaveConnectionsApi.dropConnections(
      {
        dropBy: { by: 'userIds', userIds: [42] },
        targetNodes: { target: 'specificNodes', nodeUuids: [NODE_UUID] },
      },
      'connections-drop:550e8400-e29b-41d4-a716-446655440000',
    );

    expect(capturedBody).toEqual({
      dropBy: { by: 'userIds', userIds: [42] },
      targetNodes: { target: 'specificNodes', nodeUuids: [NODE_UUID] },
    });
    expect(capturedKey).toBe('connections-drop:550e8400-e29b-41d4-a716-446655440000');
    expect(receipt).toEqual({
      expires_at: null,
      expires_in_seconds: null,
      receipt_id: RECEIPT_ID,
      requires_reconciliation: true,
      retry_allowed: false,
      state: 'outcome_unknown',
    });
  });

  it('preserves a reconciled accepted drop receipt with its expiry', async () => {
    server.use(
      http.post(MATCH_ANY_API_ORIGIN.drop, () => HttpResponse.json({
        expires_at: '2026-09-01T12:00:00Z',
        expires_in_seconds: 7_200,
        receipt_id: RECEIPT_ID,
        requires_reconciliation: false,
        retry_allowed: false,
        state: 'accepted',
      }, { status: 202 })),
    );

    await expect(adminRemnawaveConnectionsApi.dropConnections(
      {
        dropBy: { by: 'userIds', userIds: [42] },
        targetNodes: { target: 'allNodes' },
      },
      'connections-drop:accepted:0001',
    )).resolves.toEqual({
      expires_at: '2026-09-01T12:00:00Z',
      expires_in_seconds: 7_200,
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
      expires_in_seconds: 7_200,
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
      http.post(MATCH_ANY_API_ORIGIN.drop, () => HttpResponse.json({
        ...lifecycle,
        receipt_id: RECEIPT_ID,
        retry_allowed: false,
      }, { status: 202 })),
    );

    await expect(adminRemnawaveConnectionsApi.dropConnections(
      {
        dropBy: { by: 'userIds', userIds: [42] },
        targetNodes: { target: 'allNodes' },
      },
      'connections-drop:invalid:0001',
    )).rejects.toThrow('Invalid connection drop lifecycle response from CyberVPN API');
  });

  it('lists a bounded unresolved page and strips receipt-store internals', async () => {
    let capturedLimit: string | null = null;
    let capturedCursor: string | null = null;
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.unresolvedReceipts, ({ request }) => {
        const url = new URL(request.url);
        capturedLimit = url.searchParams.get('limit');
        capturedCursor = url.searchParams.get('cursor');
        return HttpResponse.json({
          items: [{
            ...UNRESOLVED_RECEIPT,
            receipt_hmac: 'must-not-cross-the-boundary',
            scope: 'admin:global',
            raw_payload: { upstream: 'secret' },
            terminal_ttl_seconds: 7_200,
          }],
          next_cursor: 'c'.repeat(43),
        });
      }),
    );

    const page = await adminRemnawaveConnectionsApi.listUnresolvedDropReceipts({
      limit: 25,
      cursor: 'a'.repeat(43),
    });

    expect(capturedLimit).toBe('25');
    expect(capturedCursor).toBe('a'.repeat(43));
    expect(page).toEqual({
      items: [UNRESOLVED_RECEIPT],
      next_cursor: 'c'.repeat(43),
    });
    expect(page.items[0]).not.toHaveProperty('receipt_hmac');
    expect(page.items[0]).not.toHaveProperty('scope');
    expect(page.items[0]).not.toHaveProperty('raw_payload');
    expect(page.items[0]).not.toHaveProperty('terminal_ttl_seconds');
  });

  it('fails closed when an unresolved page contains a terminal or inconsistent receipt', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.unresolvedReceipts, () => HttpResponse.json({
        items: [{
          ...UNRESOLVED_RECEIPT,
          state: 'accepted',
          expires_at: '2026-09-01T12:00:00Z',
          expires_in_seconds: 7_200,
          requires_reconciliation: false,
        }],
        next_cursor: null,
      })),
    );

    await expect(
      adminRemnawaveConnectionsApi.listUnresolvedDropReceipts(),
    ).rejects.toThrow('Invalid unresolved connection drop receipt lifecycle response');
  });

  it('gets an exact admin receipt and preserves a complete rejected reconciliation', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.receipt, () => HttpResponse.json({
        ...UNRESOLVED_RECEIPT,
        state: 'rejected',
        expires_at: '2026-09-01T12:00:00Z',
        expires_in_seconds: 7_200,
        requires_reconciliation: false,
        updated_at: '2026-08-31T10:05:00Z',
        reconciled_at: '2026-08-31T10:05:00Z',
        reconciliation_reason: 'provider_confirmed_not_applied',
        reconciliation_reference: RECONCILIATION_REFERENCE,
      })),
    );

    await expect(adminRemnawaveConnectionsApi.getDropReceipt(RECEIPT_ID)).resolves.toMatchObject({
      receipt_id: RECEIPT_ID,
      state: 'rejected',
      requires_reconciliation: false,
      reconciliation_reason: 'provider_confirmed_not_applied',
      reconciliation_reference: RECONCILIATION_REFERENCE,
    });
  });

  it('reconciles with only the compatible public fields and parses the terminal lifecycle', async () => {
    let capturedBody: unknown;
    server.use(
      http.post(MATCH_ANY_API_ORIGIN.reconcileReceipt, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({
          ...UNRESOLVED_RECEIPT,
          state: 'accepted',
          expires_at: '2026-09-01T12:00:00Z',
          expires_in_seconds: 7_200,
          requires_reconciliation: false,
          updated_at: '2026-08-31T10:05:00Z',
          reconciled_at: '2026-08-31T10:05:00Z',
          reconciliation_reason: 'provider_confirmed_applied',
          reconciliation_reference: RECONCILIATION_REFERENCE,
        });
      }),
    );
    const bodyWithForbiddenExtras = {
      outcome: 'accepted' as const,
      reason: 'provider_confirmed_applied' as const,
      reference: ' case-abc123 ',
      terminal_ttl_seconds: 99,
      receipt_hmac: 'forbidden',
      scope: 'admin:global',
      raw_payload: { forbidden: true },
    };

    const receipt = await adminRemnawaveConnectionsApi.reconcileDropReceipt(
      RECEIPT_ID,
      bodyWithForbiddenExtras,
    );

    expect(capturedBody).toEqual({
      outcome: 'accepted',
      reason: 'provider_confirmed_applied',
      reference: RECONCILIATION_REFERENCE,
    });
    expect(receipt).toMatchObject({
      state: 'accepted',
      requires_reconciliation: false,
      reconciliation_reason: 'provider_confirmed_applied',
      reconciliation_reference: RECONCILIATION_REFERENCE,
    });
  });

  it.each([
    {
      outcome: 'accepted' as const,
      reason: 'provider_confirmed_not_applied' as const,
      reference: RECONCILIATION_REFERENCE,
    },
    {
      outcome: 'rejected' as const,
      reason: 'provider_confirmed_not_applied' as const,
      reference: 'free-form provider note',
    },
  ])('rejects incompatible or unbounded reconciliation input before transport', async (body) => {
    let transportCalled = false;
    server.use(
      http.post(MATCH_ANY_API_ORIGIN.reconcileReceipt, () => {
        transportCalled = true;
        return HttpResponse.json({});
      }),
    );

    await expect(
      adminRemnawaveConnectionsApi.reconcileDropReceipt(RECEIPT_ID, body),
    ).rejects.toThrow(/Connection drop reconciliation/);
    expect(transportCalled).toBe(false);
  });

  it('fails closed on partial reconciliation metadata and mismatched terminal reason', async () => {
    server.use(
      http.get(MATCH_ANY_API_ORIGIN.receipt, () => HttpResponse.json({
        ...UNRESOLVED_RECEIPT,
        state: 'accepted',
        expires_at: '2026-09-01T12:00:00Z',
        expires_in_seconds: 7_200,
        requires_reconciliation: false,
        reconciled_at: '2026-08-31T10:05:00Z',
        reconciliation_reason: 'provider_confirmed_not_applied',
        reconciliation_reference: RECONCILIATION_REFERENCE,
      })),
    );

    await expect(
      adminRemnawaveConnectionsApi.getDropReceipt(RECEIPT_ID),
    ).rejects.toThrow('Invalid admin connection drop reconciliation outcome response');
  });
});

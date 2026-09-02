import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { remnawaveOperatorApi } from '../remnawave-operator';

const API = /https?:\/\/localhost(?::\d+)?\/api\/v1\/admin\/remnawave-operator/;
const UUID = '550e8400-e29b-41d4-a716-446655440000';
const KEY = '920568b9-d402-43a2-b8a8-e945d8d28ee7'; // gitleaks:allow -- deterministic UUID fixture

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('remnawaveOperatorApi', () => {
  it('reads a bounded tag inventory from the exact resource route', async () => {
    server.use(
      http.get(new RegExp(`${API.source}/tags/nodes$`), () =>
        HttpResponse.json({ resource: 'nodes', tags: ['EDGE_RU'] })),
    );

    await expect(remnawaveOperatorApi.getTags('nodes')).resolves.toMatchObject({
      data: { resource: 'nodes', tags: ['EDGE_RU'] },
    });
  });

  it('sends an exact tag mutation with the caller-owned idempotency key', async () => {
    let body: unknown;
    let idempotencyKey: string | null = null;
    server.use(
      http.patch(new RegExp(`${API.source}/tags/config-profiles$`), async ({ request }) => {
        body = await request.json();
        idempotencyKey = request.headers.get('Idempotency-Key');
        return HttpResponse.json({ uuid: UUID, tags: ['EDGE_RU'] });
      }),
    );

    await expect(
      remnawaveOperatorApi.setTags(
        'config-profiles',
        { uuid: UUID, tags: ['EDGE_RU'] },
        KEY,
      ),
    ).resolves.toEqual({
      kind: 'committed',
      resource: { uuid: UUID, tags: ['EDGE_RU'] },
    });
    expect(body).toEqual({ uuid: UUID, tags: ['EDGE_RU'] });
    expect(idempotencyKey).toBe(KEY);
  });

  it('preserves a 202 as reconciliation instead of reporting mutation success', async () => {
    server.use(
      http.post(new RegExp(`${API.source}/shared-lists/actions/sync$`), ({ request }) => {
        expect(request.headers.get('Idempotency-Key')).toBe(KEY);
        return HttpResponse.json({
          attempt_id: UUID,
          state: 'reconciliation_required',
          resource_kind: 'shared_list',
          requires_reconciliation: true,
        }, { status: 202 });
      }),
    );

    await expect(remnawaveOperatorApi.syncSharedList('routing/ru', KEY)).resolves.toEqual({
      kind: 'reconciliation',
      receipt: {
        attempt_id: UUID,
        state: 'reconciliation_required',
        resource_kind: 'shared_list',
        requires_reconciliation: true,
      },
    });
  });

  it('fails closed when a 202 response is missing its durable receipt', async () => {
    server.use(
      http.post(new RegExp(`${API.source}/snippets/actions/sync$`), () =>
        HttpResponse.json({ state: 'accepted' }, { status: 202 })),
    );

    await expect(remnawaveOperatorApi.syncRootSnippet('headers', KEY)).rejects.toThrow(
      'Invalid Remnawave reconciliation receipt',
    );
  });

  it('normalizes an empty 204 delete without requiring a response body', async () => {
    server.use(
      http.delete(new RegExp(`${API.source}/node-integrations/${UUID}$`), ({ request }) => {
        expect(request.headers.get('Idempotency-Key')).toBe(KEY);
        return new HttpResponse(null, { status: 204 });
      }),
    );

    await expect(remnawaveOperatorApi.deleteNodeIntegration(UUID, KEY)).resolves.toEqual({
      kind: 'committed',
      resource: null,
    });
  });

  it('uses the by-name query route and never places a shared-list name in the path', async () => {
    let pathname = '';
    let queryName: string | null = null;
    server.use(
      http.get(new RegExp(`${API.source}/shared-lists/by-name(?:\\?.*)?$`), ({ request }) => {
        const url = new URL(request.url);
        pathname = url.pathname;
        queryName = url.searchParams.get('name');
        return HttpResponse.json({ name: 'routing/ru', config: { type: 'cidr', items: [] } });
      }),
    );

    await remnawaveOperatorApi.getSharedList('routing/ru');

    expect(pathname).toBe('/api/v1/admin/remnawave-operator/shared-lists/by-name');
    expect(queryName).toBe('routing/ru');
  });
});

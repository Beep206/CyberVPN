import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { partnerRemnawaveStatusApi } from '../remnawave-status';

const API_BASE = '*/api/v1';
const WORKSPACE_UUID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const PROFILE_UUID = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const INTEGRATION_UUID = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
const ATTEMPT_UUID = 'dddddddd-dddd-4ddd-8ddd-dddddddddddd';

describe('partnerRemnawaveStatusApi', () => {
  it('returns only workspace-safe fields from the scoped endpoint', async () => {
    let requestedPath = '';
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/vpn-service-status`, ({ request }) => {
        requestedPath = new URL(request.url).pathname;
        return HttpResponse.json({
          workspace_id: 'workspace_001',
          capabilities: {
            connections: true,
            usage: false,
            devices: true,
            node_ssh: true,
          },
          assigned_resources: 4,
          degraded: true,
          degraded_reason: 'safe_workspace_reason',
          node_ip: '203.0.113.5',
          integration_uuid: '11111111-1111-1111-1111-111111111111',
        });
      }),
    );

    const status = await partnerRemnawaveStatusApi.getWorkspaceStatus('workspace_001');

    expect(requestedPath).toBe('/api/v1/partner-workspaces/workspace_001/vpn-service-status');
    expect(status).toEqual({
      workspace_id: 'workspace_001',
      capabilities: { connections: true, usage: false, devices: true },
      assigned_resources: 4,
      degraded: true,
      degraded_reason: 'safe_workspace_reason',
    });
    expect(status).not.toHaveProperty('node_ip');
    expect(status.capabilities).not.toHaveProperty('node_ssh');
  });

  it('rejects a response scoped to a different workspace', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/vpn-service-status`, () =>
        HttpResponse.json({
          workspace_id: 'workspace_002',
          capabilities: { connections: true, usage: true, devices: true },
          assigned_resources: 2,
          degraded: false,
          degraded_reason: null,
        }),
      ),
    );

    let rejection: unknown;
    try {
      await partnerRemnawaveStatusApi.getWorkspaceStatus('workspace_001');
    } catch (error) {
      rejection = error;
    }

    expect(rejection).toBeInstanceOf(Error);
    if (!(rejection instanceof Error)) throw new Error('Expected parser rejection');
    expect(rejection.message).toBe(
      'Invalid partner VPN service status response',
    );
  });

  it('lists only parsed object-grant resources and preserves bounded pagination', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/remnawave/resources`, ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get('limit')).toBe('50');
        expect(url.searchParams.get('offset')).toBe('50');
        return HttpResponse.json({
          workspace_id: 'workspace_001',
          items: [{
            workspace_id: 'workspace_001',
            resource_type: 'service_identity',
            resource_uuid: '11111111-1111-1111-1111-111111111111',
            effective_permissions: ['remnawave_read', 'remnawave_execute'],
            available_operations: ['inspect_assignment'],
            unavailable_operations: ['mutate_resource', 'execute_resource'],
            forbidden_operations: ['browser_ssh'],
            provider_details_available: false,
            safe_mutations: [],
            node_ip: '203.0.113.10',
            integration_uuid: '22222222-2222-2222-2222-222222222222',
            numeric_user_id: 42,
          }],
          total: 51,
          next_offset: null,
          capabilities: {
            inspect_assignment: true,
            mutate_resource: false,
            execute_resource: false,
            browser_ssh: false,
            mutation_unavailable_reason: 'no_current_write_granted_safe_mutation',
            safe_mutations: [],
          },
        });
      }),
    );

    const result = await partnerRemnawaveStatusApi.listWorkspaceResources('workspace_001', 50);

    expect(result.items).toHaveLength(1);
    expect(result.items[0]).toEqual({
      workspace_id: 'workspace_001',
      resource_type: 'service_identity',
      resource_uuid: '11111111-1111-1111-1111-111111111111',
      effective_permissions: ['remnawave_read', 'remnawave_execute'],
      available_operations: ['inspect_assignment'],
      unavailable_operations: ['mutate_resource', 'execute_resource'],
      forbidden_operations: ['browser_ssh'],
      provider_details_available: false,
      safe_mutations: [],
    });
    expect(result.items[0]).not.toHaveProperty('node_ip');
    expect(result.items[0]).not.toHaveProperty('integration_uuid');
    expect(result.items[0]).not.toHaveProperty('numeric_user_id');
    expect(result.next_offset).toBeNull();
  });

  it('binds detail responses to the requested workspace, type, and UUID', async () => {
    server.use(
      http.get(
        `${API_BASE}/partner-workspaces/workspace_001/remnawave/resources/host/11111111-1111-1111-1111-111111111111`,
        () => HttpResponse.json({
          workspace_id: 'workspace_001',
          resource_type: 'node',
          resource_uuid: '11111111-1111-1111-1111-111111111111',
          effective_permissions: ['remnawave_read'],
          available_operations: ['inspect_assignment'],
          unavailable_operations: ['mutate_resource', 'execute_resource'],
          forbidden_operations: ['browser_ssh'],
          provider_details_available: false,
          safe_mutations: [],
        }),
      ),
    );

    let rejection: unknown;
    try {
      await partnerRemnawaveStatusApi.getWorkspaceResource(
        'workspace_001',
        'host',
        '11111111-1111-1111-1111-111111111111',
      );
    } catch (error) {
      rejection = error;
    }
    expect(rejection).toBeInstanceOf(Error);
    if (!(rejection instanceof Error)) throw new Error('Expected parser rejection');
    expect(rejection.message).toBe('Invalid partner Remnawave resource response');
  });

  it('accepts only the grant-aware union of currently effective safe mutations', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/${WORKSPACE_UUID}/remnawave/resources`, () =>
        HttpResponse.json({
          workspace_id: WORKSPACE_UUID,
          items: [{
            workspace_id: WORKSPACE_UUID,
            resource_type: 'profile',
            resource_uuid: PROFILE_UUID,
            effective_permissions: ['remnawave_read', 'remnawave_write'],
            available_operations: ['inspect_assignment', 'mutate_resource'],
            unavailable_operations: ['execute_resource'],
            forbidden_operations: ['browser_ssh'],
            provider_details_available: false,
            safe_mutations: ['profile_tags'],
          }],
          total: 1,
          next_offset: null,
          capabilities: {
            inspect_assignment: true,
            mutate_resource: true,
            execute_resource: false,
            browser_ssh: false,
            mutation_unavailable_reason: 'limited_to_explicit_profile_and_integration_grants',
            safe_mutations: ['profile_tags'],
          },
        }),
      ),
    );

    const result = await partnerRemnawaveStatusApi.listWorkspaceResources(WORKSPACE_UUID);

    expect(result.capabilities).toMatchObject({
      mutate_resource: true,
      safe_mutations: ['profile_tags'],
    });
    expect(result.items[0]?.safe_mutations).toEqual(['profile_tags']);
  });

  it('rejects a list that hides an effective item mutation from global capabilities', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/${WORKSPACE_UUID}/remnawave/resources`, () =>
        HttpResponse.json({
          workspace_id: WORKSPACE_UUID,
          items: [{
            workspace_id: WORKSPACE_UUID,
            resource_type: 'profile',
            resource_uuid: PROFILE_UUID,
            effective_permissions: ['remnawave_read', 'remnawave_write'],
            available_operations: ['inspect_assignment', 'mutate_resource'],
            unavailable_operations: ['execute_resource'],
            forbidden_operations: ['browser_ssh'],
            provider_details_available: false,
            safe_mutations: ['profile_tags'],
          }],
          total: 1,
          next_offset: null,
          capabilities: {
            inspect_assignment: true,
            mutate_resource: false,
            execute_resource: false,
            browser_ssh: false,
            mutation_unavailable_reason: 'no_current_write_granted_safe_mutation',
            safe_mutations: [],
          },
        }),
      ),
    );

    let rejection: unknown;
    try {
      await partnerRemnawaveStatusApi.listWorkspaceResources(WORKSPACE_UUID);
    } catch (error) {
      rejection = error;
    }
    expect(rejection).toBeInstanceOf(Error);
    if (!(rejection instanceof Error)) throw new Error('Expected capability-union rejection');
    expect(rejection.message).toBe('Invalid partner Remnawave resource list response');
  });

  it('fails closed when the global capability advertises browser SSH', async () => {
    server.use(
      http.get(`${API_BASE}/partner-workspaces/workspace_001/remnawave/resources`, () =>
        HttpResponse.json({
          workspace_id: 'workspace_001',
          items: [],
          total: 0,
          next_offset: null,
          capabilities: {
            inspect_assignment: true,
            mutate_resource: false,
            execute_resource: false,
            browser_ssh: true,
            mutation_unavailable_reason: 'no_current_write_granted_safe_mutation',
            safe_mutations: [],
          },
        }),
      ),
    );

    let rejection: unknown;
    try {
      await partnerRemnawaveStatusApi.listWorkspaceResources('workspace_001');
    } catch (error) {
      rejection = error;
    }
    expect(rejection).toBeInstanceOf(Error);
    if (!(rejection instanceof Error)) throw new Error('Expected parser rejection');
    expect(rejection.message).toBe('Invalid partner Remnawave resource list response');
  });

  it('rejects an unbounded inventory offset before sending a request', async () => {
    let rejection: unknown;
    try {
      await partnerRemnawaveStatusApi.listWorkspaceResources('workspace_001', 10_001);
    } catch (error) {
      rejection = error;
    }

    expect(rejection).toBeInstanceOf(Error);
    if (!(rejection instanceof Error)) throw new Error('Expected offset rejection');
    expect(rejection.message).toBe('Invalid partner Remnawave resource offset');
  });

  it('sends one exact profile-tags mutation with the caller UUID idempotency key', async () => {
    let calls = 0;
    server.use(
      http.patch(
        `${API_BASE}/partner-workspaces/${WORKSPACE_UUID}/remnawave/resources/profile/${PROFILE_UUID}/tags`,
        async ({ request }) => {
          calls += 1;
          expect(request.headers.get('Idempotency-Key')).toBe(ATTEMPT_UUID);
          expect(await request.json()).toEqual({ tags: ['EDGE:RU', 'VISION'] });
          return HttpResponse.json({
            resource_uuid: PROFILE_UUID,
            tags: ['EDGE:RU', 'VISION'],
            config: { private: true },
          });
        },
      ),
    );

    const result = await partnerRemnawaveStatusApi.updateProfileTags(
      WORKSPACE_UUID,
      PROFILE_UUID,
      { tags: ['EDGE:RU', 'VISION'] },
      ATTEMPT_UUID,
    );

    expect(calls).toBe(1);
    expect(result).toEqual({
      kind: 'completed',
      value: { resource_uuid: PROFILE_UUID, tags: ['EDGE:RU', 'VISION'] },
    });
    expect(JSON.stringify(result)).not.toContain('private');
  });

  it('parses a 202 reconciliation receipt without retrying the mutation', async () => {
    let calls = 0;
    server.use(
      http.patch(
        `${API_BASE}/partner-workspaces/${WORKSPACE_UUID}/remnawave/resources/profile/${PROFILE_UUID}/tags`,
        () => {
          calls += 1;
          return HttpResponse.json({
            attempt_id: ATTEMPT_UUID,
            state: 'reconciliation_required',
            resource_type: 'profile',
            resource_uuid: PROFILE_UUID,
            requires_reconciliation: true,
          }, { status: 202 });
        },
      ),
    );

    const result = await partnerRemnawaveStatusApi.updateProfileTags(
      WORKSPACE_UUID,
      PROFILE_UUID,
      { tags: [] },
      ATTEMPT_UUID,
    );

    expect(calls).toBe(1);
    expect(result.kind).toBe('reconciliation_required');
    if (result.kind !== 'reconciliation_required') throw new Error('Expected reconciliation receipt');
    expect(result.receipt).toMatchObject({
      attempt_id: ATTEMPT_UUID,
      resource_type: 'profile',
      resource_uuid: PROFILE_UUID,
      requires_reconciliation: true,
    });
  });

  it('updates only allowlisted integration metadata and strips response extras', async () => {
    server.use(
      http.patch(
        `${API_BASE}/partner-workspaces/${WORKSPACE_UUID}/remnawave/resources/integration/${INTEGRATION_UUID}/metadata`,
        async ({ request }) => {
          expect(request.headers.get('Idempotency-Key')).toBe(ATTEMPT_UUID);
          expect(await request.json()).toEqual({ name: 'Usage relay', description: null });
          return HttpResponse.json({
            resource_uuid: INTEGRATION_UUID,
            name: 'Usage relay',
            description: null,
            config: { token: 'must-not-reach-browser-state' },
            restart_nodes: true,
          });
        },
      ),
    );

    const result = await partnerRemnawaveStatusApi.updateIntegrationMetadata(
      WORKSPACE_UUID,
      INTEGRATION_UUID,
      { name: 'Usage relay', description: null },
      ATTEMPT_UUID,
    );

    expect(result).toEqual({
      kind: 'completed',
      value: {
        resource_uuid: INTEGRATION_UUID,
        name: 'Usage relay',
        description: null,
      },
    });
    expect(JSON.stringify(result)).not.toContain('token');
    expect(JSON.stringify(result)).not.toContain('restart_nodes');
  });

  it('rejects unsafe mutation input before transport', async () => {
    let calls = 0;
    server.use(http.patch(`${API_BASE}/*`, () => {
      calls += 1;
      return HttpResponse.json({});
    }));

    const rejections: unknown[] = [];
    for (const request of [
      () => partnerRemnawaveStatusApi.updateProfileTags(
        WORKSPACE_UUID,
        PROFILE_UUID,
        { tags: ['lowercase'] },
        ATTEMPT_UUID,
      ),
      () => partnerRemnawaveStatusApi.updateProfileTags(
        WORKSPACE_UUID,
        PROFILE_UUID,
        { tags: ['VISION', 'VISION'] },
        ATTEMPT_UUID,
      ),
      () => partnerRemnawaveStatusApi.updateIntegrationMetadata(
        WORKSPACE_UUID,
        INTEGRATION_UUID,
        {},
        ATTEMPT_UUID,
      ),
      () => partnerRemnawaveStatusApi.updateIntegrationMetadata(
        WORKSPACE_UUID,
        INTEGRATION_UUID,
        { name: ' x ' },
        ATTEMPT_UUID,
      ),
    ]) {
      try {
        await request();
      } catch (error) {
        rejections.push(error);
      }
    }

    expect(rejections).toHaveLength(4);
    expect(rejections.every((error) => error instanceof Error)).toBe(true);
    expect(rejections.map((error) => error instanceof Error ? error.message : '')).toEqual([
      'Invalid partner profile-tags mutation request',
      'Invalid partner profile-tags mutation request',
      'Invalid partner integration-metadata mutation request',
      'Invalid partner integration-metadata mutation request',
    ]);
    expect(calls).toBe(0);
  });

  it('rejects receipts and completed responses for another exact resource', async () => {
    server.use(
      http.patch(
        `${API_BASE}/partner-workspaces/${WORKSPACE_UUID}/remnawave/resources/integration/${INTEGRATION_UUID}/metadata`,
        () => HttpResponse.json({
          attempt_id: ATTEMPT_UUID,
          state: 'accepted',
          resource_type: 'integration',
          resource_uuid: PROFILE_UUID,
          requires_reconciliation: false,
        }, { status: 202 }),
      ),
    );

    let rejection: unknown;
    try {
      await partnerRemnawaveStatusApi.updateIntegrationMetadata(
        WORKSPACE_UUID,
        INTEGRATION_UUID,
        { name: 'Usage relay' },
        ATTEMPT_UUID,
      );
    } catch (error) {
      rejection = error;
    }
    expect(rejection).toBeInstanceOf(Error);
    if (!(rejection instanceof Error)) throw new Error('Expected receipt parser rejection');
    expect(rejection.message).toBe('Invalid partner Remnawave mutation receipt');
  });
});

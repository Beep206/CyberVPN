import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import {
  configProfilesApi,
  helixApi,
  hostsApi,
  xrayApi,
} from '../infrastructure';

const MATCH_ANY_API_ORIGIN = {
  hosts: /https?:\/\/localhost(?::\d+)?\/api\/v1\/hosts\/$/,
  hostById: /https?:\/\/localhost(?::\d+)?\/api\/v1\/hosts\/[^/]+$/,
  configProfiles: /https?:\/\/localhost(?::\d+)?\/api\/v1\/config-profiles\/$/,
  helixRollouts: /https?:\/\/localhost(?::\d+)?\/api\/v1\/helix\/admin\/rollouts$/,
  xrayUpdateConfig: /https?:\/\/localhost(?::\d+)?\/api\/v1\/xray\/update-config$/,
};

beforeEach(() => {
  localStorage.clear();
  window.location.href = 'http://localhost:3000';
});

afterEach(() => {
  window.location.href = 'http://localhost:3000';
});

describe('hostsApi admin operations', () => {
  it('serializes the exact Remnawave 3.4 host create shape', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.hosts, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          uuid: 'host_001',
          viewPosition: 1,
          remark: 'Edge Host EU',
          address: 'edge-eu.ozoxy.ru',
          port: 443,
          sni: 'edge-eu.ozoxy.ru',
          host: 'edge-eu.ozoxy.ru',
          path: '/reality',
          alpn: 'h2,http/1.1',
          isDisabled: false,
        }, { status: 201 });
      }),
    );

    const response = await hostsApi.create({
      inbound: {
        configProfileUuid: '550e8400-e29b-41d4-a716-446655440000',
        configProfileInboundUuid: '550e8400-e29b-41d4-a716-446655440001',
      },
      remark: 'Edge Host EU',
      address: 'edge-eu.ozoxy.ru',
      port: 443,
      sni: ['edge-eu.ozoxy.ru'],
      host: ['edge-eu.ozoxy.ru'],
      path: ['/reality'],
      alpn: 'h2,http/1.1',
      isDisabled: false,
      securityLayer: 'TLS',
      isHidden: false,
      overrideSniFromAddress: false,
      keepSniBlank: false,
      shuffleHost: false,
      mihomoX25519: false,
    });

    expect(response.status).toBe(201);
    expect(response.data.uuid).toBe('host_001');
    expect(capturedBody).toMatchObject({
      remark: 'Edge Host EU',
      address: 'edge-eu.ozoxy.ru',
      host: ['edge-eu.ozoxy.ru'],
      securityLayer: 'TLS',
    });
  });

  it('updates a host by UUID route', async () => {
    let updatedUuid = '';

    server.use(
      http.put(MATCH_ANY_API_ORIGIN.hostById, async ({ request }) => {
        updatedUuid = new URL(request.url).pathname.split('/').at(-1) ?? '';
        const body = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          uuid: updatedUuid,
          remark: body.remark,
          address: body.address,
          port: body.port,
          sni: 'edge-prime.ozoxy.ru',
          host: null,
          path: null,
          alpn: null,
          isDisabled: body.isDisabled ?? false,
        });
      }),
    );

    const response = await hostsApi.update('host_001', {
      remark: 'Edge Host EU Prime',
      address: 'edge-prime.ozoxy.ru',
      port: 8443,
      isDisabled: true,
    });

    expect(response.status).toBe(200);
    expect(updatedUuid).toBe('host_001');
    expect(response.data.remark).toBe('Edge Host EU Prime');
  });
});

describe('configProfilesApi admin operations', () => {
  it('creates a config profile with default flag', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.configProfiles, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          uuid: 'profile_001',
          name: 'Clash Mobile',
          profileType: 'clash',
          content: 'mixed-port: 7890',
          description: 'Optimized for mobile clients',
          isDefault: true,
        });
      }),
    );

    const response = await configProfilesApi.create({
      name: 'Clash Mobile',
      profile_type: 'clash',
      content: 'mixed-port: 7890',
      description: 'Optimized for mobile clients',
      is_default: true,
    });

    expect(response.status).toBe(200);
    expect(response.data.uuid).toBe('profile_001');
    expect(capturedBody).toMatchObject({
      profile_type: 'clash',
      is_default: true,
    });
  });
});

describe('helixApi admin operations', () => {
  it('publishes a rollout with the expected target nodes', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.helixRollouts, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          rollout_id: 'rollout-stable-apr10',
          batch_id: 'batch-2026-04-10',
          manifest_version: 'manifest-v2026-04-10-1',
          channel: 'stable',
          desired_state: 'active',
          created_at: '2026-04-10T10:30:00Z',
          updated_at: '2026-04-10T10:30:00Z',
          current_batch: {
            batch_id: 'batch-2026-04-10',
            manifest_version: 'manifest-v2026-04-10-1',
            target_nodes: 2,
            completed_nodes: 0,
            failed_nodes: 0,
            paused_at: null,
          },
        });
      }),
    );

    const response = await helixApi.publishRollout({
      rollout_id: 'rollout-stable-apr10',
      batch_id: 'batch-2026-04-10',
      channel: 'stable',
      manifest_version: 'manifest-v2026-04-10-1',
      target_node_ids: ['service-node-1', 'service-node-2'],
      pause_on_rollback_spike: true,
      revoke_on_manifest_error: true,
    });

    expect(response.status).toBe(200);
    expect(response.data.rollout_id).toBe('rollout-stable-apr10');
    expect(capturedBody).toMatchObject({
      rollout_id: 'rollout-stable-apr10',
      target_node_ids: ['service-node-1', 'service-node-2'],
    });
  });
});

describe('xrayApi admin operations', () => {
  it('updates xray config sections via the update endpoint', async () => {
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(MATCH_ANY_API_ORIGIN.xrayUpdateConfig, async ({ request }) => {
        capturedBody = (await request.json()) as Record<string, unknown>;

        return HttpResponse.json({
          log: capturedBody?.log ?? { loglevel: 'warning' },
          inbounds: capturedBody?.inbounds ?? [],
          outbounds: capturedBody?.outbounds ?? [],
          routing: capturedBody?.routing ?? { rules: [] },
          dns: capturedBody?.dns ?? {},
          policy: capturedBody?.policy ?? {},
        });
      }),
    );

    const response = await xrayApi.updateConfig({
      log: { loglevel: 'warning' },
      inbounds: [{ tag: 'vless-in', port: 443 }],
      outbounds: [{ protocol: 'freedom', tag: 'direct' }],
      routing: { rules: [] },
    });

    expect(response.status).toBe(200);
    expect(capturedBody).toMatchObject({
      log: { loglevel: 'warning' },
      routing: { rules: [] },
    });
    expect(Array.isArray(response.data.inbounds)).toBe(true);
  });
});

import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { CANONICAL_AUTH_REALM_HEADER } from '@/lib/api/client';
import { server } from '@/test/mocks/server';
import { FRESH_AUTH_GRANT_ID_HEADER } from '../fresh-auth';
import { passkeysApi } from '../passkeys';

const API_BASE = '*/api/v1';

describe('partner passkeysApi', () => {
  it('preserves partner auth realm on passkey authentication requests', async () => {
    let capturedRealm: string | null = null;
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.post(`${API_BASE}/auth/passkeys/authentication/options`, async ({ request }) => {
        capturedRealm = request.headers.get(CANONICAL_AUTH_REALM_HEADER);
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          challengeId: 'challenge-partner-001',
          expiresAt: '2026-06-03T12:00:00Z',
          publicKey: { challenge: 'cGFydG5lcg' },
        });
      }),
    );

    const response = await passkeysApi.createAuthenticationOptions({
      identifier: 'operator@partner.example',
    });

    expect(response.data.challengeId).toBe('challenge-partner-001');
    expect(capturedRealm).toBe('partner');
    expect(capturedBody).toMatchObject({
      conditional: false,
      identifier: 'operator@partner.example',
    });
  });

  it('uses workspace passkey policy patch and compliance endpoints with partner realm preserved', async () => {
    let capturedPatchRealm: string | null = null;
    let capturedPatchFreshAuthGrantId: string | null = null;
    let capturedPatchBody: Record<string, unknown> | null = null;

    server.use(
      http.get(`${API_BASE}/partner-workspaces/:workspaceId/security/passkeys/policy`, ({ params }) =>
        HttpResponse.json({
          operatorCompliance: {
            activeMembers: 3,
            operatorsMissingActivePasskeys: 1,
            operatorsWithActivePasskeys: 2,
            workspaceId: params.workspaceId,
          },
          policy: {
            adminCountsAsMfa: false,
            allowedOrigins: ['https://partner.cybervpn.example'],
            authenticationEnabled: true,
            browserTimeoutMs: 60000,
            challengeTtlSeconds: 300,
            conditionalUiEnabled: true,
            enabled: true,
            freshAuthTtlSeconds: 300,
            realm_key: 'partner',
            reauthenticationEnabled: true,
            registrationEnabled: true,
            rp_id: 'partner.cybervpn.example',
            rp_name: 'CyberVPN Partner',
            surface: 'partner',
            userVerification: 'required',
            workspacePolicyEnabled: true,
          },
          workspaceId: params.workspaceId,
          workspaceKey: 'north-star-growth',
          workspaceMfaRequired: false,
          workspacePasskeysPreferred: false,
          workspacePolicyUpdatedAt: null,
          workspaceStatus: 'active',
        })),
      http.patch(`${API_BASE}/partner-workspaces/:workspaceId/security/passkeys/policy`, async ({ params, request }) => {
        capturedPatchRealm = request.headers.get(CANONICAL_AUTH_REALM_HEADER);
        capturedPatchFreshAuthGrantId = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
        capturedPatchBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          operatorCompliance: {
            activeMembers: 3,
            operatorsMissingActivePasskeys: 0,
            operatorsWithActivePasskeys: 3,
            workspaceId: params.workspaceId,
          },
          policy: {
            adminCountsAsMfa: false,
            allowedOrigins: ['https://partner.cybervpn.example'],
            authenticationEnabled: true,
            browserTimeoutMs: 60000,
            challengeTtlSeconds: 300,
            conditionalUiEnabled: true,
            enabled: true,
            freshAuthTtlSeconds: 300,
            realm_key: 'partner',
            reauthenticationEnabled: true,
            registrationEnabled: true,
            rp_id: 'partner.cybervpn.example',
            rp_name: 'CyberVPN Partner',
            surface: 'partner',
            userVerification: 'required',
            workspacePolicyEnabled: true,
          },
          workspaceId: params.workspaceId,
          workspaceKey: 'north-star-growth',
          workspaceMfaRequired: true,
          workspacePasskeysPreferred: true,
          workspacePolicyUpdatedAt: '2026-06-03T12:30:00Z',
          workspaceStatus: 'active',
        });
      }),
      http.get(`${API_BASE}/partner-workspaces/:workspaceId/security/passkeys/compliance`, ({ params }) =>
        HttpResponse.json({
          credentials: [],
          operatorCompliance: {
            activeMembers: 3,
            operatorsMissingActivePasskeys: 1,
            operatorsWithActivePasskeys: 2,
            workspaceId: params.workspaceId,
          },
          policy: {
            adminCountsAsMfa: false,
            allowedOrigins: ['https://partner.cybervpn.example'],
            authenticationEnabled: true,
            browserTimeoutMs: 60000,
            challengeTtlSeconds: 300,
            conditionalUiEnabled: true,
            enabled: true,
            freshAuthTtlSeconds: 300,
            realm_key: 'partner',
            reauthenticationEnabled: true,
            registrationEnabled: true,
            rp_id: 'partner.cybervpn.example',
            rp_name: 'CyberVPN Partner',
            surface: 'partner',
            userVerification: 'required',
            workspacePolicyEnabled: true,
          },
          summary: {
            activeCredentials: 2,
            cloneSuspectedCredentials: 0,
            generatedAt: '2026-06-03T12:00:00Z',
            principalsWithActivePasskeys: 2,
            revokedCredentials: 0,
            staleCredentials: 0,
          },
          workspaceId: params.workspaceId,
          workspaceKey: 'north-star-growth',
          workspaceMfaRequired: false,
          workspacePasskeysPreferred: false,
          workspacePolicyUpdatedAt: null,
          workspaceStatus: 'active',
        })),
    );

    const policy = await passkeysApi.getWorkspacePolicy('workspace_001');
    const updatedPolicy = await passkeysApi.updateWorkspacePolicy('workspace_001', {
      changeReason: 'partner security rollout',
      preferPasskeys: true,
      requireMfaForWorkspace: true,
    }, {
      freshAuthGrantId: 'fresh-workspace-policy-grant',
    });
    const compliance = await passkeysApi.getWorkspaceCompliance('workspace_001');

    expect(policy.data.operatorCompliance.operatorsMissingActivePasskeys).toBe(1);
    expect(updatedPolicy.data.workspacePasskeysPreferred).toBe(true);
    expect(updatedPolicy.data.workspaceMfaRequired).toBe(true);
    expect(compliance.data.summary.activeCredentials).toBe(2);
    expect(capturedPatchRealm).toBe('partner');
    expect(capturedPatchFreshAuthGrantId).toBe('fresh-workspace-policy-grant');
    expect(capturedPatchBody).toEqual({
      changeReason: 'partner security rollout',
      preferPasskeys: true,
      requireMfaForWorkspace: true,
    });
  });
});

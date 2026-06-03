import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { FRESH_AUTH_GRANT_ID_HEADER } from '../fresh-auth';
import { passkeysApi } from '../passkeys';

const API_BASE = '*/api/v1';

describe('passkeysApi', () => {
  it('uses passkey auth, management, admin policy, and compliance endpoints', async () => {
    let capturedAuthenticationOptionsBody: Record<string, unknown> | null = null;
    let capturedVerifyBody: Record<string, unknown> | null = null;
    let capturedRenameBody: Record<string, unknown> | null = null;
    let capturedRenameFreshAuthGrantId: string | null = null;
    let capturedDeleteFreshAuthGrantId: string | null = null;
    let capturedPolicyBody: Record<string, unknown> | null = null;
    let capturedPolicyFreshAuthGrantId: string | null = null;

    server.use(
      http.post(`${API_BASE}/auth/passkeys/authentication/options`, async ({ request }) => {
        capturedAuthenticationOptionsBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          challengeId: 'challenge-admin-001',
          expiresAt: '2026-06-03T12:00:00Z',
          publicKey: { challenge: 'YWRtaW4' },
        });
      }),
      http.post(`${API_BASE}/auth/passkeys/authentication/verify`, async ({ request }) => {
        capturedVerifyBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          access_token: 'access',
          expires_in: 3600,
          refresh_token: 'refresh',
          token_type: 'bearer',
        });
      }),
      http.get(`${API_BASE}/auth/passkeys`, () => HttpResponse.json({
        credentials: [
          {
            backedUp: true,
            createdAt: '2026-06-03T10:00:00Z',
            credentialType: 'public-key',
            deviceType: 'platform',
            id: '7d705dcc-75f4-49b4-a41e-a70ae80de188',
            label: 'Admin laptop',
            lastUsedAt: null,
            revokedAt: null,
            status: 'active',
            transports: ['internal'],
            userVerified: true,
          },
        ],
      })),
      http.patch(`${API_BASE}/auth/passkeys/:credentialId`, async ({ request }) => {
        capturedRenameBody = (await request.json()) as Record<string, unknown>;
        capturedRenameFreshAuthGrantId = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
        return HttpResponse.json({
          backedUp: true,
          createdAt: '2026-06-03T10:00:00Z',
          credentialType: 'public-key',
          deviceType: 'platform',
          id: '7d705dcc-75f4-49b4-a41e-a70ae80de188',
          label: 'Renamed admin laptop',
          lastUsedAt: null,
          revokedAt: null,
          status: 'active',
          transports: ['internal'],
          userVerified: true,
        });
      }),
      http.delete(`${API_BASE}/auth/passkeys/:credentialId`, ({ params, request }) => {
        capturedDeleteFreshAuthGrantId = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
        return HttpResponse.json({
          id: params.credentialId,
          status: 'revoked',
        });
      }),
      http.patch(`${API_BASE}/security/passkeys/policy`, async ({ request }) => {
        capturedPolicyBody = (await request.json()) as Record<string, unknown>;
        capturedPolicyFreshAuthGrantId = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
        return HttpResponse.json({
          adminCountsAsMfa: true,
          allowedOrigins: ['https://admin.cybervpn.example'],
          authenticationEnabled: true,
          browserTimeoutMs: 60000,
          challengeTtlSeconds: 300,
          conditionalUiEnabled: true,
          configuredEnabled: true,
          enabled: true,
          freshAuthTtlSeconds: 300,
          globalEnabled: true,
          policySource: 'system_config',
          realm_key: 'admin',
          reauthenticationEnabled: true,
          registrationEnabled: false,
          rp_id: 'admin.cybervpn.example',
          rp_name: 'CyberVPN Admin',
          securityDashboardEnabled: true,
          surface: 'admin',
          surfaceEnabled: true,
          updatedAt: '2026-06-03T12:30:00Z',
          updatedBy: '0e2b5f1e-9584-4209-b238-e70208e5ee2a',
          userVerification: 'required',
        });
      }),
      http.get(`${API_BASE}/security/passkeys/compliance`, () => HttpResponse.json({
        credentials: [],
        policy: {
          adminCountsAsMfa: false,
          allowedOrigins: ['https://admin.cybervpn.example'],
          authenticationEnabled: true,
          browserTimeoutMs: 60000,
          challengeTtlSeconds: 300,
          conditionalUiEnabled: true,
          configuredEnabled: true,
          enabled: true,
          freshAuthTtlSeconds: 300,
          globalEnabled: true,
          policySource: 'settings',
          realm_key: 'admin',
          reauthenticationEnabled: true,
          registrationEnabled: true,
          rp_id: 'admin.cybervpn.example',
          rp_name: 'CyberVPN Admin',
          securityDashboardEnabled: true,
          surface: 'admin',
          surfaceEnabled: true,
          userVerification: 'required',
        },
        summary: {
          activeCredentials: 1,
          cloneSuspectedCredentials: 0,
          generatedAt: '2026-06-03T12:00:00Z',
          principalsWithActivePasskeys: 1,
          revokedCredentials: 0,
          staleCredentials: 0,
        },
      })),
    );

    const options = await passkeysApi.createAuthenticationOptions({
      identifier: 'admin@cybervpn.example',
    });
    const verify = await passkeysApi.verifyAuthentication({
      challengeId: options.data.challengeId,
      credential: { id: 'credential-response' },
    });
    const list = await passkeysApi.listPasskeys();
    const rename = await passkeysApi.renamePasskey(
      '7d705dcc-75f4-49b4-a41e-a70ae80de188',
      'Renamed admin laptop',
      { freshAuthGrantId: 'fresh-rename-grant' },
    );
    const deleted = await passkeysApi.deletePasskey(
      '7d705dcc-75f4-49b4-a41e-a70ae80de188',
      { freshAuthGrantId: 'fresh-delete-grant' },
    );
    const policy = await passkeysApi.updateSecurityPolicy({
      changeReason: 'rollout window',
      registrationEnabled: false,
    }, {
      freshAuthGrantId: 'fresh-policy-grant',
    });
    const compliance = await passkeysApi.getSecurityCompliance();

    expect(options.data.challengeId).toBe('challenge-admin-001');
    expect(verify.data.token_type).toBe('bearer');
    expect(list.data.credentials[0].label).toBe('Admin laptop');
    expect(rename.data.label).toBe('Renamed admin laptop');
    expect(deleted.data.status).toBe('revoked');
    expect(policy.data.registrationEnabled).toBe(false);
    expect(policy.data.policySource).toBe('system_config');
    expect(compliance.data.summary.principalsWithActivePasskeys).toBe(1);
    expect(capturedAuthenticationOptionsBody).toMatchObject({
      conditional: false,
      identifier: 'admin@cybervpn.example',
    });
    expect(capturedVerifyBody).toMatchObject({
      challengeId: 'challenge-admin-001',
      credential: { id: 'credential-response' },
    });
    expect(capturedRenameBody).toEqual({ label: 'Renamed admin laptop' });
    expect(capturedRenameFreshAuthGrantId).toBe('fresh-rename-grant');
    expect(capturedDeleteFreshAuthGrantId).toBe('fresh-delete-grant');
    expect(capturedPolicyBody).toEqual({
      changeReason: 'rollout window',
      registrationEnabled: false,
    });
    expect(capturedPolicyFreshAuthGrantId).toBe('fresh-policy-grant');
  });
});

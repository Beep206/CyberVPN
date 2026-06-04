import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import { passkeysApi } from '../passkeys';
import { FRESH_AUTH_GRANT_ID_HEADER } from '../fresh-auth';

const API_BASE = '*/api/v1';

describe('passkeysApi', () => {
  it('reads customer passkey policy from the backend contract', async () => {
    server.use(
      http.get(`${API_BASE}/auth/passkeys/policy`, () =>
        HttpResponse.json({
          enabled: true,
          surface: 'frontend',
          realm_key: 'customer',
          rp_id: 'localhost',
          rp_name: 'CyberVPN',
          allowedOrigins: ['http://localhost:3000'],
          userVerification: 'required',
          conditionalUiEnabled: true,
          registrationEnabled: true,
          authenticationEnabled: true,
          reauthenticationEnabled: true,
          securityDashboardEnabled: null,
          workspacePolicyEnabled: null,
          adminCountsAsMfa: false,
          challengeTtlSeconds: 120,
          browserTimeoutMs: 60000,
          freshAuthTtlSeconds: 300,
        }),
      ),
    );

    const response = await passkeysApi.getPolicy();

    expect(response.data.enabled).toBe(true);
    expect(response.data.conditionalUiEnabled).toBe(true);
    expect(response.data.rp_name).toBe('CyberVPN');
  });

  it('posts authentication options and verify payloads without local token storage', async () => {
    let optionsBody: Record<string, unknown> | null = null;
    let verifyBody: Record<string, unknown> | null = null;

    server.use(
      http.post(`${API_BASE}/auth/passkeys/authentication/options`, async ({ request }) => {
        optionsBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          challengeId: 'challenge-1',
          expiresAt: '2026-06-03T10:00:00Z',
          publicKey: {
            challenge: 'abc',
            rpId: 'localhost',
            userVerification: 'required',
          },
        });
      }),
      http.post(`${API_BASE}/auth/passkeys/authentication/verify`, async ({ request }) => {
        verifyBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json({
          access_token: 'cookie-managed',
          refresh_token: 'cookie-managed',
          token_type: 'bearer',
          expires_in: 3600,
          requires_2fa: false,
          tfa_token: null,
        });
      }),
    );

    const optionsResponse = await passkeysApi.createAuthenticationOptions({
      conditional: true,
      identifier: 'neo@example.com',
    });
    const verifyResponse = await passkeysApi.verifyAuthentication({
      challengeId: optionsResponse.data.challengeId,
      credential: {
        id: 'credential-id',
        rawId: 'credential-id',
        response: {
          authenticatorData: 'auth-data',
          clientDataJSON: 'client-data',
          signature: 'signature',
        },
        clientExtensionResults: {},
        type: 'public-key',
      },
    });

    expect(optionsBody).toEqual({ conditional: true, identifier: 'neo@example.com' });
    expect(verifyBody).toMatchObject({ challengeId: 'challenge-1' });
    expect(verifyResponse.data.requires_2fa).toBe(false);
  });

  it('lists, renames, and deletes sanitized passkey metadata', async () => {
    let deleteGrantHeader: string | null = null;
    let renameBody: Record<string, unknown> | null = null;
    let renameGrantHeader: string | null = null;

    server.use(
      http.get(`${API_BASE}/auth/passkeys`, () =>
        HttpResponse.json({
          credentials: [
            {
              id: 'b0f5fbd4-ec5b-46f3-b0cb-1354cfd2d5ab',
              label: 'Laptop',
              status: 'active',
              credentialType: 'public-key',
              deviceType: 'multiDevice',
              transports: ['internal'],
              backedUp: true,
              userVerified: true,
              createdAt: '2026-06-03T09:00:00Z',
              lastUsedAt: null,
              revokedAt: null,
            },
          ],
        }),
      ),
      http.patch(
        `${API_BASE}/auth/passkeys/b0f5fbd4-ec5b-46f3-b0cb-1354cfd2d5ab`,
        async ({ request }) => {
          renameBody = (await request.json()) as Record<string, unknown>;
          renameGrantHeader = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
          return HttpResponse.json({
            id: 'b0f5fbd4-ec5b-46f3-b0cb-1354cfd2d5ab',
            label: 'Work laptop',
            status: 'active',
            credentialType: 'public-key',
            deviceType: 'multiDevice',
            transports: ['internal'],
            backedUp: true,
            userVerified: true,
            createdAt: '2026-06-03T09:00:00Z',
            lastUsedAt: null,
            revokedAt: null,
          });
        },
      ),
      http.delete(
        `${API_BASE}/auth/passkeys/b0f5fbd4-ec5b-46f3-b0cb-1354cfd2d5ab`,
        ({ request }) => {
          deleteGrantHeader = request.headers.get(FRESH_AUTH_GRANT_ID_HEADER);
          return HttpResponse.json({
            id: 'b0f5fbd4-ec5b-46f3-b0cb-1354cfd2d5ab',
            status: 'revoked',
          });
        },
      ),
    );

    const listResponse = await passkeysApi.list();
    const renameResponse = await passkeysApi.rename(
      listResponse.data.credentials[0].id,
      'Work laptop',
      { freshAuthGrantId: 'fresh-rename-grant' },
    );
    const deleteResponse = await passkeysApi.delete(listResponse.data.credentials[0].id, {
      freshAuthGrantId: 'fresh-delete-grant',
    });

    expect(listResponse.data.credentials[0].label).toBe('Laptop');
    expect(renameBody).toEqual({ label: 'Work laptop' });
    expect(renameGrantHeader).toBe('fresh-rename-grant');
    expect(renameResponse.data.label).toBe('Work laptop');
    expect(deleteGrantHeader).toBe('fresh-delete-grant');
    expect(deleteResponse.data.status).toBe('revoked');
  });
});

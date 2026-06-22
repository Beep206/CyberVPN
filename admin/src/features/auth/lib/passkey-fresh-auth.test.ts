import { afterEach, describe, expect, it, vi } from 'vitest';
import { AxiosHeaders, type AxiosResponse } from 'axios';
import { passkeysApi } from '@/lib/api/passkeys';
import type {
  PasskeyOptionsResponse,
  PasskeyReauthenticationVerifyResponse,
} from '@/lib/api/passkeys';
import { startPasskeyAuthentication } from './passkey-webauthn';
import { requestPasskeyFreshAuthGrant } from './passkey-fresh-auth';

vi.mock('@/lib/api/passkeys', () => ({
  passkeysApi: {
    createReauthenticationOptions: vi.fn(),
    verifyReauthentication: vi.fn(),
  },
}));

vi.mock('./passkey-webauthn', () => ({
  startPasskeyAuthentication: vi.fn(),
}));

function axiosResponse<T>(data: T): AxiosResponse<T> {
  return {
    config: {
      headers: new AxiosHeaders(),
    },
    data,
    headers: {},
    status: 200,
    statusText: 'OK',
  };
}

describe('requestPasskeyFreshAuthGrant', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('requests reauthentication options, uses browser WebAuthn, and returns the verified grant', async () => {
    vi.mocked(passkeysApi.createReauthenticationOptions).mockResolvedValue(
      axiosResponse<PasskeyOptionsResponse>({
        challengeId: 'reauth-admin-001',
        expiresAt: '2026-06-03T12:05:00Z',
        publicKey: { challenge: 'YWRtaW4' },
      }),
    );
    vi.mocked(startPasskeyAuthentication).mockResolvedValue({
      id: 'admin-assertion',
    });
    vi.mocked(passkeysApi.verifyReauthentication).mockResolvedValue(
      axiosResponse<PasskeyReauthenticationVerifyResponse>({
        expiresAt: '2026-06-03T12:10:00Z',
        freshAuthGrantId: 'fresh-admin-grant',
      }),
    );

    const grantId = await requestPasskeyFreshAuthGrant('admin.passkeys.policy.update');

    expect(grantId).toBe('fresh-admin-grant');
    expect(passkeysApi.createReauthenticationOptions).toHaveBeenCalledWith(
      'admin.passkeys.policy.update',
    );
    expect(startPasskeyAuthentication).toHaveBeenCalledWith({ challenge: 'YWRtaW4' });
    expect(passkeysApi.verifyReauthentication).toHaveBeenCalledWith({
      action: 'admin.passkeys.policy.update',
      challengeId: 'reauth-admin-001',
      credential: { id: 'admin-assertion' },
    });
  });
});

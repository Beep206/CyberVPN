import { describe, expect, it, beforeEach, vi } from 'vitest';
import { requestPasskeyFreshAuthGrant } from './passkey-fresh-auth';

const passkeyMocks = vi.hoisted(() => ({
  createReauthenticationOptions: vi.fn(),
  startAuthentication: vi.fn(),
  verifyReauthentication: vi.fn(),
}));

vi.mock('@simplewebauthn/browser', () => ({
  startAuthentication: passkeyMocks.startAuthentication,
}));

vi.mock('@/lib/api/passkeys', () => ({
  passkeysApi: {
    createReauthenticationOptions: passkeyMocks.createReauthenticationOptions,
    verifyReauthentication: passkeyMocks.verifyReauthentication,
  },
}));

describe('requestPasskeyFreshAuthGrant', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('exchanges a reauthentication ceremony for a fresh-auth grant', async () => {
    const publicKey = {
      challenge: 'fresh-challenge',
      rpId: 'localhost',
      userVerification: 'required',
    };
    const credential = {
      clientExtensionResults: {},
      id: 'credential-id',
      rawId: 'credential-id',
      response: {
        authenticatorData: 'auth-data',
        clientDataJSON: 'client-data',
        signature: 'signature',
      },
      type: 'public-key',
    };

    passkeyMocks.createReauthenticationOptions.mockResolvedValueOnce({
      data: {
        challengeId: 'challenge-id',
        publicKey,
      },
    });
    passkeyMocks.startAuthentication.mockResolvedValueOnce(credential);
    passkeyMocks.verifyReauthentication.mockResolvedValueOnce({
      data: {
        expiresAt: '2026-06-04T06:00:00Z',
        freshAuthGrantId: 'fresh-auth-grant',
      },
    });

    const grantId = await requestPasskeyFreshAuthGrant(
      'passkey.credential.rename:credential-id',
    );

    expect(passkeyMocks.createReauthenticationOptions).toHaveBeenCalledWith(
      'passkey.credential.rename:credential-id',
    );
    expect(passkeyMocks.startAuthentication).toHaveBeenCalledWith({ optionsJSON: publicKey });
    expect(passkeyMocks.verifyReauthentication).toHaveBeenCalledWith({
      action: 'passkey.credential.rename:credential-id',
      challengeId: 'challenge-id',
      credential,
    });
    expect(grantId).toBe('fresh-auth-grant');
  });
});

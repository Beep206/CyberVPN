import { afterEach, describe, expect, it, vi } from 'vitest';
import { passkeysApi } from '@/lib/api/passkeys';
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

describe('requestPasskeyFreshAuthGrant', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('requests reauthentication options, uses browser WebAuthn, and returns the verified grant', async () => {
    vi.mocked(passkeysApi.createReauthenticationOptions).mockResolvedValue({
      data: {
        challengeId: 'reauth-partner-001',
        expiresAt: '2026-06-03T12:05:00Z',
        publicKey: { challenge: 'cGFydG5lcg' },
      },
    });
    vi.mocked(startPasskeyAuthentication).mockResolvedValue({
      id: 'partner-assertion',
    });
    vi.mocked(passkeysApi.verifyReauthentication).mockResolvedValue({
      data: {
        expiresAt: '2026-06-03T12:10:00Z',
        freshAuthGrantId: 'fresh-partner-grant',
      },
    });

    const grantId = await requestPasskeyFreshAuthGrant(
      'partner.passkeys.policy.update:workspace_001',
    );

    expect(grantId).toBe('fresh-partner-grant');
    expect(passkeysApi.createReauthenticationOptions).toHaveBeenCalledWith(
      'partner.passkeys.policy.update:workspace_001',
    );
    expect(startPasskeyAuthentication).toHaveBeenCalledWith({ challenge: 'cGFydG5lcg' });
    expect(passkeysApi.verifyReauthentication).toHaveBeenCalledWith({
      action: 'partner.passkeys.policy.update:workspace_001',
      challengeId: 'reauth-partner-001',
      credential: { id: 'partner-assertion' },
    });
  });
});

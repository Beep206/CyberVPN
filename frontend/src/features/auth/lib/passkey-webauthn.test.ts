import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  cancelPasskeyCeremony,
  completePasskeyAuthentication,
  completePasskeyRegistration,
  getPasskeyBrowserSupport,
  getPasskeyErrorMessageKey,
} from './passkey-webauthn';

const passkeyMocks = vi.hoisted(() => {
  class MockWebAuthnError extends Error {
    code: string;

    constructor(code: string) {
      super(code);
      this.name = 'WebAuthnError';
      this.code = code;
    }
  }

  return {
    browserSupportsWebAuthn: vi.fn(),
    browserSupportsWebAuthnAutofill: vi.fn(),
    cancelCeremony: vi.fn(),
    createAuthenticationOptions: vi.fn(),
    createRegistrationOptions: vi.fn(),
    startAuthentication: vi.fn(),
    startRegistration: vi.fn(),
    verifyAuthentication: vi.fn(),
    verifyRegistration: vi.fn(),
    WebAuthnError: MockWebAuthnError,
  };
});

vi.mock('@simplewebauthn/browser', () => ({
  browserSupportsWebAuthn: passkeyMocks.browserSupportsWebAuthn,
  browserSupportsWebAuthnAutofill: passkeyMocks.browserSupportsWebAuthnAutofill,
  startAuthentication: passkeyMocks.startAuthentication,
  startRegistration: passkeyMocks.startRegistration,
  WebAuthnAbortService: {
    cancelCeremony: passkeyMocks.cancelCeremony,
  },
  WebAuthnError: passkeyMocks.WebAuthnError,
}));

vi.mock('@/lib/api/passkeys', () => ({
  passkeysApi: {
    createAuthenticationOptions: passkeyMocks.createAuthenticationOptions,
    createRegistrationOptions: passkeyMocks.createRegistrationOptions,
    verifyAuthentication: passkeyMocks.verifyAuthentication,
    verifyRegistration: passkeyMocks.verifyRegistration,
  },
}));

describe('frontend passkey WebAuthn adapter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(window, 'isSecureContext', {
      configurable: true,
      value: true,
    });
    passkeyMocks.browserSupportsWebAuthn.mockReturnValue(true);
    passkeyMocks.browserSupportsWebAuthnAutofill.mockResolvedValue(true);
  });

  it('reports browser support including secure context and autofill availability', async () => {
    await expect(getPasskeyBrowserSupport()).resolves.toEqual({
      autofill: true,
      secureContext: true,
      webAuthn: true,
    });
    expect(passkeyMocks.browserSupportsWebAuthnAutofill).toHaveBeenCalledTimes(1);
  });

  it('completes registration through SimpleWebAuthn optionsJSON and verification API', async () => {
    const publicKey = {
      challenge: 'registration-challenge',
      rp: { id: 'cyber-vpn.net', name: 'CyberVPN' },
      user: {
        displayName: 'Customer',
        id: 'customer-user-id',
        name: 'customer@example.com',
      },
    };
    const credential = {
      id: 'credential-id',
      rawId: 'credential-id',
      response: {
        attestationObject: 'attestation',
        clientDataJSON: 'client-data',
      },
      type: 'public-key',
    };
    const registrationResponse = {
      data: {
        credentialId: 'credential-id',
      },
    };

    passkeyMocks.createRegistrationOptions.mockResolvedValueOnce({
      data: {
        challengeId: 'registration-challenge-id',
        publicKey,
      },
    });
    passkeyMocks.startRegistration.mockResolvedValueOnce(credential);
    passkeyMocks.verifyRegistration.mockResolvedValueOnce(registrationResponse);

    await expect(completePasskeyRegistration('  Laptop passkey  ')).resolves.toBe(
      registrationResponse,
    );

    expect(passkeyMocks.createRegistrationOptions).toHaveBeenCalledWith({
      label: 'Laptop passkey',
    });
    expect(passkeyMocks.startRegistration).toHaveBeenCalledWith({ optionsJSON: publicKey });
    expect(passkeyMocks.verifyRegistration).toHaveBeenCalledWith({
      challengeId: 'registration-challenge-id',
      credential,
      label: 'Laptop passkey',
    });
  });

  it('completes explicit or conditional authentication through SimpleWebAuthn v13 options', async () => {
    const publicKey = {
      challenge: 'authentication-challenge',
      rpId: 'cyber-vpn.net',
      userVerification: 'required',
    };
    const credential = {
      id: 'credential-id',
      rawId: 'credential-id',
      response: {
        authenticatorData: 'auth-data',
        clientDataJSON: 'client-data',
        signature: 'signature',
      },
      type: 'public-key',
    };
    const authenticationResponse = {
      data: {
        user: {
          id: 'customer-id',
        },
      },
    };

    passkeyMocks.createAuthenticationOptions.mockResolvedValueOnce({
      data: {
        challengeId: 'authentication-challenge-id',
        publicKey,
      },
    });
    passkeyMocks.startAuthentication.mockResolvedValueOnce(credential);
    passkeyMocks.verifyAuthentication.mockResolvedValueOnce(authenticationResponse);

    await expect(
      completePasskeyAuthentication({
        conditional: true,
        identifier: '  customer@example.com  ',
      }),
    ).resolves.toBe(authenticationResponse);

    expect(passkeyMocks.createAuthenticationOptions).toHaveBeenCalledWith({
      conditional: true,
      identifier: 'customer@example.com',
    });
    expect(passkeyMocks.startAuthentication).toHaveBeenCalledWith({
      optionsJSON: publicKey,
      useBrowserAutofill: true,
    });
    expect(passkeyMocks.verifyAuthentication).toHaveBeenCalledWith({
      challengeId: 'authentication-challenge-id',
      credential,
    });
  });

  it('maps browser WebAuthn failures and exposes ceremony cancellation', () => {
    expect(getPasskeyErrorMessageKey(new passkeyMocks.WebAuthnError('ERROR_CEREMONY_ABORTED'))).toBe(
      'passkeyCancelled',
    );
    expect(getPasskeyErrorMessageKey(new DOMException('Denied', 'NotAllowedError'))).toBe(
      'passkeyCancelled',
    );
    expect(getPasskeyErrorMessageKey(new DOMException('Unsupported', 'NotSupportedError'))).toBe(
      'passkeyUnsupported',
    );
    expect(getPasskeyErrorMessageKey(new passkeyMocks.WebAuthnError('ERROR_INVALID_DOMAIN'))).toBe(
      'passkeyGenericError',
    );

    cancelPasskeyCeremony();
    expect(passkeyMocks.cancelCeremony).toHaveBeenCalledTimes(1);
  });
});

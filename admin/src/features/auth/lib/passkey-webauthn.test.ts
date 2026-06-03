import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  PasskeyWebAuthnError,
  startPasskeyAuthentication,
} from './passkey-webauthn';

const originalPublicKeyCredential = window.PublicKeyCredential;
const originalCredentials = navigator.credentials;

function bufferFromAscii(value: string): ArrayBuffer {
  return Uint8Array.from(value, (character) => character.charCodeAt(0)).buffer;
}

function installWebAuthnMocks(input: {
  create?: (options?: CredentialCreationOptions) => Promise<Credential | null>;
  get?: (options?: CredentialRequestOptions) => Promise<Credential | null>;
}) {
  Object.defineProperty(window, 'PublicKeyCredential', {
    configurable: true,
    value: function PublicKeyCredentialMock() {},
  });
  Object.defineProperty(navigator, 'credentials', {
    configurable: true,
    value: {
      create: input.create ?? vi.fn(),
      get: input.get ?? vi.fn(),
    },
  });
}

function restoreWebAuthnMocks() {
  Object.defineProperty(window, 'PublicKeyCredential', {
    configurable: true,
    value: originalPublicKeyCredential,
  });
  Object.defineProperty(navigator, 'credentials', {
    configurable: true,
    value: originalCredentials,
  });
}

function buildAuthenticationCredential(): Credential {
  return {
    authenticatorAttachment: 'platform',
    getClientExtensionResults: () => ({}),
    id: 'credential-id',
    rawId: bufferFromAscii('raw-id'),
    response: {
      authenticatorData: bufferFromAscii('auth-data'),
      clientDataJSON: bufferFromAscii('client-data'),
      signature: bufferFromAscii('signature'),
      userHandle: null,
    },
    type: 'public-key',
  } as unknown as Credential;
}

describe('passkey WebAuthn helper', () => {
  afterEach(() => {
    restoreWebAuthnMocks();
  });

  it('normalizes request options and serializes authentication credentials', async () => {
    const getMock = vi.fn(async () => buildAuthenticationCredential());
    installWebAuthnMocks({ get: getMock });

    const payload = await startPasskeyAuthentication({
      allowCredentials: [
        {
          id: 'Y3JlZGVudGlhbC1pZA',
          type: 'public-key',
        },
      ],
      challenge: 'Y2hhbGxlbmdl',
      rpId: 'admin.cybervpn.example',
      userVerification: 'required',
    });

    const requestOptions = getMock.mock.calls[0][0] as CredentialRequestOptions;
    expect(requestOptions.publicKey?.challenge).toBeInstanceOf(ArrayBuffer);
    expect(requestOptions.publicKey?.allowCredentials?.[0].id).toBeInstanceOf(ArrayBuffer);
    expect(payload).toMatchObject({
      authenticatorAttachment: 'platform',
      id: 'credential-id',
      rawId: 'cmF3LWlk',
      type: 'public-key',
    });
    expect(payload.response).toMatchObject({
      authenticatorData: 'YXV0aC1kYXRh',
      clientDataJSON: 'Y2xpZW50LWRhdGE',
      signature: 'c2lnbmF0dXJl',
      userHandle: null,
    });
  });

  it('reports unsupported browsers before starting the ceremony', async () => {
    Object.defineProperty(window, 'PublicKeyCredential', {
      configurable: true,
      value: undefined,
    });
    Object.defineProperty(navigator, 'credentials', {
      configurable: true,
      value: {},
    });

    await expect(startPasskeyAuthentication({ challenge: 'YQ' })).rejects.toEqual(
      expect.objectContaining<Partial<PasskeyWebAuthnError>>({
        code: 'unsupported',
      }),
    );
  });
});

import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  isConditionalMediationAvailable,
  PasskeyWebAuthnError,
  startPasskeyRegistration,
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
  isConditionalMediationAvailable?: () => Promise<boolean>;
}) {
  Object.defineProperty(window, 'PublicKeyCredential', {
    configurable: true,
    value: Object.assign(function PublicKeyCredentialMock() {}, {
      isConditionalMediationAvailable: input.isConditionalMediationAvailable,
    }),
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

function buildRegistrationCredential(): Credential {
  return {
    authenticatorAttachment: 'platform',
    getClientExtensionResults: () => ({ appid: false }),
    id: 'registered-credential-id',
    rawId: bufferFromAscii('registered-raw-id'),
    response: {
      attestationObject: bufferFromAscii('attestation-object'),
      clientDataJSON: bufferFromAscii('registration-client-data'),
      getTransports: () => ['internal'],
    },
    type: 'public-key',
  } as unknown as Credential;
}

describe('passkey WebAuthn helper', () => {
  afterEach(() => {
    restoreWebAuthnMocks();
  });

  it('normalizes request options and serializes authentication credentials', async () => {
    const getMock = vi.fn<(
      options?: CredentialRequestOptions,
    ) => Promise<Credential | null>>(
      async () => buildAuthenticationCredential(),
    );
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
    });
    expect(payload.response).toHaveProperty('userHandle', undefined);
  });

  it('normalizes creation options and serializes registration credentials through SimpleWebAuthn', async () => {
    const createMock = vi.fn<(
      options?: CredentialCreationOptions,
    ) => Promise<Credential | null>>(
      async () => buildRegistrationCredential(),
    );
    installWebAuthnMocks({ create: createMock });

    const payload = await startPasskeyRegistration({
      challenge: 'cmVnaXN0cmF0aW9uLWNoYWxsZW5nZQ',
      excludeCredentials: [
        {
          id: 'ZXhjbHVkZS1jcmVkZW50aWFs',
          type: 'public-key',
        },
      ],
      pubKeyCredParams: [{ alg: -7, type: 'public-key' }],
      rp: { id: 'admin.cybervpn.example', name: 'CyberVPN Admin' },
      user: {
        displayName: 'Admin Operator',
        id: 'YWRtaW4tdXNlcg',
        name: 'admin@cybervpn.example',
      },
    });

    const creationOptions = createMock.mock.calls[0][0] as CredentialCreationOptions;
    expect(creationOptions.publicKey?.challenge).toBeInstanceOf(ArrayBuffer);
    expect(creationOptions.publicKey?.user.id).toBeInstanceOf(ArrayBuffer);
    expect(creationOptions.publicKey?.excludeCredentials?.[0].id).toBeInstanceOf(ArrayBuffer);
    expect(payload).toMatchObject({
      authenticatorAttachment: 'platform',
      clientExtensionResults: { appid: false },
      id: 'registered-credential-id',
      rawId: 'cmVnaXN0ZXJlZC1yYXctaWQ',
      type: 'public-key',
    });
    expect(payload.response).toMatchObject({
      attestationObject: 'YXR0ZXN0YXRpb24tb2JqZWN0',
      clientDataJSON: 'cmVnaXN0cmF0aW9uLWNsaWVudC1kYXRh',
      transports: ['internal'],
    });
  });

  it('reports conditional mediation support from the browser helper', async () => {
    installWebAuthnMocks({
      isConditionalMediationAvailable: async () => true,
    });

    await expect(isConditionalMediationAvailable()).resolves.toBe(true);
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

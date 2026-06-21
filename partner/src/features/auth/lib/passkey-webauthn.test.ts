import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  isConditionalMediationAvailable,
  PasskeyWebAuthnError,
  startPasskeyAuthentication,
  startPasskeyRegistration,
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

function expectCredentialRequestOptions(
  options: CredentialRequestOptions | undefined,
): asserts options is CredentialRequestOptions {
  expect(options).toBeDefined();
}

function expectCredentialCreationOptions(
  options: CredentialCreationOptions | undefined,
): asserts options is CredentialCreationOptions {
  expect(options).toBeDefined();
}

function buildAuthenticationCredential(): Credential {
  return {
    authenticatorAttachment: 'platform',
    getClientExtensionResults: () => ({}),
    id: 'partner-credential-id',
    rawId: bufferFromAscii('partner-raw-id'),
    response: {
      authenticatorData: bufferFromAscii('partner-auth-data'),
      clientDataJSON: bufferFromAscii('partner-client-data'),
      signature: bufferFromAscii('partner-signature'),
      userHandle: null,
    },
    type: 'public-key',
  } as unknown as Credential;
}

function buildRegistrationCredential(): Credential {
  return {
    authenticatorAttachment: 'platform',
    getClientExtensionResults: () => ({}),
    id: 'partner-registered-credential-id',
    rawId: bufferFromAscii('partner-registered-raw-id'),
    response: {
      attestationObject: bufferFromAscii('partner-attestation-object'),
      clientDataJSON: bufferFromAscii('partner-registration-client-data'),
      getTransports: () => ['internal'],
    },
    type: 'public-key',
  } as unknown as Credential;
}

describe('partner passkey WebAuthn helper', () => {
  afterEach(() => {
    restoreWebAuthnMocks();
  });

  it('normalizes request options and serializes authentication credentials through SimpleWebAuthn', async () => {
    const getMock = vi.fn(async (_options?: CredentialRequestOptions) => buildAuthenticationCredential());
    installWebAuthnMocks({ get: getMock });

    const payload = await startPasskeyAuthentication({
      allowCredentials: [
        {
          id: 'cGFydG5lci1jcmVkZW50aWFs',
          type: 'public-key',
        },
      ],
      challenge: 'cGFydG5lci1jaGFsbGVuZ2U',
      rpId: 'partner.cybervpn.example',
      userVerification: 'required',
    });

    const requestOptions = getMock.mock.calls[0]?.[0];
    expectCredentialRequestOptions(requestOptions);
    expect(requestOptions.publicKey?.challenge).toBeInstanceOf(ArrayBuffer);
    expect(requestOptions.publicKey?.allowCredentials?.[0].id).toBeInstanceOf(ArrayBuffer);
    expect(payload).toMatchObject({
      authenticatorAttachment: 'platform',
      id: 'partner-credential-id',
      rawId: ['cGFydG5lci1yYX', 'ctaWQ'].join(''),
      type: 'public-key',
    });
    expect(payload.response).toMatchObject({
      authenticatorData: ['cGFydG5lci1hdXRo', 'LWRhdGE'].join(''),
      clientDataJSON: ['cGFydG5lci1jbGllbnQt', 'ZGF0YQ'].join(''),
      signature: ['cGFydG5lci1zaWdu', 'YXR1cmU'].join(''),
    });
    expect(payload.response).toHaveProperty('userHandle', undefined);
  });

  it('normalizes creation options and serializes registration credentials through SimpleWebAuthn', async () => {
    const createMock = vi.fn(async (_options?: CredentialCreationOptions) => buildRegistrationCredential());
    installWebAuthnMocks({ create: createMock });

    const payload = await startPasskeyRegistration({
      challenge: 'cGFydG5lci1yZWdpc3RyYXRpb24tY2hhbGxlbmdl',
      excludeCredentials: [
        {
          id: 'cGFydG5lci1leGNsdWRlLWNyZWRlbnRpYWw',
          type: 'public-key',
        },
      ],
      pubKeyCredParams: [{ alg: -7, type: 'public-key' }],
      rp: { id: 'partner.cybervpn.example', name: 'CyberVPN Partner' },
      user: {
        displayName: 'Partner Operator',
        id: 'cGFydG5lci11c2Vy',
        name: 'operator@partner.example',
      },
    });

    const creationOptions = createMock.mock.calls[0]?.[0];
    expectCredentialCreationOptions(creationOptions);
    expect(creationOptions.publicKey?.challenge).toBeInstanceOf(ArrayBuffer);
    expect(creationOptions.publicKey?.user.id).toBeInstanceOf(ArrayBuffer);
    expect(creationOptions.publicKey?.excludeCredentials?.[0].id).toBeInstanceOf(ArrayBuffer);
    expect(payload).toMatchObject({
      authenticatorAttachment: 'platform',
      id: 'partner-registered-credential-id',
      rawId: 'cGFydG5lci1yZWdpc3RlcmVkLXJhdy1pZA',
      type: 'public-key',
    });
    expect(payload.response).toMatchObject({
      attestationObject: 'cGFydG5lci1hdHRlc3RhdGlvbi1vYmplY3Q',
      clientDataJSON: 'cGFydG5lci1yZWdpc3RyYXRpb24tY2xpZW50LWRhdGE',
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

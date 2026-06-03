'use client';

export type PasskeyWebAuthnErrorCode =
  | 'unsupported'
  | 'cancelled'
  | 'invalid_response';

export class PasskeyWebAuthnError extends Error {
  code: PasskeyWebAuthnErrorCode;

  constructor(code: PasskeyWebAuthnErrorCode, message: string) {
    super(message);
    this.name = 'PasskeyWebAuthnError';
    this.code = code;
  }
}

export function isPasskeyWebAuthnError(error: unknown): error is PasskeyWebAuthnError {
  return error instanceof PasskeyWebAuthnError;
}

export type WebAuthnCredentialPayload = Record<string, unknown>;

type WebAuthnOptionsJson = Record<string, unknown>;
type UnknownRecord = Record<string, unknown>;
type PublicKeyCredentialConstructorWithConditional = typeof PublicKeyCredential & {
  isConditionalMediationAvailable?: () => Promise<boolean>;
};

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isWebAuthnSupported(): boolean {
  return (
    typeof window !== 'undefined'
    && typeof navigator !== 'undefined'
    && typeof window.PublicKeyCredential !== 'undefined'
    && typeof navigator.credentials?.create === 'function'
    && typeof navigator.credentials?.get === 'function'
  );
}

export async function isConditionalMediationAvailable(): Promise<boolean> {
  if (!isWebAuthnSupported()) {
    return false;
  }

  const credentialConstructor =
    window.PublicKeyCredential as PublicKeyCredentialConstructorWithConditional;

  if (typeof credentialConstructor.isConditionalMediationAvailable !== 'function') {
    return false;
  }

  return credentialConstructor.isConditionalMediationAvailable();
}

function base64UrlToArrayBuffer(value: string): ArrayBuffer {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
  const paddingLength = (4 - (normalized.length % 4)) % 4;
  const padded = normalized.padEnd(normalized.length + paddingLength, '=');
  const binary = window.atob(padded);
  const bytes = new Uint8Array(binary.length);

  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  return bytes.buffer;
}

function arrayBufferToBase64Url(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';

  for (let index = 0; index < bytes.byteLength; index += 1) {
    binary += String.fromCharCode(bytes[index]);
  }

  return window.btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/u, '');
}

function readArrayBufferField(record: UnknownRecord, key: string): ArrayBuffer | null {
  const value = record[key];
  return value instanceof ArrayBuffer ? value : null;
}

function decodeCredentialDescriptors(value: unknown): PublicKeyCredentialDescriptor[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }

  return value
    .filter(isRecord)
    .map((descriptor) => {
      const nextDescriptor = { ...descriptor };
      if (typeof nextDescriptor.id === 'string') {
        nextDescriptor.id = base64UrlToArrayBuffer(nextDescriptor.id);
      }
      if (Array.isArray(nextDescriptor.transports)) {
        nextDescriptor.transports = nextDescriptor.transports.filter(
          (transport): transport is AuthenticatorTransport => typeof transport === 'string',
        );
      }
      return nextDescriptor as unknown as PublicKeyCredentialDescriptor;
    });
}

function normalizeRegistrationOptions(
  publicKeyJson: WebAuthnOptionsJson,
): PublicKeyCredentialCreationOptions {
  const publicKey: UnknownRecord = { ...publicKeyJson };

  if (typeof publicKey.challenge === 'string') {
    publicKey.challenge = base64UrlToArrayBuffer(publicKey.challenge);
  }

  if (isRecord(publicKey.user)) {
    const user = { ...publicKey.user };
    if (typeof user.id === 'string') {
      user.id = base64UrlToArrayBuffer(user.id);
    }
    publicKey.user = user;
  }

  const excludeCredentials = decodeCredentialDescriptors(publicKey.excludeCredentials);
  if (excludeCredentials) {
    publicKey.excludeCredentials = excludeCredentials;
  }

  return publicKey as unknown as PublicKeyCredentialCreationOptions;
}

function normalizeAuthenticationOptions(
  publicKeyJson: WebAuthnOptionsJson,
): PublicKeyCredentialRequestOptions {
  const publicKey: UnknownRecord = { ...publicKeyJson };

  if (typeof publicKey.challenge === 'string') {
    publicKey.challenge = base64UrlToArrayBuffer(publicKey.challenge);
  }

  const allowCredentials = decodeCredentialDescriptors(publicKey.allowCredentials);
  if (allowCredentials) {
    publicKey.allowCredentials = allowCredentials;
  }

  return publicKey as unknown as PublicKeyCredentialRequestOptions;
}

function assertCredential(
  credential: Credential | null,
): asserts credential is PublicKeyCredential {
  if (!credential || !('rawId' in credential) || !('response' in credential)) {
    throw new PasskeyWebAuthnError('invalid_response', 'Browser returned an invalid passkey response.');
  }
}

function serializeCredential(credential: Credential | null): WebAuthnCredentialPayload {
  assertCredential(credential);

  const response = credential.response as AuthenticatorResponse & UnknownRecord;
  const responsePayload: WebAuthnCredentialPayload = {
    clientDataJSON: arrayBufferToBase64Url(response.clientDataJSON),
  };

  const attestationObject = readArrayBufferField(response, 'attestationObject');
  if (attestationObject) {
    responsePayload.attestationObject = arrayBufferToBase64Url(attestationObject);
  }

  const authenticatorData = readArrayBufferField(response, 'authenticatorData');
  if (authenticatorData) {
    responsePayload.authenticatorData = arrayBufferToBase64Url(authenticatorData);
  }

  const signature = readArrayBufferField(response, 'signature');
  if (signature) {
    responsePayload.signature = arrayBufferToBase64Url(signature);
  }

  const userHandle = response.userHandle;
  if (userHandle instanceof ArrayBuffer) {
    responsePayload.userHandle = arrayBufferToBase64Url(userHandle);
  } else if (userHandle === null) {
    responsePayload.userHandle = null;
  }

  if (typeof response.getTransports === 'function') {
    responsePayload.transports = response.getTransports();
  }

  return {
    authenticatorAttachment: credential.authenticatorAttachment ?? null,
    clientExtensionResults: credential.getClientExtensionResults(),
    id: credential.id,
    rawId: arrayBufferToBase64Url(credential.rawId),
    response: responsePayload,
    type: credential.type,
  };
}

function normalizeBrowserError(error: unknown): PasskeyWebAuthnError {
  if (error instanceof PasskeyWebAuthnError) {
    return error;
  }

  if (error instanceof DOMException && (error.name === 'NotAllowedError' || error.name === 'AbortError')) {
    return new PasskeyWebAuthnError('cancelled', 'Passkey ceremony was cancelled.');
  }

  return new PasskeyWebAuthnError('invalid_response', 'Could not complete passkey ceremony.');
}

export async function startPasskeyRegistration(
  publicKeyJson: WebAuthnOptionsJson,
): Promise<WebAuthnCredentialPayload> {
  if (!isWebAuthnSupported()) {
    throw new PasskeyWebAuthnError('unsupported', 'This browser does not support passkeys.');
  }

  try {
    const credential = await navigator.credentials.create({
      publicKey: normalizeRegistrationOptions(publicKeyJson),
    });
    return serializeCredential(credential);
  } catch (error) {
    throw normalizeBrowserError(error);
  }
}

export async function startPasskeyAuthentication(
  publicKeyJson: WebAuthnOptionsJson,
  options: { conditional?: boolean; signal?: AbortSignal } = {},
): Promise<WebAuthnCredentialPayload> {
  if (!isWebAuthnSupported()) {
    throw new PasskeyWebAuthnError('unsupported', 'This browser does not support passkeys.');
  }

  try {
    const credentialRequestOptions: CredentialRequestOptions = {
      publicKey: normalizeAuthenticationOptions(publicKeyJson),
      signal: options.signal,
    };

    if (options.conditional) {
      credentialRequestOptions.mediation = 'conditional';
    }

    const credential = await navigator.credentials.get(credentialRequestOptions);
    return serializeCredential(credential);
  } catch (error) {
    throw normalizeBrowserError(error);
  }
}

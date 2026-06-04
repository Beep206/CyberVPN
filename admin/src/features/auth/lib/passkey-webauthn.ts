'use client';

import {
  browserSupportsWebAuthn,
  browserSupportsWebAuthnAutofill,
  startAuthentication as startSimpleWebAuthnAuthentication,
  startRegistration as startSimpleWebAuthnRegistration,
  WebAuthnAbortService,
  WebAuthnError,
  type AuthenticationResponseJSON,
  type PublicKeyCredentialCreationOptionsJSON,
  type PublicKeyCredentialRequestOptionsJSON,
  type RegistrationResponseJSON,
} from '@simplewebauthn/browser';

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

export function isWebAuthnSupported(): boolean {
  return (
    typeof window !== 'undefined'
    && typeof navigator !== 'undefined'
    && browserSupportsWebAuthn()
    && typeof navigator.credentials?.create === 'function'
    && typeof navigator.credentials?.get === 'function'
  );
}

export async function isConditionalMediationAvailable(): Promise<boolean> {
  if (!isWebAuthnSupported()) {
    return false;
  }

  return browserSupportsWebAuthnAutofill();
}

function normalizeBrowserError(error: unknown): PasskeyWebAuthnError {
  if (error instanceof PasskeyWebAuthnError) {
    return error;
  }

  if (
    error instanceof WebAuthnError
    && (error.code === 'ERROR_CEREMONY_ABORTED' || error.name === 'NotAllowedError')
  ) {
    return new PasskeyWebAuthnError('cancelled', 'Passkey ceremony was cancelled.');
  }

  if (error instanceof DOMException && (error.name === 'NotAllowedError' || error.name === 'AbortError')) {
    return new PasskeyWebAuthnError('cancelled', 'Passkey ceremony was cancelled.');
  }

  return new PasskeyWebAuthnError('invalid_response', 'Could not complete passkey ceremony.');
}

function toCredentialPayload(
  credential: AuthenticationResponseJSON | RegistrationResponseJSON,
): WebAuthnCredentialPayload {
  return { ...credential } as WebAuthnCredentialPayload;
}

async function runWithExternalAbort<T>(
  signal: AbortSignal | undefined,
  ceremony: () => Promise<T>,
): Promise<T> {
  if (!signal) {
    return ceremony();
  }

  if (signal.aborted) {
    throw new PasskeyWebAuthnError('cancelled', 'Passkey ceremony was cancelled.');
  }

  const abortCeremony = () => WebAuthnAbortService.cancelCeremony();
  signal.addEventListener('abort', abortCeremony, { once: true });

  try {
    return await ceremony();
  } finally {
    signal.removeEventListener('abort', abortCeremony);
  }
}

export async function startPasskeyRegistration(
  publicKeyJson: WebAuthnOptionsJson,
): Promise<WebAuthnCredentialPayload> {
  if (!isWebAuthnSupported()) {
    throw new PasskeyWebAuthnError('unsupported', 'This browser does not support passkeys.');
  }

  try {
    const credential = await startSimpleWebAuthnRegistration({
      optionsJSON: publicKeyJson as unknown as PublicKeyCredentialCreationOptionsJSON,
    });
    return toCredentialPayload(credential);
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
    const credential = await runWithExternalAbort(options.signal, () =>
      startSimpleWebAuthnAuthentication({
        optionsJSON: publicKeyJson as unknown as PublicKeyCredentialRequestOptionsJSON,
        useBrowserAutofill: options.conditional ?? false,
        verifyBrowserAutofillInput: false,
      }));
    return toCredentialPayload(credential);
  } catch (error) {
    throw normalizeBrowserError(error);
  }
}

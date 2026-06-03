'use client';

import {
  browserSupportsWebAuthn,
  browserSupportsWebAuthnAutofill,
  startAuthentication,
  startRegistration,
  WebAuthnAbortService,
  WebAuthnError,
} from '@simplewebauthn/browser';
import { passkeysApi } from '@/lib/api/passkeys';

export type PasskeyBrowserSupport = {
  autofill: boolean;
  secureContext: boolean;
  webAuthn: boolean;
};

export async function getPasskeyBrowserSupport(): Promise<PasskeyBrowserSupport> {
  if (typeof window === 'undefined') {
    return {
      autofill: false,
      secureContext: false,
      webAuthn: false,
    };
  }

  const webAuthn = browserSupportsWebAuthn();
  const autofill = webAuthn ? await browserSupportsWebAuthnAutofill() : false;

  return {
    autofill,
    secureContext: window.isSecureContext,
    webAuthn,
  };
}

export function cancelPasskeyCeremony(): void {
  WebAuthnAbortService.cancelCeremony();
}

export async function completePasskeyAuthentication({
  conditional = false,
  identifier,
}: {
  conditional?: boolean;
  identifier?: string | null;
}) {
  const { data: options } = await passkeysApi.createAuthenticationOptions({
    conditional,
    identifier: identifier?.trim() || null,
  });
  const credential = await startAuthentication({
    optionsJSON: options.publicKey,
    useBrowserAutofill: conditional,
  });

  return passkeysApi.verifyAuthentication({
    challengeId: options.challengeId,
    credential,
  });
}

export async function completePasskeyRegistration(label: string | null) {
  const normalizedLabel = label?.trim() || null;
  const { data: options } = await passkeysApi.createRegistrationOptions({
    label: normalizedLabel,
  });
  const credential = await startRegistration({
    optionsJSON: options.publicKey,
  });

  return passkeysApi.verifyRegistration({
    challengeId: options.challengeId,
    credential,
    label: normalizedLabel,
  });
}

function readErrorName(error: unknown): string | null {
  if (error instanceof WebAuthnError) {
    return error.code;
  }

  if (error instanceof DOMException) {
    return error.name;
  }

  if (typeof error === 'object' && error !== null && 'name' in error) {
    const name = (error as { name?: unknown }).name;
    return typeof name === 'string' ? name : null;
  }

  return null;
}

export function getPasskeyErrorMessageKey(error: unknown): string {
  const name = readErrorName(error);

  if (
    name === 'AbortError' ||
    name === 'NotAllowedError' ||
    name === 'ERROR_CEREMONY_ABORTED'
  ) {
    return 'passkeyCancelled';
  }

  if (name === 'SecurityError' || name === 'ERROR_INVALID_DOMAIN' || name === 'ERROR_INVALID_RP_ID') {
    return 'passkeyGenericError';
  }

  if (name === 'NotSupportedError') {
    return 'passkeyUnsupported';
  }

  return 'passkeyGenericError';
}

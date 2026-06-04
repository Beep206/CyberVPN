'use client';

import { startAuthentication } from '@simplewebauthn/browser';
import { passkeysApi } from '@/lib/api/passkeys';

export async function requestPasskeyFreshAuthGrant(action: string): Promise<string> {
  const optionsResponse = await passkeysApi.createReauthenticationOptions(action);
  const credential = await startAuthentication({
    optionsJSON: optionsResponse.data.publicKey,
  });
  const verifyResponse = await passkeysApi.verifyReauthentication({
    action,
    challengeId: optionsResponse.data.challengeId,
    credential,
  });

  return verifyResponse.data.freshAuthGrantId;
}

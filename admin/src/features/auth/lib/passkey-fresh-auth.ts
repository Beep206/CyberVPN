'use client';

import { passkeysApi } from '@/lib/api/passkeys';
import { startPasskeyAuthentication } from './passkey-webauthn';

export async function requestPasskeyFreshAuthGrant(action: string): Promise<string> {
  const optionsResponse = await passkeysApi.createReauthenticationOptions(action);
  const credential = await startPasskeyAuthentication(optionsResponse.data.publicKey);
  const verifyResponse = await passkeysApi.verifyReauthentication({
    action,
    challengeId: optionsResponse.data.challengeId,
    credential,
  });

  return verifyResponse.data.freshAuthGrantId;
}

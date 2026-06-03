import { apiClient } from './client';
import type { LoginResponse } from './auth';
import type {
  AuthenticationResponseJSON,
  PublicKeyCredentialCreationOptionsJSON,
  PublicKeyCredentialRequestOptionsJSON,
  RegistrationResponseJSON,
} from '@simplewebauthn/browser';

export type PasskeyPolicyResponse = {
  enabled: boolean;
  surface: string;
  realm_key: string;
  rp_id: string;
  rp_name: string;
  allowedOrigins: string[];
  userVerification?: string;
  conditionalUiEnabled: boolean;
  registrationEnabled: boolean;
  authenticationEnabled: boolean;
  reauthenticationEnabled: boolean;
  securityDashboardEnabled?: boolean | null;
  workspacePolicyEnabled?: boolean | null;
  adminCountsAsMfa: boolean;
  challengeTtlSeconds: number;
  browserTimeoutMs: number;
  freshAuthTtlSeconds?: number | null;
};

export type PasskeyOptionsResponse<TPublicKey> = {
  challengeId: string;
  publicKey: TPublicKey;
  expiresAt: string;
};

export type PasskeyCredential = {
  id: string;
  label: string;
  status: string;
  credentialType: string;
  deviceType: string | null;
  transports: string[];
  backedUp: boolean;
  userVerified: boolean;
  createdAt: string;
  lastUsedAt: string | null;
  revokedAt: string | null;
};

export type PasskeyCredentialListResponse = {
  credentials: PasskeyCredential[];
};

export type PasskeyDeleteResponse = {
  id: string;
  status: string;
};

export type PasskeyAuthenticationOptionsRequest = {
  identifier?: string | null;
  conditional?: boolean;
};

export type PasskeyRegistrationOptionsRequest = {
  label?: string | null;
};

export type PasskeyReauthenticationVerifyResponse = {
  freshAuthGrantId: string;
  expiresAt: string;
};

export const passkeysApi = {
  /**
   * GET /api/v1/auth/passkeys/policy
   */
  getPolicy: () => apiClient.get<PasskeyPolicyResponse>('/auth/passkeys/policy'),

  /**
   * POST /api/v1/auth/passkeys/authentication/options
   */
  createAuthenticationOptions: (data: PasskeyAuthenticationOptionsRequest = {}) =>
    apiClient.post<PasskeyOptionsResponse<PublicKeyCredentialRequestOptionsJSON>>(
      '/auth/passkeys/authentication/options',
      data,
    ),

  /**
   * POST /api/v1/auth/passkeys/authentication/verify
   */
  verifyAuthentication: (data: {
    challengeId: string;
    credential: AuthenticationResponseJSON;
  }) => apiClient.post<LoginResponse>('/auth/passkeys/authentication/verify', data),

  /**
   * POST /api/v1/auth/passkeys/registration/options
   */
  createRegistrationOptions: (data: PasskeyRegistrationOptionsRequest = {}) =>
    apiClient.post<PasskeyOptionsResponse<PublicKeyCredentialCreationOptionsJSON>>(
      '/auth/passkeys/registration/options',
      data,
    ),

  /**
   * POST /api/v1/auth/passkeys/registration/verify
   */
  verifyRegistration: (data: {
    challengeId: string;
    credential: RegistrationResponseJSON;
    label?: string | null;
  }) => apiClient.post<PasskeyCredential>('/auth/passkeys/registration/verify', data),

  /**
   * GET /api/v1/auth/passkeys
   */
  list: () => apiClient.get<PasskeyCredentialListResponse>('/auth/passkeys'),

  /**
   * PATCH /api/v1/auth/passkeys/{credential_id}
   */
  rename: (credentialId: string, label: string) =>
    apiClient.patch<PasskeyCredential>(`/auth/passkeys/${credentialId}`, { label }),

  /**
   * DELETE /api/v1/auth/passkeys/{credential_id}
   */
  delete: (credentialId: string) =>
    apiClient.delete<PasskeyDeleteResponse>(`/auth/passkeys/${credentialId}`),

  /**
   * POST /api/v1/auth/passkeys/reauthentication/options
   */
  createReauthenticationOptions: (action: string) =>
    apiClient.post<PasskeyOptionsResponse<PublicKeyCredentialRequestOptionsJSON>>(
      '/auth/passkeys/reauthentication/options',
      { action },
    ),

  /**
   * POST /api/v1/auth/passkeys/reauthentication/verify
   */
  verifyReauthentication: (data: {
    action: string;
    challengeId: string;
    credential: AuthenticationResponseJSON;
  }) =>
    apiClient.post<PasskeyReauthenticationVerifyResponse>(
      '/auth/passkeys/reauthentication/verify',
      data,
    ),
};

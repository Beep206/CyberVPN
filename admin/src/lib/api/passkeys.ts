import { apiClient } from './client';
import type { LoginResponse } from './auth';
import {
  buildFreshAuthRequestConfig,
  type FreshAuthRequestOptions,
} from './fresh-auth';

export type PasskeyCredentialPayload = Record<string, unknown>;

export interface PasskeyPolicyResponse {
  enabled: boolean;
  configuredEnabled?: boolean;
  globalEnabled?: boolean;
  surfaceEnabled?: boolean;
  surface: string;
  realm_key: string;
  rp_id: string;
  rp_name: string;
  allowedOrigins: string[];
  userVerification: string;
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
  policySource?: string;
  updatedAt?: string | null;
  updatedBy?: string | null;
}

export interface UpdateAdminPasskeyPolicyRequest {
  enabled?: boolean;
  registrationEnabled?: boolean;
  authenticationEnabled?: boolean;
  reauthenticationEnabled?: boolean;
  conditionalUiEnabled?: boolean;
  securityDashboardEnabled?: boolean;
  adminCountsAsMfa?: boolean;
  challengeTtlSeconds?: number;
  browserTimeoutMs?: number;
  freshAuthTtlSeconds?: number;
  changeReason?: string | null;
}

export interface PasskeyOptionsResponse {
  challengeId: string;
  publicKey: Record<string, unknown>;
  expiresAt: string;
}

export interface PasskeyCredentialResponse {
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
}

export interface PasskeyCredentialListResponse {
  credentials: PasskeyCredentialResponse[];
}

export interface PasskeyDeleteResponse {
  id: string;
  status: string;
}

export interface PasskeyComplianceSummaryResponse {
  activeCredentials: number;
  revokedCredentials: number;
  cloneSuspectedCredentials: number;
  principalsWithActivePasskeys: number;
  staleCredentials: number;
  generatedAt: string;
}

export interface PasskeyComplianceCredentialResponse {
  id: string;
  label: string;
  status: string;
  realmKey: string;
  principalClass: string;
  principalSubject: string;
  surface: string;
  rpId: string;
  credentialIdHashPrefix: string;
  credentialType: string;
  deviceType: string | null;
  transports: string[];
  backedUp: boolean;
  userVerified: boolean;
  cloneSuspectedAt: string | null;
  createdAt: string;
  lastUsedAt: string | null;
  revokedAt: string | null;
}

export interface PasskeyComplianceResponse {
  policy: PasskeyPolicyResponse;
  summary: PasskeyComplianceSummaryResponse;
  credentials: PasskeyComplianceCredentialResponse[];
}

export interface PasskeyReauthenticationVerifyResponse {
  freshAuthGrantId: string;
  expiresAt: string;
}

export const passkeysApi = {
  getAuthPolicy: () =>
    apiClient.get<PasskeyPolicyResponse>('/auth/passkeys/policy'),

  createRegistrationOptions: (label?: string | null) =>
    apiClient.post<PasskeyOptionsResponse>('/auth/passkeys/registration/options', {
      label: label?.trim() || null,
    }),

  verifyRegistration: (data: {
    challengeId: string;
    credential: PasskeyCredentialPayload;
    label?: string | null;
  }) =>
    apiClient.post<PasskeyCredentialResponse>('/auth/passkeys/registration/verify', {
      challengeId: data.challengeId,
      credential: data.credential,
      label: data.label?.trim() || null,
    }),

  createAuthenticationOptions: (data?: {
    identifier?: string | null;
    conditional?: boolean;
  }) =>
    apiClient.post<PasskeyOptionsResponse>('/auth/passkeys/authentication/options', {
      conditional: data?.conditional ?? false,
      identifier: data?.identifier?.trim() || null,
    }),

  verifyAuthentication: (data: {
    challengeId: string;
    credential: PasskeyCredentialPayload;
  }) =>
    apiClient.post<LoginResponse>('/auth/passkeys/authentication/verify', data),

  listPasskeys: () =>
    apiClient.get<PasskeyCredentialListResponse>('/auth/passkeys'),

  renamePasskey: (
    credentialId: string,
    label: string,
    options?: FreshAuthRequestOptions,
  ) =>
    apiClient.patch<PasskeyCredentialResponse>(
      `/auth/passkeys/${encodeURIComponent(credentialId)}`,
      { label },
      buildFreshAuthRequestConfig(options),
    ),

  deletePasskey: (credentialId: string, options?: FreshAuthRequestOptions) =>
    apiClient.delete<PasskeyDeleteResponse>(
      `/auth/passkeys/${encodeURIComponent(credentialId)}`,
      buildFreshAuthRequestConfig(options),
    ),

  createReauthenticationOptions: (action: string) =>
    apiClient.post<PasskeyOptionsResponse>('/auth/passkeys/reauthentication/options', {
      action,
    }),

  verifyReauthentication: (data: {
    action: string;
    challengeId: string;
    credential: PasskeyCredentialPayload;
  }) =>
    apiClient.post<PasskeyReauthenticationVerifyResponse>(
      '/auth/passkeys/reauthentication/verify',
      data,
    ),

  getSecurityPolicy: () =>
    apiClient.get<PasskeyPolicyResponse>('/security/passkeys/policy'),

  updateSecurityPolicy: (
    data: UpdateAdminPasskeyPolicyRequest,
    options?: FreshAuthRequestOptions,
  ) =>
    apiClient.patch<PasskeyPolicyResponse>(
      '/security/passkeys/policy',
      data,
      buildFreshAuthRequestConfig(options),
    ),

  getSecurityCompliance: () =>
    apiClient.get<PasskeyComplianceResponse>('/security/passkeys/compliance'),
};

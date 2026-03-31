import type { OAuthProvider } from '@/lib/api/auth';

export const OAUTH_PROVIDER_QUERY_PARAM = 'oauth_provider';

export const OAUTH_ERROR_CODES = {
  invalidProvider: 'invalid_provider',
  oauthNotConfigured: 'oauth_not_configured',
  oauthUpstreamUnavailable: 'oauth_upstream_unavailable',
  oauthStartFailed: 'oauth_start_failed',
  oauthStartInvalidResponse: 'oauth_start_invalid_response',
  oauthInvalidTransaction: 'oauth_invalid_transaction',
  oauthMissingParams: 'oauth_missing_params',
  providerDenied: 'provider_denied',
  oauthStateInvalid: 'oauth_state_invalid',
  oauthCollision: 'oauth_collision',
  oauthLinkingRequired: 'oauth_linking_required',
  oauthAuthFailed: 'oauth_auth_failed',
  oauthCallbackFailed: 'oauth_callback_failed',
  deprecatedCallback: 'deprecated_callback',
} as const;

export type OAuthUiErrorCode = typeof OAUTH_ERROR_CODES[keyof typeof OAUTH_ERROR_CODES];

export type OAuthFailureKind =
  | 'provider_denied'
  | 'collision'
  | 'state_invalid'
  | 'callback_failed';

const OAUTH_UI_ERROR_CODES = new Set<OAuthUiErrorCode>(Object.values(OAUTH_ERROR_CODES));
const OAUTH_PROVIDER_IDS = new Set<OAuthProvider>([
  'google',
  'github',
  'discord',
  'facebook',
  'apple',
  'microsoft',
  'twitter',
  'telegram',
]);

export function isOAuthProvider(value: string | null | undefined): value is OAuthProvider {
  return Boolean(value && OAUTH_PROVIDER_IDS.has(value as OAuthProvider));
}

export function normalizeOAuthProviderErrorCode(rawError: string | null): OAuthUiErrorCode {
  const normalized = rawError
    ?.trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');

  if (!normalized) {
    return OAUTH_ERROR_CODES.oauthCallbackFailed;
  }

  if (
    normalized === 'access_denied'
    || normalized === 'authorization_denied'
    || normalized === 'user_denied'
    || normalized === 'user_cancelled_login'
  ) {
    return OAUTH_ERROR_CODES.providerDenied;
  }

  return OAUTH_ERROR_CODES.oauthCallbackFailed;
}

export function normalizeOAuthUiErrorCode(rawError: string | null | undefined): OAuthUiErrorCode {
  if (!rawError) {
    return OAUTH_ERROR_CODES.oauthCallbackFailed;
  }

  const normalized = rawError.trim().toLowerCase() as OAuthUiErrorCode;
  return OAUTH_UI_ERROR_CODES.has(normalized) ? normalized : OAUTH_ERROR_CODES.oauthCallbackFailed;
}

export function inferOAuthUpstreamErrorCode(status: number, detail: string | null | undefined): OAuthUiErrorCode {
  const normalizedDetail = detail?.trim().toLowerCase() ?? '';

  if (status === 409) {
    if (normalizedDetail.includes('linking') || normalizedDetail.includes('link')) {
      return OAUTH_ERROR_CODES.oauthLinkingRequired;
    }
    return OAUTH_ERROR_CODES.oauthCollision;
  }

  if (status === 401 && normalizedDetail.includes('state')) {
    return OAUTH_ERROR_CODES.oauthStateInvalid;
  }

  if (status === 401) {
    return OAUTH_ERROR_CODES.oauthAuthFailed;
  }

  return OAUTH_ERROR_CODES.oauthCallbackFailed;
}

export function getOAuthErrorMessageKey(errorCode: string): string {
  switch (normalizeOAuthUiErrorCode(errorCode)) {
    case OAUTH_ERROR_CODES.invalidProvider:
      return 'oauthErrors.invalidProvider';
    case OAUTH_ERROR_CODES.oauthNotConfigured:
      return 'oauthErrors.notConfigured';
    case OAUTH_ERROR_CODES.oauthUpstreamUnavailable:
      return 'oauthErrors.upstreamUnavailable';
    case OAUTH_ERROR_CODES.oauthStartFailed:
    case OAUTH_ERROR_CODES.oauthStartInvalidResponse:
      return 'oauthErrors.startFailed';
    case OAUTH_ERROR_CODES.oauthInvalidTransaction:
      return 'oauthErrors.invalidTransaction';
    case OAUTH_ERROR_CODES.oauthMissingParams:
      return 'oauthErrors.missingParams';
    case OAUTH_ERROR_CODES.providerDenied:
      return 'oauthErrors.providerDenied';
    case OAUTH_ERROR_CODES.oauthStateInvalid:
      return 'oauthErrors.stateInvalid';
    case OAUTH_ERROR_CODES.oauthCollision:
      return 'oauthErrors.collision';
    case OAUTH_ERROR_CODES.oauthLinkingRequired:
      return 'oauthErrors.linkingRequired';
    case OAUTH_ERROR_CODES.oauthAuthFailed:
      return 'oauthErrors.authFailed';
    case OAUTH_ERROR_CODES.deprecatedCallback:
      return 'oauthErrors.deprecatedCallback';
    default:
      return 'oauthErrors.callbackFailed';
  }
}

export function getOAuthFailureKind(errorCode: string): OAuthFailureKind {
  switch (normalizeOAuthUiErrorCode(errorCode)) {
    case OAUTH_ERROR_CODES.providerDenied:
      return 'provider_denied';
    case OAUTH_ERROR_CODES.oauthCollision:
    case OAUTH_ERROR_CODES.oauthLinkingRequired:
      return 'collision';
    case OAUTH_ERROR_CODES.oauthStateInvalid:
      return 'state_invalid';
    default:
      return 'callback_failed';
  }
}

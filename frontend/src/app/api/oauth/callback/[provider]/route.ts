import { NextRequest, NextResponse } from 'next/server';

import type { OAuthLoginResponse } from '@/lib/api/auth';
import {
  inferOAuthUpstreamErrorCode,
  normalizeOAuthProviderErrorCode,
  OAUTH_ERROR_CODES,
  OAUTH_PROVIDER_QUERY_PARAM,
} from '@/features/auth/lib/oauth-error-codes';
import {
  isSupportedWebOAuthProvider,
  OAUTH_TRANSACTION_COOKIE,
  parseOAuthTransactionCookieValue,
} from '@/features/auth/lib/oauth-transaction';
import {
  createPendingTwoFactorCookieValue,
  pendingTwoFactorCookieOptions,
  PENDING_2FA_COOKIE,
} from '@/features/auth/lib/pending-twofa';
import { getDefaultPostLoginPath, normalizeAuthLocale } from '@/features/auth/lib/redirect-path';
import {
  oauthResultCookieOptions,
  OAUTH_RESULT_COOKIE,
} from '@/features/auth/lib/session';

function getBackendBaseUrl(): string {
  const baseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new Error('API_URL or NEXT_PUBLIC_API_URL must be configured.');
  }

  return baseUrl.replace(/\/$/, '');
}

function buildForwardHeaders(request: NextRequest): Headers {
  const headers = new Headers({
    accept: 'application/json',
    'content-type': 'application/json',
  });

  const forwardedFor = request.headers.get('x-forwarded-for');
  const userAgent = request.headers.get('user-agent');
  const acceptLanguage = request.headers.get('accept-language');

  if (forwardedFor) {
    headers.set('x-forwarded-for', forwardedFor);
  }
  if (userAgent) {
    headers.set('user-agent', userAgent);
  }
  if (acceptLanguage) {
    headers.set('accept-language', acceptLanguage);
  }

  return headers;
}

function buildLoginErrorUrl(
  request: NextRequest,
  locale: string,
  errorCode: string,
  provider: string | null = null,
): URL {
  const loginUrl = new URL(`/${locale}/login`, request.url);
  loginUrl.searchParams.set('oauth_error', errorCode);
  if (provider) {
    loginUrl.searchParams.set(OAUTH_PROVIDER_QUERY_PARAM, provider);
  }
  return loginUrl;
}

function getSetCookieHeaders(response: Response): string[] {
  const headers = response.headers as Headers & {
    getSetCookie?: () => string[];
  };

  if (typeof headers.getSetCookie === 'function') {
    return headers.getSetCookie();
  }

  const setCookie = response.headers.get('set-cookie');
  return setCookie ? [setCookie] : [];
}

function appendSetCookieHeaders(source: Response, target: NextResponse): void {
  for (const headerValue of getSetCookieHeaders(source)) {
    target.headers.append('set-cookie', headerValue);
  }
}

async function readOAuthPayload(response: Response): Promise<OAuthLoginResponse | null> {
  try {
    return await response.json() as OAuthLoginResponse;
  } catch {
    return null;
  }
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const payload = await response.json() as { detail?: unknown };
    return typeof payload.detail === 'string' ? payload.detail : null;
  } catch {
    return null;
  }
}

function finalizeRedirectResponse(targetUrl: URL): NextResponse {
  const response = NextResponse.redirect(targetUrl);
  response.cookies.delete(OAUTH_TRANSACTION_COOKIE);
  return response;
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ provider: string }> },
): Promise<NextResponse> {
  const { provider } = await context.params;
  const fallbackLocale = normalizeAuthLocale(request.nextUrl.searchParams.get('locale'));

  if (!isSupportedWebOAuthProvider(provider)) {
    return finalizeRedirectResponse(
      buildLoginErrorUrl(request, fallbackLocale, OAUTH_ERROR_CODES.invalidProvider),
    );
  }

  const transaction = parseOAuthTransactionCookieValue(
    request.cookies.get(OAUTH_TRANSACTION_COOKIE)?.value,
  );
  const locale = transaction?.locale ?? fallbackLocale;

  const providerError = request.nextUrl.searchParams.get('error');
  if (providerError) {
    return finalizeRedirectResponse(
      buildLoginErrorUrl(request, locale, normalizeOAuthProviderErrorCode(providerError), provider),
    );
  }

  if (!transaction || transaction.provider !== provider) {
    return finalizeRedirectResponse(
      buildLoginErrorUrl(request, locale, OAUTH_ERROR_CODES.oauthInvalidTransaction, provider),
    );
  }

  const code = request.nextUrl.searchParams.get('code');
  const state = request.nextUrl.searchParams.get('state');
  if (!code || !state) {
    return finalizeRedirectResponse(
      buildLoginErrorUrl(request, locale, OAUTH_ERROR_CODES.oauthMissingParams, provider),
    );
  }

  let backendResponse: Response;
  try {
    backendResponse = await fetch(
      `${getBackendBaseUrl()}/api/v1/oauth/${provider}/login/callback`,
      {
        body: JSON.stringify({ code, state }),
        cache: 'no-store',
        headers: buildForwardHeaders(request),
        method: 'POST',
      },
    );
  } catch {
    return finalizeRedirectResponse(
      buildLoginErrorUrl(request, locale, OAUTH_ERROR_CODES.oauthUpstreamUnavailable, provider),
    );
  }

  if (!backendResponse.ok) {
    const detail = await readErrorDetail(backendResponse);
    return finalizeRedirectResponse(
      buildLoginErrorUrl(
        request,
        locale,
        inferOAuthUpstreamErrorCode(backendResponse.status, detail),
        provider,
      ),
    );
  }

  const payload = await readOAuthPayload(backendResponse);
  if (!payload) {
    return finalizeRedirectResponse(
      buildLoginErrorUrl(request, locale, OAUTH_ERROR_CODES.oauthCallbackFailed, provider),
    );
  }

  const defaultReturnTo = getDefaultPostLoginPath(locale);
  const targetUrl = new URL(transaction.returnTo, request.url);

  if (payload.requires_2fa && payload.tfa_token) {
    const loginUrl = new URL(`/${locale}/login`, request.url);
    loginUrl.searchParams.set('2fa', 'true');
    loginUrl.searchParams.set(OAUTH_PROVIDER_QUERY_PARAM, provider);
    const response = finalizeRedirectResponse(loginUrl);
    const pendingTwoFactor = createPendingTwoFactorCookieValue(
      payload.tfa_token,
      locale,
      transaction.returnTo,
      payload.is_new_user,
    );
    response.cookies.set(PENDING_2FA_COOKIE, pendingTwoFactor.cookieValue, pendingTwoFactorCookieOptions);
    return response;
  }

  if (payload.is_new_user && transaction.returnTo === defaultReturnTo) {
    targetUrl.searchParams.set('welcome', 'true');
  }

  const response = finalizeRedirectResponse(targetUrl);
  response.cookies.set(OAUTH_RESULT_COOKIE, provider, oauthResultCookieOptions);
  appendSetCookieHeaders(backendResponse, response);
  return response;
}

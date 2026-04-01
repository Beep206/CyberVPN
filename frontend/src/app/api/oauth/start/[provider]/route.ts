import { NextRequest, NextResponse } from 'next/server';

import {
  OAUTH_PROVIDER_QUERY_PARAM,
  OAUTH_ERROR_CODES,
} from '@/features/auth/lib/oauth-error-codes';
import {
  createOAuthTransactionCookieValue,
  isSupportedWebOAuthProvider,
  OAUTH_TRANSACTION_COOKIE,
  oauthTransactionCookieOptions,
} from '@/features/auth/lib/oauth-transaction';
import { buildAppUrl } from '@/features/auth/lib/request-origin';
import { normalizeAuthLocale } from '@/features/auth/lib/redirect-path';

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
  const loginUrl = buildAppUrl(request, `/${locale}/login`);
  loginUrl.searchParams.set('oauth_error', errorCode);
  if (provider) {
    loginUrl.searchParams.set(OAUTH_PROVIDER_QUERY_PARAM, provider);
  }
  return loginUrl;
}

async function readAuthorizeUrl(response: Response): Promise<string | null> {
  try {
    const payload = await response.json() as { authorize_url?: unknown };
    return typeof payload.authorize_url === 'string' ? payload.authorize_url : null;
  } catch {
    return null;
  }
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ provider: string }> },
): Promise<NextResponse> {
  const { provider } = await context.params;
  const locale = normalizeAuthLocale(request.nextUrl.searchParams.get('locale'));

  if (!isSupportedWebOAuthProvider(provider)) {
    return NextResponse.redirect(buildLoginErrorUrl(request, locale, OAUTH_ERROR_CODES.invalidProvider));
  }

  let transaction;
  try {
    transaction = createOAuthTransactionCookieValue(
      provider,
      locale,
      request.nextUrl.searchParams.get('return_to'),
    );
  } catch {
    return NextResponse.redirect(
      buildLoginErrorUrl(request, locale, OAUTH_ERROR_CODES.oauthNotConfigured, provider),
    );
  }

  let backendResponse: Response;
  try {
    backendResponse = await fetch(
      `${getBackendBaseUrl()}/api/v1/oauth/${provider}/login`,
      {
        cache: 'no-store',
        headers: buildForwardHeaders(request),
        method: 'GET',
      },
    );
  } catch {
    return NextResponse.redirect(
      buildLoginErrorUrl(
        request,
        transaction.locale,
        OAUTH_ERROR_CODES.oauthUpstreamUnavailable,
        provider,
      ),
    );
  }

  if (!backendResponse.ok) {
    return NextResponse.redirect(
      buildLoginErrorUrl(request, transaction.locale, OAUTH_ERROR_CODES.oauthStartFailed, provider),
    );
  }

  const authorizeUrl = await readAuthorizeUrl(backendResponse);
  if (!authorizeUrl) {
    return NextResponse.redirect(
      buildLoginErrorUrl(
        request,
        transaction.locale,
        OAUTH_ERROR_CODES.oauthStartInvalidResponse,
        provider,
      ),
    );
  }

  const response = NextResponse.redirect(authorizeUrl);
  response.cookies.set(
    OAUTH_TRANSACTION_COOKIE,
    transaction.cookieValue,
    oauthTransactionCookieOptions,
  );

  return response;
}

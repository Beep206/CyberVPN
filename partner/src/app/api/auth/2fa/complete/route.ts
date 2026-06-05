import { NextRequest, NextResponse } from 'next/server';

import {
  parsePendingTwoFactorCookieValue,
  PENDING_2FA_COOKIE,
} from '@/features/auth/lib/pending-twofa';
import { PARTNER_PORTAL_REALM_KEY } from '@/features/auth/lib/partner-access';
import { getDefaultPostLoginPath } from '@/features/auth/lib/redirect-path';
import { resolvePartnerSurfaceContext } from '@/features/storefront-shell/lib/runtime';

function getBackendBaseUrl(): string {
  const baseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new Error('API_URL or NEXT_PUBLIC_API_URL must be configured.');
  }

  return baseUrl.replace(/\/$/, '');
}

const PARTNER_PORTAL_BACKEND_HOST =
  process.env.NEXT_PUBLIC_PARTNER_PORTAL_HOST?.trim() || 'partner.cyber-vpn.net';
const PARTNER_CANONICAL_FORWARDED_PROTO = 'https';
const APPROVED_LOCAL_STAGE_PARTNER_HOSTS = new Set([
  'portal.localhost:3004',
  'storefront.localhost:3004',
  '127.0.0.1:3004',
  'localhost:3004',
  'portal.localhost:3002',
  'storefront.localhost:3002',
  '127.0.0.1:3002',
  'localhost:3002',
]);

interface ForwardedAuthContext {
  authRealmKey: string;
  forwardedHost: string;
}

function getRequestHost(request: NextRequest): string {
  return request.headers.get('x-forwarded-host') ?? request.headers.get('host') ?? request.nextUrl.host;
}

function getForwardedAuthContext(request: NextRequest): ForwardedAuthContext {
  const surfaceContext = resolvePartnerSurfaceContext(getRequestHost(request));

  if (surfaceContext.family === 'portal') {
    return {
      authRealmKey: PARTNER_PORTAL_REALM_KEY,
      forwardedHost: PARTNER_PORTAL_BACKEND_HOST,
    };
  }

  return {
    authRealmKey: surfaceContext.authRealmKey,
    forwardedHost: surfaceContext.canonicalHost,
  };
}

function buildForwardHeaders(request: NextRequest, token: string): Headers {
  const { authRealmKey, forwardedHost } = getForwardedAuthContext(request);
  const headers = new Headers({
    accept: 'application/json',
    authorization: `Bearer ${token}`,
    'content-type': 'application/json',
    'x-auth-realm': authRealmKey,
    'x-forwarded-host': forwardedHost,
    'x-forwarded-proto': PARTNER_CANONICAL_FORWARDED_PROTO,
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

function getSetCookieHeaders(response: Response): string[] {
  const headers = response.headers as Headers & {
    getSetCookie?: () => string[];
  };

  if (typeof headers.getSetCookie === 'function') {
    const setCookieHeaders = headers.getSetCookie();
    if (setCookieHeaders.length > 0) {
      return setCookieHeaders.flatMap(splitCombinedSetCookieHeader);
    }
  }

  const setCookie = response.headers.get('set-cookie');
  return setCookie ? splitCombinedSetCookieHeader(setCookie) : [];
}

function isCookieHeaderBoundary(headerValue: string, commaIndex: number): boolean {
  const remainder = headerValue.slice(commaIndex + 1).trimStart();
  const equalsIndex = remainder.indexOf('=');
  const semicolonIndex = remainder.indexOf(';');

  if (equalsIndex <= 0) {
    return false;
  }

  if (semicolonIndex !== -1 && semicolonIndex < equalsIndex) {
    return false;
  }

  const cookieName = remainder.slice(0, equalsIndex).trim();
  return /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/.test(cookieName);
}

function splitCombinedSetCookieHeader(headerValue: string): string[] {
  const headers: string[] = [];
  let start = 0;

  for (let index = 0; index < headerValue.length; index += 1) {
    if (headerValue[index] === ',' && isCookieHeaderBoundary(headerValue, index)) {
      headers.push(headerValue.slice(start, index).trim());
      start = index + 1;
    }
  }

  headers.push(headerValue.slice(start).trim());
  return headers.filter(Boolean);
}

function getResponseCookieHost(request: NextRequest): string {
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host') ?? request.nextUrl.host;
  return host.split(':')[0]?.toLowerCase() ?? '';
}

function normalizeCookieDomain(domain: string): string {
  return domain.trim().replace(/^\./, '').toLowerCase();
}

function getRequestUrl(request: NextRequest): URL {
  try {
    return new URL(request.url);
  } catch {
    return request.nextUrl;
  }
}

function isApprovedLocalStagePartnerHttpRequest(request: NextRequest): boolean {
  const url = getRequestUrl(request);
  return (
    process.env.NODE_ENV !== 'production'
    && url.protocol === 'http:'
    && APPROVED_LOCAL_STAGE_PARTNER_HOSTS.has(url.host.toLowerCase())
  );
}

function isDomainCompatibleWithHost(domain: string, host: string): boolean {
  const normalizedDomain = normalizeCookieDomain(domain);
  const normalizedHost = host.toLowerCase();

  return normalizedHost === normalizedDomain || normalizedHost.endsWith(`.${normalizedDomain}`);
}

function normalizeSetCookieForRequest(headerValue: string, request: NextRequest): string {
  const host = getResponseCookieHost(request);
  const shouldStripSecure = isApprovedLocalStagePartnerHttpRequest(request);

  if (!host && !shouldStripSecure) {
    return headerValue;
  }

  const parts = headerValue.split(';').map((part) => part.trim());
  const domainAttribute = parts.find((part) => part.toLowerCase().startsWith('domain='));
  const shouldStripDomain = Boolean(
    host
      && domainAttribute
      && !isDomainCompatibleWithHost(domainAttribute.slice('domain='.length), host),
  );

  if (!shouldStripDomain && !shouldStripSecure) {
    return headerValue;
  }

  return parts
    .filter((part) => {
      if (shouldStripDomain && part === domainAttribute) {
        return false;
      }

      return !(shouldStripSecure && part.toLowerCase() === 'secure');
    })
    .join('; ');
}

function appendSetCookieHeaders(source: Response, target: NextResponse, request: NextRequest): void {
  for (const headerValue of getSetCookieHeaders(source)) {
    target.headers.append('set-cookie', normalizeSetCookieForRequest(headerValue, request));
  }
}

async function readErrorPayload(response: Response): Promise<{ detail: string }> {
  try {
    const payload = await response.json() as { detail?: string };
    return {
      detail: payload.detail || 'Two-factor verification failed.',
    };
  } catch {
    return {
      detail: 'Two-factor verification failed.',
    };
  }
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const transaction = parsePendingTwoFactorCookieValue(
    request.cookies.get(PENDING_2FA_COOKIE)?.value,
  );
  if (!transaction) {
    const response = NextResponse.json(
      { detail: 'Two-factor login session expired. Start sign-in again.' },
      { status: 401 },
    );
    response.cookies.delete(PENDING_2FA_COOKIE);
    return response;
  }

  let body: { code?: string };
  try {
    body = await request.json() as { code?: string };
  } catch {
    return NextResponse.json({ detail: 'Invalid request body.' }, { status: 400 });
  }

  const code = typeof body.code === 'string' ? body.code.trim() : '';
  if (!/^\d{6}$/.test(code)) {
    return NextResponse.json({ detail: 'Enter a valid 6-digit code.' }, { status: 400 });
  }

  let backendResponse: Response;
  try {
    backendResponse = await fetch(`${getBackendBaseUrl()}/api/v1/2fa/complete`, {
      method: 'POST',
      cache: 'no-store',
      headers: buildForwardHeaders(request, transaction.token),
      body: JSON.stringify({ code }),
    });
  } catch {
    return NextResponse.json({ detail: 'Authentication service is unavailable.' }, { status: 503 });
  }

  if (!backendResponse.ok) {
    const errorPayload = await readErrorPayload(backendResponse);
    const response = NextResponse.json(errorPayload, { status: backendResponse.status });
    if (backendResponse.status === 401) {
      response.cookies.delete(PENDING_2FA_COOKIE);
    }
    return response;
  }

  const redirectTo = new URL(transaction.returnTo, request.url);
  const defaultReturnTo = getDefaultPostLoginPath(transaction.locale);
  if (transaction.isNewUser && transaction.returnTo === defaultReturnTo) {
    redirectTo.searchParams.set('welcome', 'true');
  }

  const response = NextResponse.json({ redirect_to: redirectTo.pathname + redirectTo.search });
  response.cookies.delete(PENDING_2FA_COOKIE);
  appendSetCookieHeaders(backendResponse, response, request);
  return response;
}

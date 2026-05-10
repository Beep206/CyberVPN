import { NextRequest, NextResponse } from 'next/server';

import {
  parsePendingTwoFactorCookieValue,
  PENDING_2FA_COOKIE,
} from '@/features/auth/lib/pending-twofa';
import { getDefaultPostLoginPath } from '@/features/auth/lib/redirect-path';

function getBackendBaseUrl(): string {
  const baseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new Error('API_URL or NEXT_PUBLIC_API_URL must be configured.');
  }

  return baseUrl.replace(/\/$/, '');
}

function buildForwardHeaders(request: NextRequest, token: string): Headers {
  const headers = new Headers({
    accept: 'application/json',
    authorization: `Bearer ${token}`,
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

function getSetCookieHeaders(response: Response): string[] {
  const headers = response.headers as Headers & {
    getSetCookie?: () => string[];
  };

  if (typeof headers.getSetCookie === 'function') {
    const setCookieHeaders = headers.getSetCookie();
    if (setCookieHeaders.length > 0) {
      return setCookieHeaders;
    }
  }

  const setCookie = response.headers.get('set-cookie');
  return setCookie ? [setCookie] : [];
}

async function appendBackendAuthCookies(source: Response, target: NextResponse): Promise<void> {
  const headerValues = getSetCookieHeaders(source);
  if (headerValues.length > 0) {
    for (const headerValue of headerValues) {
      target.headers.append('Set-Cookie', headerValue);
      mirrorBackendCookieForNextResponse(headerValue, target);
    }
    return;
  }

  await appendJsonTokenFallbackCookies(source, target);
}

async function appendJsonTokenFallbackCookies(source: Response, target: NextResponse): Promise<void> {
  let payload: { access_token?: string; refresh_token?: string };
  try {
    payload = await source.clone().json() as { access_token?: string; refresh_token?: string };
  } catch {
    return;
  }

  const secure = process.env.NODE_ENV === 'production';
  for (const [name, value] of [
    ['access_token', payload.access_token],
    ['refresh_token', payload.refresh_token],
  ] as const) {
    if (!value) {
      continue;
    }
    target.cookies.set(name, value, {
      httpOnly: true,
      path: '/',
      sameSite: 'lax',
      secure,
    });
  }
}

function mirrorBackendCookieForNextResponse(headerValue: string, target: NextResponse): void {
  const [nameValue, ...attributes] = headerValue.split(';').map((part) => part.trim());
  const separatorIndex = nameValue.indexOf('=');
  if (separatorIndex <= 0) {
    return;
  }

  const name = nameValue.slice(0, separatorIndex);
  const value = nameValue.slice(separatorIndex + 1);
  const pathAttribute = attributes.find((attribute) => attribute.toLowerCase().startsWith('path='));
  const sameSiteAttribute = attributes.find((attribute) => attribute.toLowerCase().startsWith('samesite='));
  const sameSite = sameSiteAttribute?.split('=')[1]?.toLowerCase();

  target.cookies.set(name, value, {
    httpOnly: attributes.some((attribute) => attribute.toLowerCase() === 'httponly'),
    path: pathAttribute?.slice('path='.length) || '/',
    sameSite: sameSite === 'strict' || sameSite === 'lax' || sameSite === 'none' ? sameSite : undefined,
    secure: attributes.some((attribute) => attribute.toLowerCase() === 'secure'),
  });
}

function deletePendingTwoFactorCookie(response: NextResponse): void {
  response.headers.append(
    'Set-Cookie',
    `${PENDING_2FA_COOKIE}=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT`,
  );
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
    deletePendingTwoFactorCookie(response);
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
      deletePendingTwoFactorCookie(response);
    }
    return response;
  }

  const redirectTo = new URL(transaction.returnTo, request.url);
  const defaultReturnTo = getDefaultPostLoginPath(transaction.locale);
  if (transaction.isNewUser && transaction.returnTo === defaultReturnTo) {
    redirectTo.searchParams.set('welcome', 'true');
  }

  const response = NextResponse.json({ redirect_to: redirectTo.pathname + redirectTo.search });
  deletePendingTwoFactorCookie(response);
  await appendBackendAuthCookies(backendResponse, response);
  return response;
}

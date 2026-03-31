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
  appendSetCookieHeaders(backendResponse, response);
  return response;
}

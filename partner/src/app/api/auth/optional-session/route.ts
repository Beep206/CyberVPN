import { connection, NextResponse, type NextRequest } from 'next/server';

import {
  getCanonicalPartnerSurfaceHost,
  isKnownPartnerSurfaceHost,
  resolvePartnerSurfaceContext,
} from '@/features/storefront-shell/lib/runtime';

const SESSION_PATH = '/api/v1/auth/session';

function getBackendBaseUrl(): string | null {
  const configuredBaseUrl =
    process.env.API_INTERNAL_ORIGIN?.trim()
    || process.env.API_URL?.trim()
    || process.env.NEXT_PUBLIC_API_URL?.trim();

  if (!configuredBaseUrl) return null;

  return configuredBaseUrl.replace(/\/$/, '');
}

function resolveForwardedSurfaceHost(request: NextRequest): string {
  const requestHost = request.headers.get('host') ?? request.nextUrl.host;
  if (!isKnownPartnerSurfaceHost(requestHost)) {
    throw new Error('UNKNOWN_PARTNER_SURFACE_HOST');
  }

  return getCanonicalPartnerSurfaceHost(resolvePartnerSurfaceContext(requestHost));
}

function buildForwardHeaders(request: NextRequest): Headers {
  const headers = new Headers({
    accept: 'application/json',
  });

  const cookie = request.headers.get('cookie');
  if (cookie) {
    headers.set('cookie', cookie);
  }

  const requestId = request.headers.get('x-request-id');
  if (requestId) {
    headers.set('x-request-id', requestId);
  }

  headers.set('x-forwarded-host', resolveForwardedSurfaceHost(request));
  headers.set('x-forwarded-proto', 'https');

  return headers;
}

function emptyOptionalSession(): Response {
  return NextResponse.json(null, {
    status: 200,
    headers: {
      'Cache-Control': 'no-store',
    },
  });
}

function unknownPartnerHostResponse(): Response {
  return NextResponse.json(
    { detail: { code: 'UNKNOWN_PARTNER_SURFACE_HOST', message: 'Unknown partner surface host.' } },
    {
      status: 421,
      headers: {
        'Cache-Control': 'no-store',
      },
    },
  );
}

export async function GET(request: NextRequest): Promise<Response> {
  await connection();

  const baseUrl = getBackendBaseUrl();
  if (!baseUrl) {
    return emptyOptionalSession();
  }

  let headers: Headers;
  try {
    headers = buildForwardHeaders(request);
  } catch (error) {
    if (error instanceof Error && error.message === 'UNKNOWN_PARTNER_SURFACE_HOST') {
      return unknownPartnerHostResponse();
    }
    return emptyOptionalSession();
  }

  try {
    const response = await fetch(`${baseUrl}${SESSION_PATH}`, {
      cache: 'no-store',
      headers,
      method: 'GET',
    });

    if (response.status === 401 || response.status === 403 || !response.ok) {
      return emptyOptionalSession();
    }

    const payload = await response.json();
    return NextResponse.json(payload, {
      headers: {
        'Cache-Control': 'no-store',
      },
    });
  } catch {
    return emptyOptionalSession();
  }
}

import { connection, NextResponse, type NextRequest } from 'next/server';

const SESSION_PATH = '/api/v1/auth/session';

function getBackendBaseUrl(): string | null {
  const configuredBaseUrl = (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL)?.trim();
  if (!configuredBaseUrl) return null;

  return configuredBaseUrl.replace(/\/$/, '');
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

  const forwardedFor = request.headers.get('x-forwarded-for');
  if (forwardedFor) {
    headers.set('x-forwarded-for', forwardedFor);
  }

  headers.set('x-forwarded-host', request.headers.get('host') ?? request.nextUrl.host);
  headers.set('x-forwarded-proto', request.nextUrl.protocol.replace(':', '') || 'https');

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

export async function GET(request: NextRequest): Promise<Response> {
  await connection();

  const baseUrl = getBackendBaseUrl();
  if (!baseUrl) {
    return emptyOptionalSession();
  }

  try {
    const response = await fetch(`${baseUrl}${SESSION_PATH}`, {
      cache: 'no-store',
      headers: buildForwardHeaders(request),
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

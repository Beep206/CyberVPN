import { NextRequest, NextResponse } from 'next/server';

const ADMIN_CANONICAL_HOST = 'admin.cyber-vpn.net';

function getBackendBaseUrl(): string {
  const baseUrl =
    process.env.API_INTERNAL_ORIGIN?.trim()
    || process.env.API_URL?.trim()
    || process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!baseUrl) {
    throw new Error('API_INTERNAL_ORIGIN, API_URL or NEXT_PUBLIC_API_URL must be configured.');
  }

  return baseUrl.replace(/\/$/, '');
}

function buildSessionHeaders(request: NextRequest): Headers {
  const headers = new Headers({
    accept: 'application/json',
  });

  const cookie = request.headers.get('cookie');
  const userAgent = request.headers.get('user-agent');
  const acceptLanguage = request.headers.get('accept-language');
  const requestId = request.headers.get('x-request-id');

  if (cookie) {
    headers.set('cookie', cookie);
  }
  if (userAgent) {
    headers.set('user-agent', userAgent);
  }
  if (acceptLanguage) {
    headers.set('accept-language', acceptLanguage);
  }
  if (requestId) {
    headers.set('x-request-id', requestId);
  }
  headers.set('x-forwarded-host', ADMIN_CANONICAL_HOST);
  headers.set('x-forwarded-proto', 'https');

  return headers;
}

async function ensureAdminSession(request: NextRequest) {
  let sessionResponse: Response;
  try {
    sessionResponse = await fetch(`${getBackendBaseUrl()}/api/v1/auth/session`, {
      method: 'GET',
      cache: 'no-store',
      headers: buildSessionHeaders(request),
    });
  } catch {
    return NextResponse.json(
      { detail: 'Authentication service is unavailable.' },
      { status: 503 },
    );
  }

  if (sessionResponse.ok) {
    return null;
  }

  return NextResponse.json(
    { detail: 'Not authenticated.' },
    { status: sessionResponse.status === 401 ? 401 : 403 },
  );
}

function getTelegramBotSecret() {
  return process.env.TELEGRAM_BOT_INTERNAL_SECRET?.trim();
}

function buildProxyHeaders(
  request: NextRequest,
  secret: string,
  hasBody: boolean,
): Headers {
  const headers = new Headers({
    accept: 'application/json',
    'x-telegram-bot-secret': secret,
  });

  const userAgent = request.headers.get('user-agent');
  const acceptLanguage = request.headers.get('accept-language');
  const requestId = request.headers.get('x-request-id');

  if (hasBody) {
    headers.set('content-type', 'application/json');
  }
  if (userAgent) {
    headers.set('user-agent', userAgent);
  }
  if (acceptLanguage) {
    headers.set('accept-language', acceptLanguage);
  }
  if (requestId) {
    headers.set('x-request-id', requestId);
  }

  return headers;
}

async function proxyTelegramBotRequest(
  request: NextRequest,
  pathSegments: string[],
) {
  const authResponse = await ensureAdminSession(request);
  if (authResponse) {
    return authResponse;
  }

  const secret = getTelegramBotSecret();
  if (!secret) {
    return NextResponse.json(
      { detail: 'TELEGRAM_BOT_INTERNAL_SECRET is not configured.' },
      { status: 503 },
    );
  }

  const upstreamUrl = new URL(
    `${getBackendBaseUrl()}/api/v1/telegram/bot/${pathSegments
      .map((segment) => encodeURIComponent(segment))
      .join('/')}`,
  );
  upstreamUrl.search = new URL(request.url).search;

  const hasBody = request.method !== 'GET';
  const body = hasBody ? await request.text() : undefined;

  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetch(upstreamUrl, {
      method: request.method,
      cache: 'no-store',
      headers: buildProxyHeaders(request, secret, hasBody),
      body,
    });
  } catch {
    return NextResponse.json(
      { detail: 'Telegram bot integration is unavailable.' },
      { status: 503 },
    );
  }

  const responseText = await upstreamResponse.text();
  const contentType = upstreamResponse.headers.get('content-type');

  return new NextResponse(responseText || null, {
    status: upstreamResponse.status,
    headers: {
      'cache-control': 'no-store',
      ...(contentType ? { 'content-type': contentType } : {}),
    },
  });
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxyTelegramBotRequest(request, path);
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxyTelegramBotRequest(request, path);
}

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  return proxyTelegramBotRequest(request, path);
}

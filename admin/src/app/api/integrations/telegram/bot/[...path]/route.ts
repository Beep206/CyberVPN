import { NextRequest, NextResponse } from 'next/server';

function getBackendBaseUrl(): string {
  const baseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (!baseUrl) {
    throw new Error('API_URL or NEXT_PUBLIC_API_URL must be configured.');
  }

  return baseUrl.replace(/\/$/, '');
}

function buildSessionHeaders(request: NextRequest): Headers {
  const headers = new Headers({
    accept: 'application/json',
  });

  const cookie = request.headers.get('cookie');
  const forwardedFor = request.headers.get('x-forwarded-for');
  const userAgent = request.headers.get('user-agent');
  const acceptLanguage = request.headers.get('accept-language');

  if (cookie) {
    headers.set('cookie', cookie);
  }
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

  const forwardedFor = request.headers.get('x-forwarded-for');
  const userAgent = request.headers.get('user-agent');
  const acceptLanguage = request.headers.get('accept-language');

  if (hasBody) {
    headers.set('content-type', 'application/json');
  }
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
    `${getBackendBaseUrl()}/api/v1/telegram/bot/${pathSegments.join('/')}`,
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

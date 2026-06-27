import { NextRequest } from 'next/server';

const ADMIN_CANONICAL_HOST = 'admin.cyber-vpn.net';
const ADMIN_CANONICAL_ORIGIN = `https://${ADMIN_CANONICAL_HOST}`;
const APPROVED_LOCAL_STAGE_ADMIN_ORIGINS = new Set([
  'http://127.0.0.1:13001',
  'http://localhost:13001',
  'http://127.0.0.1:3000',
  'http://localhost:3000',
]);
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);
const PASSKEY_API_PREFIX = ['auth', 'passkeys'] as const;
const HOP_BY_HOP_HEADERS = new Set([
  'connection',
  'expect',
  'keep-alive',
  'proxy-authenticate',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
]);

export interface ApiProxyRouteContext {
  params: Promise<{
    path: string[];
  }>;
}

function getBackendBaseUrl(): string {
  const baseUrl =
    process.env.API_INTERNAL_ORIGIN?.trim()
    || process.env.API_URL?.trim()
    || process.env.NEXT_PUBLIC_API_URL?.trim()
    || 'http://localhost:8000';

  return baseUrl.replace(/\/$/, '');
}

function buildBackendUrl(request: NextRequest, path: string[], apiBasePath: string): string {
  const safePath = path.map((segment) => encodeURIComponent(segment)).join('/');
  const search = request.nextUrl.search;

  return `${getBackendBaseUrl()}${apiBasePath}/${safePath}${search}`;
}

function normalizeOrigin(value: string | null): string | null {
  if (!value) return null;

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function rewriteRefererToCanonicalOrigin(value: string): string {
  const url = new URL(value);
  return `${ADMIN_CANONICAL_ORIGIN}${url.pathname}${url.search}${url.hash}`;
}

function getRequestOrigin(request: NextRequest): string {
  try {
    return new URL(request.url).origin;
  } catch {
    return request.nextUrl.origin;
  }
}

function isPasskeyApiPath(path: string[]): boolean {
  return path[0] === PASSKEY_API_PREFIX[0] && path[1] === PASSKEY_API_PREFIX[1];
}

function isApprovedLocalStageAdminRequest(request: NextRequest): boolean {
  return APPROVED_LOCAL_STAGE_ADMIN_ORIGINS.has(getRequestOrigin(request));
}

function shouldPreserveLocalStagePasskeyOrigin(request: NextRequest, path: string[]): boolean {
  return isPasskeyApiPath(path) && isApprovedLocalStageAdminRequest(request);
}

function shouldUseSecureCookie(request: NextRequest): boolean {
  return !isApprovedLocalStageAdminRequest(request);
}

function normalizeApprovedLocalStageCsrfHeaders(request: NextRequest, headers: Headers, path: string[]): void {
  if (SAFE_METHODS.has(request.method.toUpperCase())) {
    return;
  }

  if (!isApprovedLocalStageAdminRequest(request)) {
    return;
  }

  if (shouldPreserveLocalStagePasskeyOrigin(request, path)) {
    return;
  }

  if (APPROVED_LOCAL_STAGE_ADMIN_ORIGINS.has(normalizeOrigin(headers.get('origin')) ?? '')) {
    headers.set('origin', ADMIN_CANONICAL_ORIGIN);
  }

  const referer = headers.get('referer');
  if (referer && APPROVED_LOCAL_STAGE_ADMIN_ORIGINS.has(normalizeOrigin(referer) ?? '')) {
    headers.set('referer', rewriteRefererToCanonicalOrigin(referer));
  }
}

function buildForwardHeaders(request: NextRequest, path: string[]): Headers {
  const headers = new Headers();

  for (const [key, value] of request.headers.entries()) {
    const normalizedKey = key.toLowerCase();

    if (
      HOP_BY_HOP_HEADERS.has(normalizedKey)
      || normalizedKey === 'host'
      || normalizedKey === 'x-forwarded-host'
      || normalizedKey === 'x-forwarded-proto'
      || normalizedKey === 'x-forwarded-port'
    ) {
      continue;
    }

    headers.set(key, value);
  }

  if (!headers.has('cookie')) {
    const cookieHeader = request.cookies
      .getAll()
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join('; ');

    if (cookieHeader) {
      headers.set('cookie', cookieHeader);
    }
  }

  headers.set('x-forwarded-host', ADMIN_CANONICAL_HOST);
  headers.set('x-forwarded-proto', 'https');
  headers.set('accept-encoding', 'identity');
  normalizeApprovedLocalStageCsrfHeaders(request, headers, path);

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

function normalizeSetCookieForRequest(headerValue: string, request: NextRequest): string {
  if (shouldUseSecureCookie(request)) {
    return headerValue;
  }

  return headerValue
    .split(';')
    .map((part) => part.trim())
    .filter((part) => part.toLowerCase() !== 'secure')
    .join('; ');
}

function buildResponseHeaders(upstreamResponse: Response, request: NextRequest): Headers {
  const headers = new Headers();

  for (const [key, value] of upstreamResponse.headers.entries()) {
    const normalizedKey = key.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(normalizedKey) || normalizedKey === 'set-cookie') {
      continue;
    }

    headers.set(key, value);
  }

  for (const cookie of getSetCookieHeaders(upstreamResponse)) {
    headers.append('set-cookie', normalizeSetCookieForRequest(cookie, request));
  }

  return headers;
}

export async function proxyApiRequest(
  request: NextRequest,
  context: ApiProxyRouteContext,
  apiBasePath: string,
): Promise<Response> {
  const { path } = await context.params;
  const body = request.method === 'GET' || request.method === 'HEAD'
    ? undefined
    : await request.arrayBuffer();

  const upstreamResponse = await fetch(buildBackendUrl(request, path, apiBasePath), {
    method: request.method,
    headers: buildForwardHeaders(request, path),
    body,
    cache: 'no-store',
    redirect: 'manual',
  });

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: buildResponseHeaders(upstreamResponse, request),
  });
}

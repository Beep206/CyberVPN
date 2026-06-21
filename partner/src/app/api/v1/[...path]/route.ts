import { NextRequest } from 'next/server';
import {
  getCanonicalPartnerSurfaceHost,
  isKnownPartnerSurfaceHost,
  resolvePartnerSurfaceContext,
} from '@/features/storefront-shell/lib/runtime';

const API_BASE_PATH = '/api/v1';
const APPROVED_LOCAL_STAGE_PARTNER_ORIGINS = new Set([
  'http://portal.localhost:3004',
  'http://storefront.localhost:3004',
  'http://127.0.0.1:3004',
  'http://localhost:3004',
  'http://portal.localhost:3002',
  'http://storefront.localhost:3002',
  'http://127.0.0.1:3002',
  'http://localhost:3002',
]);
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE']);
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

interface ApiProxyRouteContext {
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

function buildBackendUrl(request: NextRequest, path: string[]): string {
  const safePath = path.map((segment) => encodeURIComponent(segment)).join('/');
  const search = request.nextUrl.search;

  return `${getBackendBaseUrl()}${API_BASE_PATH}/${safePath}${search}`;
}

function normalizeOrigin(value: string | null): string | null {
  if (!value) return null;

  try {
    return new URL(value).origin;
  } catch {
    return null;
  }
}

function rewriteRefererToCanonicalOrigin(value: string, canonicalOrigin: string): string {
  const url = new URL(value);
  return `${canonicalOrigin}${url.pathname}${url.search}${url.hash}`;
}

function getRequestOrigin(request: NextRequest): string {
  try {
    return new URL(request.url).origin;
  } catch {
    return request.nextUrl.origin;
  }
}

function normalizeApprovedLocalStageCsrfHeaders(
  request: NextRequest,
  headers: Headers,
  canonicalOrigin: string,
): void {
  if (SAFE_METHODS.has(request.method.toUpperCase())) {
    return;
  }

  if (!APPROVED_LOCAL_STAGE_PARTNER_ORIGINS.has(getRequestOrigin(request))) {
    return;
  }

  if (APPROVED_LOCAL_STAGE_PARTNER_ORIGINS.has(normalizeOrigin(headers.get('origin')) ?? '')) {
    headers.set('origin', canonicalOrigin);
  }

  const referer = headers.get('referer');
  if (referer && APPROVED_LOCAL_STAGE_PARTNER_ORIGINS.has(normalizeOrigin(referer) ?? '')) {
    headers.set('referer', rewriteRefererToCanonicalOrigin(referer, canonicalOrigin));
  }
}

function resolveForwardedSurfaceHost(request: NextRequest): string {
  const requestHost = request.headers.get('host') ?? request.nextUrl.host;
  if (!isKnownPartnerSurfaceHost(requestHost)) {
    throw new Error('UNKNOWN_PARTNER_SURFACE_HOST');
  }

  const surfaceContext = resolvePartnerSurfaceContext(requestHost);
  return getCanonicalPartnerSurfaceHost(surfaceContext);
}

function buildForwardHeaders(request: NextRequest): Headers {
  const headers = new Headers();
  const forwardedHost = resolveForwardedSurfaceHost(request);
  const forwardedOrigin = `https://${forwardedHost}`;

  for (const [key, value] of request.headers.entries()) {
    const normalizedKey = key.toLowerCase();

    if (
      HOP_BY_HOP_HEADERS.has(normalizedKey)
      || normalizedKey === 'host'
      || normalizedKey === 'x-forwarded-host'
      || normalizedKey === 'x-forwarded-proto'
      || normalizedKey === 'x-forwarded-port'
      || normalizedKey === 'x-auth-realm'
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

  headers.set('x-forwarded-host', forwardedHost);
  headers.set('x-forwarded-proto', 'https');
  headers.set('accept-encoding', 'identity');
  normalizeApprovedLocalStageCsrfHeaders(request, headers, forwardedOrigin);

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

function buildResponseHeaders(upstreamResponse: Response): Headers {
  const headers = new Headers();

  for (const [key, value] of upstreamResponse.headers.entries()) {
    const normalizedKey = key.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(normalizedKey) || normalizedKey === 'set-cookie') {
      continue;
    }

    headers.set(key, value);
  }

  for (const cookie of getSetCookieHeaders(upstreamResponse)) {
    headers.append('set-cookie', cookie);
  }

  return headers;
}

async function proxyApiRequest(
  request: NextRequest,
  context: ApiProxyRouteContext,
): Promise<Response> {
  const { path } = await context.params;
  let headers: Headers;
  try {
    headers = buildForwardHeaders(request);
  } catch (error) {
    if (error instanceof Error && error.message === 'UNKNOWN_PARTNER_SURFACE_HOST') {
      return Response.json(
        { detail: { code: 'UNKNOWN_PARTNER_SURFACE_HOST', message: 'Unknown partner surface host.' } },
        { status: 421, headers: { 'cache-control': 'no-store' } },
      );
    }
    throw error;
  }
  const body = request.method === 'GET' || request.method === 'HEAD'
    ? undefined
    : await request.arrayBuffer();

  const upstreamResponse = await fetch(buildBackendUrl(request, path), {
    method: request.method,
    headers,
    body,
    cache: 'no-store',
    redirect: 'manual',
  });

  return new Response(upstreamResponse.body, {
    status: upstreamResponse.status,
    statusText: upstreamResponse.statusText,
    headers: buildResponseHeaders(upstreamResponse),
  });
}

export function GET(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context);
}

export function POST(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context);
}

export function PUT(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context);
}

export function PATCH(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context);
}

export function DELETE(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context);
}

export function HEAD(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context);
}

export function OPTIONS(request: NextRequest, context: ApiProxyRouteContext) {
  return proxyApiRequest(request, context);
}

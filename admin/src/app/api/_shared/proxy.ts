import { NextRequest } from 'next/server';

const ADMIN_CANONICAL_HOST = 'admin.cyber-vpn.net';
const ADMIN_CANONICAL_ORIGIN = `https://${ADMIN_CANONICAL_HOST}`;
const MAX_PROXY_BODY_BYTES = 1_048_576;
const APPROVED_LOCAL_STAGE_ADMIN_ORIGINS = new Set([
  'http://127.0.0.1:13001',
  'http://localhost:13001',
  'http://admin.localhost:13001',
  'http://127.0.0.1:3000',
  'http://localhost:3000',
  'http://127.0.0.1:3001',
  'http://localhost:3001',
  'http://admin.localhost:3001',
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
const INTERNAL_SECRET_HEADERS = new Set([
  'x-backend-internal-secret',
  'x-payment-settlement-worker-secret',
  'x-telegram-bot-secret',
]);
const SAFE_FORWARD_HEADERS = new Set([
  'accept',
  'accept-language',
  'content-language',
  'content-type',
  'cookie',
  'idempotency-key',
  'origin',
  'referer',
  'user-agent',
  'x-correlation-id',
  'x-csrf-token',
  'x-fresh-auth-grant-id',
  'x-idempotency-key',
  'x-request-id',
  'x-requested-with',
  'x-xsrf-token',
]);
const SET_COOKIE_BOUNDARY_NAMES = [
  '__Host-cvpn_device_id',
  '__Host-cvpn_private_catalog_session',
  'access_token',
  'customer_access_token',
  'customer_refresh_token',
  'cv_partner_attribution',
  'cv_ref_attribution',
  'partner_access_token',
  'partner_refresh_token',
  'refresh_token',
];

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
  const trailingSlash = request.nextUrl.pathname.endsWith('/') ? '/' : '';

  return `${getBackendBaseUrl()}${apiBasePath}/${safePath}${trailingSlash}${search}`;
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

    if (!SAFE_FORWARD_HEADERS.has(normalizedKey)
      || HOP_BY_HOP_HEADERS.has(normalizedKey)
      || INTERNAL_SECRET_HEADERS.has(normalizedKey)
      || normalizedKey === 'host') {
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
    return headers.getSetCookie().flatMap(splitSetCookieHeader);
  }

  const setCookie = response.headers.get('set-cookie');
  return setCookie ? splitSetCookieHeader(setCookie) : [];
}

function splitSetCookieHeader(headerValue: string): string[] {
  const cookies: string[] = [];
  let start = 0;

  for (let index = 0; index < headerValue.length; index += 1) {
    if (headerValue[index] !== ',') continue;

    const candidate = headerValue.slice(index + 1).trimStart();
    if (!SET_COOKIE_BOUNDARY_NAMES.some((name) => candidate.startsWith(`${name}=`))) {
      continue;
    }

    cookies.push(headerValue.slice(start, index).trim());
    start = index + 1;
  }

  cookies.push(headerValue.slice(start).trim());
  return cookies.filter(Boolean);
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

function bodyTooLargeResponse(): Response {
  return Response.json(
    { detail: { code: 'REQUEST_BODY_TOO_LARGE', message: 'Request body is too large.' } },
    { status: 413, headers: { 'cache-control': 'no-store' } },
  );
}

function readContentLength(request: NextRequest): number | null {
  const rawValue = request.headers.get('content-length');
  if (!rawValue) return null;

  const parsed = Number(rawValue);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : MAX_PROXY_BODY_BYTES + 1;
}

async function readBoundedRequestBody(request: NextRequest): Promise<ArrayBuffer | Response | undefined> {
  if (request.method === 'GET' || request.method === 'HEAD') {
    return undefined;
  }

  const contentLength = readContentLength(request);
  if (contentLength !== null && contentLength > MAX_PROXY_BODY_BYTES) {
    return bodyTooLargeResponse();
  }

  if (!request.body) {
    return new ArrayBuffer(0);
  }

  const chunks: Uint8Array[] = [];
  let totalBytes = 0;
  const reader = request.body.getReader();

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      if (!value) continue;

      totalBytes += value.byteLength;
      if (totalBytes > MAX_PROXY_BODY_BYTES) {
        await reader.cancel().catch(() => undefined);
        return bodyTooLargeResponse();
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }

  const body = new Uint8Array(totalBytes);
  let offset = 0;
  for (const chunk of chunks) {
    body.set(chunk, offset);
    offset += chunk.byteLength;
  }

  return body.buffer;
}

export async function proxyApiRequest(
  request: NextRequest,
  context: ApiProxyRouteContext,
  apiBasePath: string,
): Promise<Response> {
  const { path } = await context.params;
  const body = await readBoundedRequestBody(request);
  if (body instanceof Response) {
    return body;
  }

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

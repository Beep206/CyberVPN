import { NextRequest, NextResponse } from 'next/server';
import { createHash, randomBytes } from 'crypto';
import { SITE_URL } from '@/shared/lib/seo-route-policy';

type CaptureResponse = {
  redirect_url: string;
};

const PARTNER_BROWSER_COOKIE_NAME = 'cv_partner_browser';
const PARTNER_BROWSER_COOKIE_MAX_AGE_SECONDS = 30 * 24 * 60 * 60;
const CUSTOMER_APP_ORIGIN = 'https://my.cyber-vpn.net';
const PUBLIC_CAPTURE_HOSTS = new Set(['cyber-vpn.net', 'www.cyber-vpn.net', 'my.cyber-vpn.net']);
const LOCAL_CAPTURE_HOSTS = new Set(['localhost', '127.0.0.1', '::1', 'testserver']);

const CAMPAIGN_KEYS = [
  'utm_source',
  'utm_medium',
  'utm_campaign',
  'utm_term',
  'utm_content',
  'gclid',
  'fbclid',
  'click_id',
  'sub_id',
] as const;

function resolveBackendApiBaseUrl(): string {
  const baseUrl = (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL)?.trim();
  if (!baseUrl) {
    throw new Error('API_URL or NEXT_PUBLIC_API_URL must be configured.');
  }
  return `${baseUrl.replace(/\/$/, '')}/api/v1`;
}

function collectCampaignParams(request: NextRequest): Record<string, string> {
  const params: Record<string, string> = {};
  for (const key of CAMPAIGN_KEYS) {
    const value = request.nextUrl.searchParams.get(key)?.trim();
    if (value) {
      params[key] = value.slice(0, 200);
    }
  }
  for (const [key, value] of request.nextUrl.searchParams.entries()) {
    if (key.startsWith('sub_') && value.trim()) {
      params[key] = value.trim().slice(0, 200);
    }
  }
  return params;
}

function collectSubIds(request: NextRequest): Record<string, string> {
  const params: Record<string, string> = {};
  for (const [key, value] of request.nextUrl.searchParams.entries()) {
    if (key.startsWith('sub_') && value.trim()) {
      params[key.replace(/^sub_/, '')] = value.trim().slice(0, 160);
    }
  }
  return params;
}

function buildSanitizedSourcePath(request: NextRequest): string {
  const params = new URLSearchParams();
  request.nextUrl.searchParams.forEach((value, key) => {
    if (key.toLowerCase() !== 'pat') {
      params.append(key, value);
    }
  });
  const query = params.toString();
  return `${request.nextUrl.pathname}${query ? `?${query}` : ''}`;
}

function resolveLocale(request: NextRequest): string {
  const explicit = request.nextUrl.searchParams.get('locale')?.trim();
  if (explicit && /^[a-z]{2}-[A-Z]{2}$/.test(explicit)) {
    return explicit;
  }
  const cookieLocale = request.cookies.get('NEXT_LOCALE')?.value?.trim();
  if (cookieLocale && /^[a-z]{2}-[A-Z]{2}$/.test(cookieLocale)) {
    return cookieLocale;
  }
  const acceptLanguage = request.headers.get('accept-language') ?? '';
  return acceptLanguage.toLowerCase().startsWith('en') ? 'en-EN' : 'ru-RU';
}

function resolveDestinationPath(request: NextRequest): string | null {
  const destinationKey = request.nextUrl.searchParams.get('destination')?.trim();
  if (destinationKey === 'pricing') {
    return '/pricing';
  }
  if (destinationKey === 'download') {
    return '/download';
  }
  return null;
}

function resolveBrowserToken(request: NextRequest): { token: string; created: boolean } {
  const existing = request.cookies.get(PARTNER_BROWSER_COOKIE_NAME)?.value?.trim();
  if (existing && /^[A-Za-z0-9_-]{24,128}$/.test(existing)) {
    return { token: existing, created: false };
  }
  return { token: randomBytes(32).toString('base64url'), created: true };
}

function buildCaptureIdempotencyKey(publicToken: string, browserToken: string): string {
  return createHash('sha256')
    .update(`partner-capture:${publicToken}:${browserToken}`)
    .digest('hex');
}

function isProductionRuntime(): boolean {
  return process.env.NODE_ENV === 'production'
    || process.env.NEXT_PUBLIC_APP_ENV === 'production';
}

function normalizeHost(rawHost: string | null): string | null {
  if (!rawHost) {
    return null;
  }
  const host = rawHost.split(',', 1)[0]?.trim().toLowerCase() ?? '';
  if (!host) {
    return null;
  }
  if (host.startsWith('[')) {
    const bracketIndex = host.indexOf(']');
    return bracketIndex > 0 ? host.slice(1, bracketIndex) : null;
  }
  return host.split(':', 1)[0] || null;
}

function resolveTrustedPublicHost(request: NextRequest): string | null {
  const host = normalizeHost(request.headers.get('host')) ?? normalizeHost(request.nextUrl.host);
  if (!host) {
    return null;
  }
  if (PUBLIC_CAPTURE_HOSTS.has(host)) {
    return host;
  }
  if (!isProductionRuntime() && (LOCAL_CAPTURE_HOSTS.has(host) || host.endsWith('.localhost'))) {
    return host;
  }
  return null;
}

function safeCaptureRedirect(rawRedirectUrl: string): URL {
  try {
    const redirectUrl = new URL(rawRedirectUrl);
    const allowedOrigins = new Set([SITE_URL, CUSTOMER_APP_ORIGIN]);
    if (allowedOrigins.has(redirectUrl.origin) && /^\/[a-z]{2}-[A-Z]{2}\//.test(redirectUrl.pathname)) {
      return redirectUrl;
    }
  } catch {
    // Fall through to the canonical registration page.
  }
  return new URL('/ru-RU/register', SITE_URL);
}

function withBrowserCookie(response: NextResponse, browserToken: string): NextResponse {
  response.cookies.set(PARTNER_BROWSER_COOKIE_NAME, browserToken, {
    httpOnly: true,
    maxAge: PARTNER_BROWSER_COOKIE_MAX_AGE_SECONDS,
    path: '/',
    sameSite: 'lax',
    secure: isProductionRuntime(),
  });
  response.headers.set('Cache-Control', 'no-store');
  return response;
}

async function preserveRateLimitResponse(response: Response): Promise<NextResponse> {
  let payload: unknown = {
    detail: {
      code: 'PARTNER_ATTRIBUTION_RATE_LIMITED',
      message: 'Too many partner attribution attempts.',
    },
  };
  try {
    payload = await response.clone().json() as unknown;
  } catch {
    // Keep the stable fallback body when the backend returns a non-JSON rate-limit payload.
  }
  const nextResponse = NextResponse.json(payload, { status: 429 });
  const retryAfter = response.headers.get('Retry-After');
  if (retryAfter) {
    nextResponse.headers.set('Retry-After', retryAfter);
  }
  nextResponse.headers.set('Cache-Control', 'no-store');
  return nextResponse;
}

async function preserveCaptureFailureResponse(response: Response): Promise<NextResponse> {
  let payload: unknown = {
    detail: {
      code: 'PARTNER_ATTRIBUTION_CAPTURE_FAILED',
      message: 'Partner attribution link cannot be used.',
    },
  };
  try {
    payload = await response.clone().json() as unknown;
  } catch {
    // Keep a stable public failure body when the backend sends a non-JSON error.
  }
  const status = response.status >= 400 && response.status < 500 ? response.status : 503;
  const nextResponse = NextResponse.json(payload, { status });
  nextResponse.headers.set('Cache-Control', 'no-store');
  return nextResponse;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ publicToken: string }> },
) {
  const { publicToken } = await params;
  const trustedPublicHost = resolveTrustedPublicHost(request);
  if (!trustedPublicHost) {
    return NextResponse.json(
      {
        detail: {
          code: 'PARTNER_ATTRIBUTION_HOST_NOT_TRUSTED',
          message: 'Partner attribution capture host is not trusted.',
        },
      },
      { status: 421 },
    );
  }
  const browser = resolveBrowserToken(request);
  const captureIdempotencyKey = buildCaptureIdempotencyKey(publicToken, browser.token);
  const response = await fetch(`${resolveBackendApiBaseUrl()}/partner-attribution/capture`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': captureIdempotencyKey,
      'X-Forwarded-Host': trustedPublicHost,
    },
    body: JSON.stringify({
      public_token: publicToken,
      source_path: buildSanitizedSourcePath(request),
      destination_path: resolveDestinationPath(request),
      locale: resolveLocale(request),
      sale_channel: request.nextUrl.searchParams.get('channel')?.trim() || 'content',
      sub_ids: collectSubIds(request),
      click_id: request.nextUrl.searchParams.get('click_id')?.trim() || null,
      browser_key: browser.token,
      campaign_params: collectCampaignParams(request),
    }),
    cache: 'no-store',
  });

  if (!response.ok) {
    if (response.status === 429) {
      return preserveRateLimitResponse(response);
    }
    return preserveCaptureFailureResponse(response);
  }

  const payload = await response.json() as CaptureResponse;
  return withBrowserCookie(NextResponse.redirect(safeCaptureRedirect(payload.redirect_url)), browser.token);
}

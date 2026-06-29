// @vitest-environment node

import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { NextRequest } from 'next/server';

// Mock next-intl/middleware to pass through
vi.mock('next-intl/middleware', () => ({
  default: () => () => new Response(null, { status: 200 }),
}));

vi.mock('@/i18n/config', () => ({
  locales: ['en-EN', 'ru-RU'],
  defaultLocale: 'en-EN',
}));

// Import after mocks
const {
  proxy,
  resetCustomerSiteRuntimeCacheForTests,
} = await import('../proxy');

const ORIGINAL_API_URL = process.env.API_URL;
const ORIGINAL_API_INTERNAL_ORIGIN = process.env.API_INTERNAL_ORIGIN;
const ORIGINAL_NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;
const ORIGINAL_CUSTOMER_SITE_MODE_FALLBACK = process.env.CUSTOMER_SITE_MODE_FALLBACK;

type SiteRuntimeOverrides = {
  customer_site_mode?: 'full_site' | 'cabinet_only' | 'maintenance';
  public_hosts?: string[];
  cabinet_hosts?: string[];
  cabinet_destination_path?: string;
  allowed_path_prefixes?: string[];
  cabinet_allowed_prefixes?: string[];
  cabinet_marketing_route_action?: 'redirect_public' | 'allow' | 'not_found';
  public_marketing_destination_path?: string;
  legal_path_prefixes?: string[];
  operational_path_prefixes?: string[];
  preserve_query_keys?: string[];
};

function restoreEnvVar(name: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[name];
    return;
  }

  process.env[name] = value;
}

function createRequest(
  path: string,
  cookies?: Record<string, string>,
  baseUrl = 'http://localhost:3000',
  headers?: HeadersInit,
): NextRequest {
  const url = new URL(path, baseUrl);
  const req = new NextRequest(url, { headers });
  if (cookies) {
    for (const [name, value] of Object.entries(cookies)) {
      req.cookies.set(name, value);
    }
  }
  return req;
}

function createProxiedRequest(path: string, forwardedHost: string): NextRequest {
  return createRequest(path, undefined, 'http://cybervpn-frontend:3000', {
    host: 'cybervpn-frontend:3000',
    'x-forwarded-host': forwardedHost,
    'x-forwarded-proto': 'https',
  });
}

function mockCustomerSiteRuntime(overrides: SiteRuntimeOverrides = {}) {
  process.env.API_URL = 'https://backend.cybervpn.test';
  process.env.NEXT_PUBLIC_API_URL = '';
  const response = {
    site: {
      customer_site_mode: 'cabinet_only',
      cabinet_only: overrides.customer_site_mode === undefined || overrides.customer_site_mode === 'cabinet_only',
      public_hosts: ['cyber-vpn.net', 'www.cyber-vpn.net'],
      cabinet_hosts: ['my.cyber-vpn.net'],
      cabinet_destination_path: '/dashboard',
      allowed_path_prefixes: [
        '/login',
        '/register',
        '/verify',
        '/reset-password',
        '/magic-link',
        '/oauth',
        '/telegram-link',
        '/r/',
        '/p/',
      ],
      cabinet_allowed_prefixes: [
        '/dashboard',
        '/subscriptions',
        '/support',
        '/settings',
        '/rewards',
        '/messages',
        '/onboarding',
        '/login',
        '/register',
      ],
      cabinet_marketing_route_action: 'redirect_public',
      public_marketing_destination_path: '/',
      legal_path_prefixes: ['/privacy', '/privacy-policy', '/terms', '/refund-policy'],
      operational_path_prefixes: ['/status', '/telegram-widget', '/.well-known'],
      preserve_query_keys: ['ref', 'referral', 'utm_source', 'utm_campaign'],
      ...overrides,
    },
  };
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(response), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  }));
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

beforeEach(() => {
  resetCustomerSiteRuntimeCacheForTests();
  process.env.API_INTERNAL_ORIGIN = '';
  process.env.API_URL = '';
  process.env.NEXT_PUBLIC_API_URL = '';
  delete process.env.CUSTOMER_SITE_MODE_FALLBACK;
});

afterEach(() => {
  resetCustomerSiteRuntimeCacheForTests();
  restoreEnvVar('API_INTERNAL_ORIGIN', ORIGINAL_API_INTERNAL_ORIGIN);
  restoreEnvVar('API_URL', ORIGINAL_API_URL);
  restoreEnvVar('NEXT_PUBLIC_API_URL', ORIGINAL_NEXT_PUBLIC_API_URL);
  restoreEnvVar('CUSTOMER_SITE_MODE_FALLBACK', ORIGINAL_CUSTOMER_SITE_MODE_FALLBACK);
  vi.unstubAllGlobals();
});

describe('proxy routing', () => {
  it('passes dashboard route through on cabinet host (auth handled by AuthGuard)', async () => {
    const req = createRequest('/en-EN/dashboard/servers', undefined, 'https://my.cyber-vpn.net');
    const res = await proxy(req);

    // No redirect — AuthGuard in the (dashboard) layout handles auth
    expect(res.status).toBe(200);
  });

  it('passes dashboard route with auth cookie through on cabinet host', async () => {
    const req = createRequest('/en-EN/dashboard/servers', {
      access_token: 'some-token-value',
    }, 'https://my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes support route through on cabinet host', async () => {
    const req = createRequest('/ru-RU/support', undefined, 'https://my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes public login route through', async () => {
    const req = createRequest('/en-EN/login');
    const res = await proxy(req);

    expect(res.status).toBe(200);
  });

  it('redirects public dashboard route to cabinet host', async () => {
    const req = createRequest('/ru-RU/dashboard/analytics', undefined, 'https://cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/ru-RU/dashboard/analytics');
  });

  it('redirects public support route to cabinet host', async () => {
    const req = createRequest('/ru-RU/support', undefined, 'https://cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/ru-RU/support');
  });

  it('redirects public rewards and messages routes to cabinet host', async () => {
    for (const path of ['/en-EN/rewards/invites', '/en-EN/messages']) {
      const req = createRequest(path, undefined, 'https://cyber-vpn.net');
      const res = await proxy(req);

      expect(res.status).toBe(307);
      expect(res.headers.get('location')).toBe(`https://my.cyber-vpn.net${path}`);
    }
  });

  it('redirects short referral links to localized cabinet registration', async () => {
    const req = createRequest('/r/CYBER42?utm_source=share', undefined, 'https://cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe(
      'https://my.cyber-vpn.net/en-EN/register?ref=CYBER42&utm_source=share',
    );
  });

  it('drops non-campaign parameters from short referral redirects', async () => {
    const req = createRequest(
      '/r/CYBER42?utm_source=share&redirect=https%3A%2F%2Fevil.example%2Fcb&next=/wallet',
      undefined,
      'https://cyber-vpn.net',
    );
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe(
      'https://my.cyber-vpn.net/en-EN/register?ref=CYBER42&utm_source=share',
    );
  });

  it('does not treat auth callback code parameters as referral codes', async () => {
    const req = createRequest('/en-EN/login?code=oauth-code-42', undefined, 'https://cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('redirects localized short referral links without losing locale', async () => {
    const req = createRequest('/ru-RU/r/CYBER42', undefined, 'https://cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/ru-RU/register?ref=CYBER42');
  });

  it('passes canonical partner attribution links through without locale redirect', async () => {
    const req = createRequest('/p/partner-token-42?utm_source=share', undefined, 'https://cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('redirects localized partner attribution links back to the canonical public route', async () => {
    const req = createRequest('/ru-RU/p/partner-token-42?utm_source=share', undefined, 'https://cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://cyber-vpn.net/p/partner-token-42?utm_source=share');
  });

  it('redirects cabinet partner attribution links to the canonical public route', async () => {
    const req = createRequest('/p/partner-token-42?utm_source=share', undefined, 'https://my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://cyber-vpn.net/p/partner-token-42?utm_source=share');
  });

  it('redirects legacy referral code URLs to canonical cabinet registration', async () => {
    const req = createRequest('/ru-RU/referral?code=CYBER42&utm_campaign=friend', undefined, 'https://cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe(
      'https://my.cyber-vpn.net/ru-RU/register?ref=CYBER42&utm_campaign=friend',
    );
  });

  it('redirects public dashboard route by Host header when runtime URL is local', async () => {
    const req = createRequest(
      '/en-EN/dashboard?tab=ops',
      undefined,
      'http://127.0.0.1:9001',
      { host: 'cyber-vpn.net:9001' },
    );
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/en-EN/dashboard?tab=ops');
  });

  it('redirects production proxied public dashboard routes without leaking the app port', async () => {
    const req = createProxiedRequest('/en-EN/dashboard?tab=ops', 'cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/en-EN/dashboard?tab=ops');
  });

  it('redirects public delete-account route to cabinet host', async () => {
    const req = createRequest('/ru-RU/delete-account', undefined, 'https://cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/ru-RU/delete-account');
  });

  it('passes delete-account route through on cabinet host', async () => {
    const req = createRequest('/ru-RU/delete-account', undefined, 'https://my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(200);
  });

  it('passes register route through', async () => {
    const req = createRequest('/en-EN/register');
    const res = await proxy(req);

    expect(res.status).toBe(200);
  });

  it('redirects admin mirror host to canonical admin host', async () => {
    const req = createRequest('/en-EN/dashboard?tab=ops', undefined, 'https://admin.cyber-vpn.org');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://admin.cyber-vpn.net/en-EN/dashboard?tab=ops');
  });

  it('redirects cabinet root to localized dashboard', async () => {
    const req = createRequest('/', undefined, 'https://my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/en-EN/dashboard');
  });

  it('redirects cabinet root by Host header when runtime URL is local', async () => {
    const req = createRequest(
      '/',
      undefined,
      'http://127.0.0.1:9001',
      { host: 'my.cyber-vpn.net:9001' },
    );
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/en-EN/dashboard');
  });

  it('redirects production proxied cabinet root without leaking the app port', async () => {
    const req = createProxiedRequest('/', 'my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://my.cyber-vpn.net/en-EN/dashboard');
  });

  it('keeps public marketing routes canonical on public host', async () => {
    const req = createRequest('/ru-RU/pricing', undefined, 'https://cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(200);
  });

  it('redirects public marketing routes to cabinet dashboard in cabinet-only runtime', async () => {
    const fetchMock = mockCustomerSiteRuntime();
    const req = createRequest(
      '/ru-RU/pricing?utm_source=launch&ref=FRIEND42&redirect=https%3A%2F%2Fevil.example%2Fcb',
      undefined,
      'https://cyber-vpn.net',
    );
    const res = await proxy(req);

    expect(fetchMock).toHaveBeenCalledWith(
      'https://backend.cybervpn.test/api/v1/client/capabilities',
      expect.objectContaining({ cache: 'no-store' }),
    );
    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe(
      'https://my.cyber-vpn.net/ru-RU/dashboard?utm_source=launch&ref=FRIEND42',
    );
  });

  it('uses the internal API origin before public API env for site-mode runtime', async () => {
    process.env.API_INTERNAL_ORIGIN = 'https://internal-backend.cybervpn.test';
    process.env.API_URL = 'https://backend.cybervpn.test';
    process.env.NEXT_PUBLIC_API_URL = 'https://public-api.cybervpn.test';
    const fetchMock = mockCustomerSiteRuntime();
    const req = createRequest('/ru-RU/pricing', undefined, 'https://cyber-vpn.net');

    await proxy(req);

    expect(fetchMock).toHaveBeenCalledWith(
      'https://internal-backend.cybervpn.test/api/v1/client/capabilities',
      expect.objectContaining({ cache: 'no-store' }),
    );
  });

  it('redirects public auth routes to the same cabinet auth route in cabinet-only runtime', async () => {
    mockCustomerSiteRuntime();
    const req = createRequest(
      '/ru-RU/login?ref=FRIEND42&code=oauth-code-42&redirect=https%3A%2F%2Fevil.example%2Fcb',
      undefined,
      'https://cyber-vpn.net',
    );
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe(
      'https://my.cyber-vpn.net/ru-RU/login?ref=FRIEND42&code=oauth-code-42',
    );
  });

  it('allows legal routes on public host in cabinet-only runtime', async () => {
    mockCustomerSiteRuntime();
    const req = createRequest(
      '/ru-RU/privacy-policy?utm_source=legal',
      undefined,
      'https://cyber-vpn.net',
    );
    const res = await proxy(req);

    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('allows cabinet routes from backend cabinet prefix snapshot in cabinet-only runtime', async () => {
    mockCustomerSiteRuntime({
      cabinet_allowed_prefixes: ['/dashboard', '/subscriptions', '/onboarding'],
    });
    const req = createRequest('/ru-RU/onboarding/code', undefined, 'https://my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('allows cabinet rewards and messages RSC requests in cabinet-only runtime', async () => {
    mockCustomerSiteRuntime({
      cabinet_allowed_prefixes: ['/dashboard', '/rewards', '/messages'],
    });

    for (const path of ['/en-EN/rewards/invites?_rsc=probe', '/en-EN/messages?_rsc=probe']) {
      const req = createProxiedRequest(path, 'my.cyber-vpn.net');
      const res = await proxy(req);

      expect(res.status).toBe(200);
      expect(res.headers.get('location')).toBeNull();
    }
  });

  it('keeps mandatory cabinet routes when capabilities only include miniapp', async () => {
    mockCustomerSiteRuntime({
      cabinet_allowed_prefixes: ['/miniapp'],
    });

    for (const path of ['/en-EN/rewards/invites?_rsc=probe', '/en-EN/messages?_rsc=probe']) {
      const req = createProxiedRequest(path, 'my.cyber-vpn.net');
      const res = await proxy(req);

      expect(res.status).toBe(200);
      expect(res.headers.get('location')).toBeNull();
    }
  });

  it('allows normal browser navigation to mandatory cabinet routes with stale capabilities', async () => {
    mockCustomerSiteRuntime({
      cabinet_allowed_prefixes: ['/miniapp'],
    });

    for (const path of ['/en-EN/rewards/invites', '/en-EN/messages']) {
      const req = createRequest(path, undefined, 'https://my.cyber-vpn.net');
      const res = await proxy(req);

      expect(res.status).toBe(200);
      expect(res.headers.get('location')).toBeNull();
    }
  });

  it('redirects cabinet marketing routes to configured public destination in cabinet-only runtime', async () => {
    mockCustomerSiteRuntime({
      public_marketing_destination_path: '/',
      preserve_query_keys: ['ref', 'utm_source'],
    });
    const req = createRequest(
      '/ru-RU/pricing?utm_source=launch&ref=FRIEND42&redirect=https%3A%2F%2Fevil.example%2Fcb',
      undefined,
      'https://my.cyber-vpn.net',
    );
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe(
      'https://cyber-vpn.net/ru-RU?utm_source=launch&ref=FRIEND42',
    );
  });

  it('redirects unknown cabinet-host marketing routes to public for normal navigation', async () => {
    mockCustomerSiteRuntime({
      public_marketing_destination_path: '/',
      preserve_query_keys: ['ref', 'utm_source'],
    });
    const req = createRequest(
      '/en-EN/features?utm_source=launch&ref=FRIEND42&redirect=https%3A%2F%2Fevil.example%2Fcb',
      undefined,
      'https://my.cyber-vpn.net',
    );
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe(
      'https://cyber-vpn.net/en-EN?utm_source=launch&ref=FRIEND42',
    );
  });

  it('returns not found without Location for unknown cabinet-host RSC requests', async () => {
    mockCustomerSiteRuntime({
      public_marketing_destination_path: '/',
      preserve_query_keys: ['ref', 'utm_source'],
    });
    const req = createProxiedRequest('/en-EN/features?_rsc=probe', 'my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(404);
    expect(res.headers.get('location')).toBeNull();
  });

  it('does not redirect cabinet RSC preflight requests with stale capabilities', async () => {
    mockCustomerSiteRuntime({
      cabinet_allowed_prefixes: ['/miniapp'],
    });

    const req = new NextRequest(new URL('/en-EN/rewards/invites', 'http://cybervpn-frontend:3000'), {
      method: 'OPTIONS',
      headers: {
        host: 'cybervpn-frontend:3000',
        'x-forwarded-host': 'my.cyber-vpn.net',
        'x-forwarded-proto': 'https',
        origin: 'https://my.cyber-vpn.net',
        'access-control-request-method': 'GET',
        'access-control-request-headers': 'rsc,next-router-state-tree',
      },
    });
    const res = await proxy(req);

    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('returns not found without Location for unknown cabinet-host RSC preflight', async () => {
    mockCustomerSiteRuntime({
      public_marketing_destination_path: '/',
    });

    const req = new NextRequest(new URL('/en-EN/features', 'http://cybervpn-frontend:3000'), {
      method: 'OPTIONS',
      headers: {
        host: 'cybervpn-frontend:3000',
        'x-forwarded-host': 'my.cyber-vpn.net',
        'x-forwarded-proto': 'https',
        origin: 'https://my.cyber-vpn.net',
        'access-control-request-method': 'GET',
        'access-control-request-headers': 'rsc,next-router-state-tree',
      },
    });
    const res = await proxy(req);

    expect(res.status).toBe(404);
    expect(res.headers.get('location')).toBeNull();
  });

  it('allows cabinet marketing routes when backend snapshot explicitly allows them', async () => {
    mockCustomerSiteRuntime({ cabinet_marketing_route_action: 'allow' });
    const req = createRequest('/ru-RU/pricing', undefined, 'https://my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('returns not found for cabinet marketing routes when backend snapshot requires it', async () => {
    mockCustomerSiteRuntime({ cabinet_marketing_route_action: 'not_found' });
    const req = createRequest('/ru-RU/pricing', undefined, 'https://my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(404);
    expect(res.headers.get('location')).toBeNull();
  });

  it('uses cabinet-only fallback when runtime fetch fails', async () => {
    process.env.API_URL = 'https://backend.cybervpn.test';
    process.env.CUSTOMER_SITE_MODE_FALLBACK = 'cabinet_only';
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new Error('network timeout');
    }));
    const req = createRequest(
      '/en-EN/features?utm_campaign=hold&redirect=https%3A%2F%2Fevil.example%2Fcb',
      undefined,
      'https://cyber-vpn.net',
    );
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe(
      'https://my.cyber-vpn.net/en-EN/dashboard?utm_campaign=hold',
    );
  });

  it('does not apply cabinet-only redirects to untrusted forwarded hosts', async () => {
    mockCustomerSiteRuntime();
    const req = createProxiedRequest('/ru-RU/pricing?utm_source=launch', 'evil.example');
    const res = await proxy(req);

    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });

  it('redirects maintenance runtime traffic to the public status route', async () => {
    mockCustomerSiteRuntime({ customer_site_mode: 'maintenance' });
    const req = createRequest(
      '/ru-RU/pricing?utm_source=ops&redirect=https%3A%2F%2Fevil.example%2Fcb',
      undefined,
      'https://cyber-vpn.net',
    );
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe(
      'https://cyber-vpn.net/ru-RU/status?utm_source=ops&mode=maintenance&source=site_mode',
    );
  });

  it('redirects marketing routes away from cabinet host', async () => {
    const req = createRequest('/ru-RU/pricing', undefined, 'https://my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://cyber-vpn.net/ru-RU/pricing');
  });

  it('redirects production proxied cabinet marketing routes to public origin without leaking the app port', async () => {
    const req = createProxiedRequest('/ru-RU/pricing?currency=RUB', 'my.cyber-vpn.net');
    const res = await proxy(req);

    expect(res.status).toBe(307);
    expect(res.headers.get('location')).toBe('https://cyber-vpn.net/ru-RU/pricing?currency=RUB');
  });

  it('does not reflect an untrusted forwarded host into redirect locations', async () => {
    const req = createProxiedRequest('/ru-RU/dashboard', 'evil.example');
    const res = await proxy(req);

    expect(res.status).toBe(200);
    expect(res.headers.get('location')).toBeNull();
  });
});

// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET } from './route';

const ORIGINAL_API_URL = process.env.API_URL;
const ORIGINAL_NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;
const ORIGINAL_NEXT_PUBLIC_APP_ENV = process.env.NEXT_PUBLIC_APP_ENV;

describe('partner attribution public route', () => {
  beforeEach(() => {
    process.env.API_URL = 'https://api.cyber-vpn.net';
    delete process.env.NEXT_PUBLIC_API_URL;
  });

  afterEach(() => {
    process.env.API_URL = ORIGINAL_API_URL;
    process.env.NEXT_PUBLIC_API_URL = ORIGINAL_NEXT_PUBLIC_API_URL;
    process.env.NEXT_PUBLIC_APP_ENV = ORIGINAL_NEXT_PUBLIC_APP_ENV;
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('returns an explicit no-store error for invalid public attribution tokens', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: 'PARTNER_CODE_NOT_FOUND',
          },
        }),
        {
          headers: {
            'Content-Type': 'application/json',
          },
          status: 404,
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const request = new NextRequest('http://localhost:3000/p/invalid-smoke-token?utm_source=smoke', {
      headers: {
        host: 'localhost:3000',
        'x-forwarded-host': 'cyber-vpn.net',
      },
    });

    const response = await GET(request, {
      params: Promise.resolve({ publicToken: 'invalid-smoke-token' }),
    });

    expect(response.status).toBe(404);
    expect(response.headers.get('location')).toBeNull();
    expect(response.headers.get('set-cookie')).toBeNull();
    expect(response.headers.get('cache-control')).toBe('no-store');
    await expect(response.json()).resolves.toMatchObject({
      detail: {
        code: 'PARTNER_CODE_NOT_FOUND',
      },
    });
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.cyber-vpn.net/api/v1/partner-attribution/capture',
      expect.objectContaining({
        method: 'POST',
      }),
    );
  });

  it('redirects to the backend-provided URL after a successful capture', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          redirect_url: 'https://cyber-vpn.net/ru-RU/register?pat=transfer-token',
        }),
        {
          headers: {
            'Content-Type': 'application/json',
          },
          status: 200,
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const request = new NextRequest('https://cyber-vpn.net/p/public-token');
    const response = await GET(request, {
      params: Promise.resolve({ publicToken: 'public-token' }),
    });

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe(
      'https://cyber-vpn.net/ru-RU/register?pat=transfer-token',
    );
    expect(response.headers.get('set-cookie')).toContain('cv_partner_browser=');
  });

  it('strips spoofed forwarding headers and sends a trusted host plus idempotency key', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          redirect_url: 'https://my.cyber-vpn.net/ru-RU/register?pat=transfer-token',
        }),
        {
          headers: {
            'Content-Type': 'application/json',
          },
          status: 200,
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const request = new NextRequest(
      'https://cyber-vpn.net/p/public-token?to=/account&pat=attacker-token&utm_source=share',
      {
        headers: {
          host: 'cyber-vpn.net',
          'x-auth-realm': 'partner',
          'x-forwarded-host': 'evil.example',
        },
      },
    );
    const response = await GET(request, {
      params: Promise.resolve({ publicToken: 'public-token' }),
    });

    expect(response.status).toBe(307);
    const [, init] = fetchMock.mock.calls[0];
    expect(init.headers['X-Forwarded-Host']).toBe('cyber-vpn.net');
    expect(init.headers['X-Auth-Realm']).toBeUndefined();
    expect(init.headers['Idempotency-Key']).toMatch(/^[a-f0-9]{64}$/);
    const captureBody = JSON.parse(String(init.body));
    expect(captureBody.destination_path).toBeNull();
    expect(captureBody.source_path).toContain('/p/public-token?');
    expect(captureBody.source_path).toContain('utm_source=share');
    expect(captureBody.source_path).not.toContain('pat=');
  });

  it('preserves backend capture rate limits with Retry-After', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: {
            code: 'PARTNER_ATTRIBUTION_RATE_LIMITED',
            message: 'Too many attempts.',
          },
        }),
        {
          headers: {
            'Content-Type': 'application/json',
            'Retry-After': '42',
          },
          status: 429,
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const request = new NextRequest('https://cyber-vpn.net/p/public-token');
    const response = await GET(request, {
      params: Promise.resolve({ publicToken: 'public-token' }),
    });

    expect(response.status).toBe(429);
    expect(response.headers.get('Retry-After')).toBe('42');
    expect(response.headers.get('location')).toBeNull();
    expect(response.headers.get('set-cookie')).toBeNull();
    await expect(response.json()).resolves.toMatchObject({
      detail: {
        code: 'PARTNER_ATTRIBUTION_RATE_LIMITED',
      },
    });
  });

  it('falls back to the canonical registration URL for untrusted backend redirects', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          redirect_url: 'https://evil.example/ru-RU/register?pat=transfer-token',
        }),
        {
          headers: {
            'Content-Type': 'application/json',
          },
          status: 200,
        },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    const request = new NextRequest('https://cyber-vpn.net/p/public-token');
    const response = await GET(request, {
      params: Promise.resolve({ publicToken: 'public-token' }),
    });

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://cyber-vpn.net/ru-RU/register');
  });

  it('rejects unknown production capture hosts before calling the backend', async () => {
    process.env.NEXT_PUBLIC_APP_ENV = 'production';
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const request = new NextRequest('https://unknown.example/p/public-token', {
      headers: {
        host: 'unknown.example',
        'x-forwarded-host': 'cyber-vpn.net',
      },
    });
    const response = await GET(request, {
      params: Promise.resolve({ publicToken: 'public-token' }),
    });

    expect(response.status).toBe(421);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('treats production Node runtime as secure even when the public app environment is staging', async () => {
    vi.stubEnv('NODE_ENV', 'production');
    process.env.NEXT_PUBLIC_APP_ENV = 'staging';
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const rejectedRequest = new NextRequest('https://localhost/p/public-token', {
      headers: {
        host: 'localhost',
      },
    });
    const rejectedResponse = await GET(rejectedRequest, {
      params: Promise.resolve({ publicToken: 'public-token' }),
    });

    expect(rejectedResponse.status).toBe(421);
    expect(fetchMock).not.toHaveBeenCalled();

    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          redirect_url: 'https://cyber-vpn.net/ru-RU/register?pat=transfer-token',
        }),
        {
          headers: {
            'Content-Type': 'application/json',
          },
          status: 200,
        },
      ),
    );
    const acceptedRequest = new NextRequest('https://cyber-vpn.net/p/public-token');
    const acceptedResponse = await GET(acceptedRequest, {
      params: Promise.resolve({ publicToken: 'public-token' }),
    });

    expect(acceptedResponse.status).toBe(307);
    expect(acceptedResponse.headers.get('set-cookie')).toContain('Secure');
  });
});

// @vitest-environment node

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { GET } from './route';

const ORIGINAL_API_URL = process.env.API_URL;
const ORIGINAL_NEXT_PUBLIC_API_URL = process.env.NEXT_PUBLIC_API_URL;

describe('partner attribution public route', () => {
  beforeEach(() => {
    process.env.API_URL = 'https://api.cyber-vpn.net';
    delete process.env.NEXT_PUBLIC_API_URL;
  });

  afterEach(() => {
    process.env.API_URL = ORIGINAL_API_URL;
    process.env.NEXT_PUBLIC_API_URL = ORIGINAL_NEXT_PUBLIC_API_URL;
    vi.unstubAllGlobals();
  });

  it('uses the public site origin for invalid-token fallback redirects', async () => {
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

    expect(response.status).toBe(307);
    expect(response.headers.get('location')).toBe('https://cyber-vpn.net/ru-RU/register');
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
  });
});

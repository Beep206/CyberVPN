// @vitest-environment node

import { NextRequest } from 'next/server';
import { describe, expect, it } from 'vitest';
import {
  buildCanonicalRedirectUrl,
  buildExternalRequestRedirectUrl,
} from '../redirect-url';

function createRequest(url: string, headers?: HeadersInit): NextRequest {
  return new NextRequest(url, { headers });
}

describe('redirect url helpers', () => {
  it('builds canonical redirects without inheriting runtime ports', () => {
    const request = createRequest('http://cybervpn-frontend:3000/ru-RU/dashboard?tab=ops');

    const url = buildCanonicalRedirectUrl(request, 'https://my.cyber-vpn.net');

    expect(url.toString()).toBe('https://my.cyber-vpn.net/ru-RU/dashboard?tab=ops');
  });

  it('uses allowed forwarded host while dropping non-local ports', () => {
    const request = createRequest('http://cybervpn-frontend:3000/ru-RU?from=proxy', {
      'x-forwarded-host': 'my.cyber-vpn.net:3000',
      'x-forwarded-proto': 'https',
      host: 'cybervpn-frontend:3000',
    });

    const url = buildExternalRequestRedirectUrl(request, 'https://my.cyber-vpn.net', {
      pathname: '/ru-RU/dashboard',
      allowedHosts: new Set(['my.cyber-vpn.net']),
    });

    expect(url.toString()).toBe('https://my.cyber-vpn.net/ru-RU/dashboard?from=proxy');
  });

  it('preserves local development ports only for local hosts', () => {
    const request = createRequest('http://localhost:3000/ru-RU?from=dev', {
      host: 'localhost:3000',
    });

    const url = buildExternalRequestRedirectUrl(request, 'https://my.cyber-vpn.net', {
      pathname: '/ru-RU/dashboard',
      allowedHosts: new Set(['localhost']),
    });

    expect(url.toString()).toBe('http://localhost:3000/ru-RU/dashboard?from=dev');
  });

  it('falls back instead of reflecting an untrusted forwarded host', () => {
    const request = createRequest('http://cybervpn-frontend:3000/ru-RU?from=proxy', {
      'x-forwarded-host': 'evil.example',
      host: 'cybervpn-frontend:3000',
    });

    const url = buildExternalRequestRedirectUrl(request, 'https://my.cyber-vpn.net', {
      pathname: '/ru-RU/dashboard',
      allowedHosts: new Set(['my.cyber-vpn.net']),
    });

    expect(url.toString()).toBe('https://my.cyber-vpn.net/ru-RU/dashboard?from=proxy');
  });

  it('rejects external-looking redirect pathnames', () => {
    const request = createRequest('http://cybervpn-frontend:3000/ru-RU');

    expect(() => {
      buildCanonicalRedirectUrl(request, 'https://my.cyber-vpn.net', {
        pathname: '//evil.example/login',
      });
    }).toThrow('Redirect pathname must be an internal absolute path');
  });
});

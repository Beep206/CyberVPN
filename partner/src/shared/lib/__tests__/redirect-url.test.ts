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
    const request = createRequest('http://cybervpn-partner:3002/en-EN?tab=ops');

    const url = buildCanonicalRedirectUrl(request, 'https://partner.cyber-vpn.net');

    expect(url.toString()).toBe('https://partner.cyber-vpn.net/en-EN?tab=ops');
  });

  it('uses allowed forwarded host while dropping non-local ports', () => {
    const request = createRequest('http://cybervpn-partner:3002/en-EN?from=proxy', {
      'x-forwarded-host': 'partner.cyber-vpn.net:3002',
      'x-forwarded-proto': 'https',
      host: 'cybervpn-partner:3002',
    });

    const url = buildExternalRequestRedirectUrl(request, 'https://partner.cyber-vpn.net', {
      pathname: '/en-EN/login',
      allowedHosts: new Set(['partner.cyber-vpn.net']),
    });

    expect(url.toString()).toBe('https://partner.cyber-vpn.net/en-EN/login?from=proxy');
  });

  it('preserves local development ports only for local hosts', () => {
    const request = createRequest('http://portal.localhost:3002/en-EN?from=dev', {
      host: 'portal.localhost:3002',
    });

    const url = buildExternalRequestRedirectUrl(request, 'https://partner.cyber-vpn.net', {
      pathname: '/en-EN/login',
      allowedHosts: new Set(['portal.localhost']),
    });

    expect(url.toString()).toBe('http://portal.localhost:3002/en-EN/login?from=dev');
  });

  it('falls back instead of reflecting an untrusted forwarded host', () => {
    const request = createRequest('http://cybervpn-partner:3002/en-EN?from=proxy', {
      'x-forwarded-host': 'evil.example',
      host: 'cybervpn-partner:3002',
    });

    const url = buildExternalRequestRedirectUrl(request, 'https://partner.cyber-vpn.net', {
      pathname: '/en-EN/login',
      allowedHosts: new Set(['partner.cyber-vpn.net']),
    });

    expect(url.toString()).toBe('https://partner.cyber-vpn.net/en-EN/login?from=proxy');
  });

  it('rejects external-looking redirect pathnames', () => {
    const request = createRequest('http://cybervpn-partner:3002/en-EN');

    expect(() => {
      buildCanonicalRedirectUrl(request, 'https://partner.cyber-vpn.net', {
        pathname: '//evil.example/login',
      });
    }).toThrow('Redirect pathname must be an internal absolute path');
  });
});

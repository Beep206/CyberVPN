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
    const request = createRequest('http://cybervpn-admin:3001/en-EN?tab=ops');

    const url = buildCanonicalRedirectUrl(request, 'https://admin.cyber-vpn.net');

    expect(url.toString()).toBe('https://admin.cyber-vpn.net/en-EN?tab=ops');
  });

  it('uses allowed forwarded host while dropping non-local ports', () => {
    const request = createRequest('http://cybervpn-admin:3001/en-EN?from=proxy', {
      'x-forwarded-host': 'admin.cyber-vpn.net:3001',
      'x-forwarded-proto': 'https',
      host: 'cybervpn-admin:3001',
    });

    const url = buildExternalRequestRedirectUrl(request, 'https://admin.cyber-vpn.net', {
      pathname: '/en-EN/login',
      allowedHosts: new Set(['admin.cyber-vpn.net']),
    });

    expect(url.toString()).toBe('https://admin.cyber-vpn.net/en-EN/login?from=proxy');
  });

  it('preserves local development ports only for local hosts', () => {
    const request = createRequest('http://localhost:3001/en-EN?from=dev', {
      host: 'localhost:3001',
    });

    const url = buildExternalRequestRedirectUrl(request, 'https://admin.cyber-vpn.net', {
      pathname: '/en-EN/login',
      allowedHosts: new Set(['localhost']),
    });

    expect(url.toString()).toBe('http://localhost:3001/en-EN/login?from=dev');
  });

  it('falls back instead of reflecting an untrusted forwarded host', () => {
    const request = createRequest('http://cybervpn-admin:3001/en-EN?from=proxy', {
      'x-forwarded-host': 'evil.example',
      host: 'cybervpn-admin:3001',
    });

    const url = buildExternalRequestRedirectUrl(request, 'https://admin.cyber-vpn.net', {
      pathname: '/en-EN/login',
      allowedHosts: new Set(['admin.cyber-vpn.net']),
    });

    expect(url.toString()).toBe('https://admin.cyber-vpn.net/en-EN/login?from=proxy');
  });

  it('rejects external-looking redirect pathnames', () => {
    const request = createRequest('http://cybervpn-admin:3001/en-EN');

    expect(() => {
      buildCanonicalRedirectUrl(request, 'https://admin.cyber-vpn.net', {
        pathname: '//evil.example/login',
      });
    }).toThrow('Redirect pathname must be an internal absolute path');
  });
});

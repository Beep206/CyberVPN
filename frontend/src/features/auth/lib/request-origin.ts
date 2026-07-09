import type { NextRequest } from 'next/server';

type ParsedAuthority = {
  hostname: string;
  port: string;
};

const CUSTOMER_AUTH_CANONICAL_ORIGIN = 'https://my.cyber-vpn.net';
const CUSTOMER_AUTH_PUBLIC_HOSTS = new Set([
  'cyber-vpn.net',
  'www.cyber-vpn.net',
  'my.cyber-vpn.net',
]);
const CUSTOMER_AUTH_LOCAL_HOSTS = new Set([
  'localhost',
  '127.0.0.1',
  '::1',
  'testserver',
]);

function readFirstHeaderValue(value: string | null): string | null {
  const firstValue = value?.split(',')[0]?.trim();
  return firstValue || null;
}

function normalizeHostname(hostname: string): string {
  return hostname.toLowerCase().replace(/^\[(.*)\]$/, '$1').replace(/\.$/, '');
}

function parseAuthority(value: string | null): ParsedAuthority | null {
  const authority = readFirstHeaderValue(value);
  if (!authority || /[\r\n]/.test(authority)) {
    return null;
  }

  if (authority.includes('/') || authority.includes('\\') || authority.includes('@')) {
    return null;
  }

  try {
    const parsed = new URL(`http://${authority}`);
    if (parsed.username || parsed.password || parsed.pathname !== '/') {
      return null;
    }

    return {
      hostname: normalizeHostname(parsed.hostname),
      port: parsed.port,
    };
  } catch {
    return null;
  }
}

function isLocalAuthHostname(hostname: string): boolean {
  return CUSTOMER_AUTH_LOCAL_HOSTS.has(hostname) || hostname.endsWith('.localhost');
}

function isAllowedAuthHostname(hostname: string): boolean {
  return CUSTOMER_AUTH_PUBLIC_HOSTS.has(hostname) || isLocalAuthHostname(hostname);
}

function hostWithOptionalPort(authority: ParsedAuthority): string {
  const hostname = authority.hostname.includes(':') && !authority.hostname.startsWith('[')
    ? `[${authority.hostname}]`
    : authority.hostname;

  return isLocalAuthHostname(authority.hostname) && authority.port
    ? `${hostname}:${authority.port}`
    : hostname;
}

function readAllowedAuthority(request: NextRequest): ParsedAuthority | null {
  const candidates = [
    request.headers.get('host'),
    request.nextUrl.host,
  ];

  for (const candidate of candidates) {
    const authority = parseAuthority(candidate);
    if (authority && isAllowedAuthHostname(authority.hostname)) {
      return authority;
    }
  }

  return null;
}

function protocolForAuthority(request: NextRequest, authority: ParsedAuthority): string {
  if (!isLocalAuthHostname(authority.hostname)) {
    return 'https';
  }

  return request.nextUrl.protocol === 'https:' ? 'https' : 'http';
}

export function getRequestOrigin(request: NextRequest): string {
  const authority = readAllowedAuthority(request);
  if (!authority) {
    return CUSTOMER_AUTH_CANONICAL_ORIGIN;
  }

  return `${protocolForAuthority(request, authority)}://${hostWithOptionalPort(authority)}`;
}

export function getTrustedForwardedHost(request: NextRequest): string {
  return new URL(getRequestOrigin(request)).host;
}

export function getTrustedForwardedProto(request: NextRequest): string {
  return new URL(getRequestOrigin(request)).protocol.replace(/:$/, '');
}

export function buildAppUrl(request: NextRequest, pathname: string): URL {
  return new URL(pathname, getRequestOrigin(request));
}

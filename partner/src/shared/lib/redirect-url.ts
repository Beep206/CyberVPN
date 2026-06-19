import type { NextRequest } from 'next/server';

type RedirectUrlOptions = {
  pathname?: string;
  preserveSearch?: boolean;
};

type ExternalRedirectUrlOptions = RedirectUrlOptions & {
  allowedHosts?: ReadonlySet<string>;
};

type ParsedAuthority = {
  hostname: string;
  port: string;
};

const LOCAL_HOSTNAMES = new Set(['localhost', '127.0.0.1', '::1']);

function firstHeaderValue(value: string | null | undefined): string | null {
  const first = value?.split(',')[0]?.trim();
  return first || null;
}

function hasUnsafeHeaderCharacters(value: string): boolean {
  return /[\r\n]/.test(value);
}

function normalizeRedirectPathname(pathname: string): string {
  if (!pathname.startsWith('/') || pathname.startsWith('//')) {
    throw new Error('Redirect pathname must be an internal absolute path');
  }

  return pathname;
}

function parseSafeOrigin(origin: string): URL {
  const parsed = new URL(origin);
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error('Redirect origin must use http or https');
  }
  if (parsed.username || parsed.password) {
    throw new Error('Redirect origin must not include credentials');
  }

  return parsed;
}

function parseForwardedProto(value: string | null | undefined, fallbackProtocol: string): string {
  const proto = firstHeaderValue(value)?.toLowerCase().replace(/:$/, '');
  if (proto === 'http' || proto === 'https') {
    return `${proto}:`;
  }

  return fallbackProtocol;
}

function safeRequestProtocol(request: NextRequest, fallbackProtocol: string): string {
  return request.nextUrl.protocol === 'http:' || request.nextUrl.protocol === 'https:'
    ? request.nextUrl.protocol
    : fallbackProtocol;
}

function parseAuthority(value: string | null | undefined): ParsedAuthority | null {
  const authority = firstHeaderValue(value);
  if (!authority || hasUnsafeHeaderCharacters(authority)) {
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
      hostname: parsed.hostname.toLowerCase().replace(/\.$/, ''),
      port: parsed.port,
    };
  } catch {
    return null;
  }
}

function normalizeAllowedHostname(value: string): string | null {
  const authority = parseAuthority(value);
  if (authority) {
    return authority.hostname;
  }

  try {
    return parseAuthority(new URL(value).host)?.hostname ?? null;
  } catch {
    return null;
  }
}

function isLocalHostname(hostname: string): boolean {
  return LOCAL_HOSTNAMES.has(hostname) || hostname.endsWith('.localhost');
}

function hostWithOptionalPort(hostname: string, port: string): string {
  const formattedHostname = hostname.includes(':') && !hostname.startsWith('[')
    ? `[${hostname}]`
    : hostname;

  return port ? `${formattedHostname}:${port}` : formattedHostname;
}

function buildUrl(request: NextRequest, origin: string, options: RedirectUrlOptions = {}): URL {
  const pathname = normalizeRedirectPathname(options.pathname ?? request.nextUrl.pathname);
  const target = new URL(pathname, origin);
  if (options.preserveSearch ?? true) {
    target.search = request.nextUrl.search;
  }

  return target;
}

export function buildCanonicalRedirectUrl(
  request: NextRequest,
  canonicalOrigin: string,
  options: RedirectUrlOptions = {},
): URL {
  const origin = parseSafeOrigin(canonicalOrigin).origin;
  return buildUrl(request, origin, options);
}

export function buildExternalRequestRedirectUrl(
  request: NextRequest,
  fallbackOrigin: string,
  options: ExternalRedirectUrlOptions = {},
): URL {
  const fallback = parseSafeOrigin(fallbackOrigin);
  const allowedHostnames = new Set<string>([fallback.hostname.toLowerCase()]);
  for (const host of options.allowedHosts ?? []) {
    const normalized = normalizeAllowedHostname(host);
    if (normalized) {
      allowedHostnames.add(normalized);
    }
  }

  const authority =
    parseAuthority(request.headers.get('x-forwarded-host'))
    ?? parseAuthority(request.headers.get('host'))
    ?? parseAuthority(request.nextUrl.host);
  const proto = parseForwardedProto(
    request.headers.get('x-forwarded-proto'),
    authority && isLocalHostname(authority.hostname)
      ? safeRequestProtocol(request, fallback.protocol)
      : fallback.protocol,
  );

  if (!authority || !allowedHostnames.has(authority.hostname)) {
    return buildUrl(request, fallback.origin, options);
  }

  const origin = `${proto}//${hostWithOptionalPort(
    authority.hostname,
    isLocalHostname(authority.hostname) ? authority.port : '',
  )}`;

  return buildUrl(request, origin, options);
}

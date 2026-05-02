import type { ErrorEvent } from '@sentry/core';

const SENSITIVE_HEADER_NAMES = new Set([
  'authorization',
  'cookie',
  'set-cookie',
  'x-observability-secret',
]);

function sanitizeUrl(url: unknown): unknown {
  if (typeof url !== 'string' || !url) {
    return url;
  }

  try {
    const parsed = new URL(url, 'http://localhost');
    parsed.search = '';
    parsed.hash = '';

    if (url.startsWith('/')) {
      return `${parsed.pathname}${parsed.search}${parsed.hash}` || '/';
    }

    return parsed.toString();
  } catch {
    return url.split('?')[0]?.split('#')[0] || url;
  }
}

export function scrubSentryEvent(event: ErrorEvent): ErrorEvent {
  if (event.user) {
    delete event.user.email;
    delete event.user.ip_address;
    delete event.user.username;
  }

  const request = event.request;
  if (request) {
    request.url = sanitizeUrl(request.url) as string | undefined;

    if (request.headers) {
      Object.keys(request.headers).forEach((headerName) => {
        if (SENSITIVE_HEADER_NAMES.has(headerName.toLowerCase())) {
          request.headers![headerName] = '[Filtered]';
        }
      });
    }

    if ('cookies' in request) {
      delete request.cookies;
    }

    if ('data' in request) {
      request.data = '[Filtered]';
    }
  }

  return event;
}

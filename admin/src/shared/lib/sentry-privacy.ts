import type { ErrorEvent } from '@sentry/core';

const SENSITIVE_HEADER_NAMES = new Set([
  'authorization',
  'cookie',
  'set-cookie',
  'x-observability-secret',
  'x-telegram-bot-api-secret-token',
]);

const SENSITIVE_FIELD_MARKERS = [
  'token',
  'secret',
  'password',
  'cookie',
  'authorization',
  'jwt',
  'payload',
  'config',
  'certificate',
  'private_key',
  'wireguard',
  'vless',
  'vmess',
  'remnawave',
  'openbao',
  'opentofu',
  'nats',
  'payment',
  'oauth',
  'totp',
  'initdata',
  'init_data',
  'checkout',
  'invoice',
] as const;

const SENSITIVE_STRING_PATTERNS = [
  /\b(?:vless|vmess|trojan|wireguard|ss):\/\//i,
  /(?:access[_-]?token|refresh[_-]?token|id[_-]?token|auth[_-]?code|otp|totp|secret|password|telegram[_-]?init[_-]?data|initdata|tgWebAppData)=/i,
  /\/api\/v1\/(?:vpn|xray|provisioning|subscriptions?)\/(?:config|credentials|subscription)/i,
] as const;

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

function shouldFilterKey(key: string): boolean {
  const loweredKey = key.toLowerCase();
  return SENSITIVE_FIELD_MARKERS.some((marker) => loweredKey.includes(marker));
}

function shouldFilterString(value: string): boolean {
  return SENSITIVE_STRING_PATTERNS.some((pattern) => pattern.test(value));
}

function scrubSensitiveValue(value: unknown): unknown {
  if (typeof value === 'string') {
    return shouldFilterString(value) ? '[Filtered]' : value;
  }

  if (Array.isArray(value)) {
    return value.map((item) => scrubSensitiveValue(item));
  }

  if (value && typeof value === 'object') {
    scrubSensitiveMapping(value as Record<string, unknown>);
  }

  return value;
}

function scrubSensitiveMapping(payload: Record<string, unknown>): void {
  Object.keys(payload).forEach((key) => {
    if (shouldFilterKey(key)) {
      payload[key] = '[Filtered]';
      return;
    }

    payload[key] = scrubSensitiveValue(payload[key]);
  });
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

  if (event.extra) {
    scrubSensitiveMapping(event.extra as Record<string, unknown>);
  }

  if (event.contexts) {
    scrubSensitiveMapping(event.contexts as Record<string, unknown>);
  }

  return event;
}

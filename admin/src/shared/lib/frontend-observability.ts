'use client';

import * as Sentry from '@sentry/nextjs';
import { getLocaleFromPathname } from '@/shared/lib/ai-seo-analytics';
import { getMobileTelemetryContext } from '@/shared/lib/mobile-device-bucket';

export type FrontendRuntimeEventName =
  | 'route_load'
  | 'api_call'
  | 'route_guard_block'
  | 'form_validation_error'
  | 'submit_attempt'
  | 'submit_failure'
  | 'unhandled_error'
  | 'render_error';

export type FrontendSurface = 'partner_portal' | 'admin_portal';

export type FrontendRuntimePayload = {
  event: FrontendRuntimeEventName;
  surface: FrontendSurface;
  connectionType: string;
  deviceBucket: string;
  locale?: string;
  path: string;
  reducedMotion: string;
  routeGroup: string;
  saveData: string;
  viewportBucket: string;
  blockedReason?: string;
  durationMs?: number;
  endpointTemplate?: string;
  errorCode?: string;
  formName?: string;
  lane?: string;
  method?: string;
  releaseRing?: string;
  requestId?: string;
  result?: string;
  workspaceStatus?: string;
};

const FRONTEND_RUNTIME_ENDPOINT = '/api/analytics/frontend-runtime';
const FRONTEND_ERROR_HANDLER_KEY = '__CYBERVPN_FRONTEND_ERROR_OBSERVABILITY_INSTALLED__';
const UUID_SEGMENT_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const NUMERIC_SEGMENT_RE = /^\d+$/;
const LONG_TOKEN_SEGMENT_RE = /^(?:[a-z0-9_-]{20,}|[0-9a-f]{16,})$/i;

declare global {
  interface Window {
    __CYBERVPN_FRONTEND_ERROR_OBSERVABILITY_INSTALLED__?: boolean;
  }
}

function normalizePath(path: string): string {
  return path.trim() || '/';
}

export function sanitizeFrontendObservabilityToken(value: string | null | undefined): string {
  if (!value) {
    return 'unknown';
  }

  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._/-]+/g, '_')
    .slice(0, 80);

  return normalized || 'unknown';
}

export function normalizeFrontendApiEndpointTemplate(rawUrl: string): string {
  if (!rawUrl) {
    return '/';
  }

  const parsed = new URL(rawUrl, 'http://localhost');
  const segments = parsed.pathname
    .split('/')
    .filter(Boolean)
    .map((segment) => {
      if (
        UUID_SEGMENT_RE.test(segment)
        || NUMERIC_SEGMENT_RE.test(segment)
        || LONG_TOKEN_SEGMENT_RE.test(segment)
      ) {
        return ':id';
      }

      return sanitizeFrontendObservabilityToken(segment);
    });

  return `/${segments.join('/')}`.slice(0, 160) || '/';
}

function buildFrontendRuntimePayload(
  event: FrontendRuntimeEventName,
  surface: FrontendSurface,
  overrides: Partial<FrontendRuntimePayload> = {},
): FrontendRuntimePayload | null {
  if (typeof window === 'undefined') {
    return null;
  }

  const pathname = normalizePath(overrides.path ?? window.location.pathname);
  const telemetry = getMobileTelemetryContext(pathname);
  const locale = overrides.locale ?? getLocaleFromPathname(pathname);
  const routeGroup = overrides.routeGroup ?? telemetry.routeGroup;

  return {
    ...overrides,
    connectionType: telemetry.connectionType,
    deviceBucket: telemetry.deviceBucket,
    event,
    locale,
    path: pathname,
    reducedMotion: telemetry.reducedMotion,
    routeGroup,
    saveData: telemetry.saveData,
    surface,
    viewportBucket: telemetry.viewportBucket,
  };
}

function sendFrontendRuntimePayload(payload: FrontendRuntimePayload): void {
  const body = JSON.stringify(payload);

  if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
    navigator.sendBeacon(FRONTEND_RUNTIME_ENDPOINT, new Blob([body], { type: 'application/json' }));
    return;
  }

  void fetch(FRONTEND_RUNTIME_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body,
    credentials: 'same-origin',
    keepalive: true,
  });
}

export function reportFrontendRuntimeEvent(
  event: FrontendRuntimeEventName,
  surface: FrontendSurface,
  overrides: Partial<FrontendRuntimePayload> = {},
): void {
  const payload = buildFrontendRuntimePayload(event, surface, overrides);

  if (!payload) {
    return;
  }

  Sentry.addBreadcrumb({
    category: 'frontend.runtime',
    level: event === 'unhandled_error' || event === 'render_error' ? 'error' : 'info',
    message: event,
    data: {
      blockedReason: payload.blockedReason,
      endpointTemplate: payload.endpointTemplate,
      errorCode: payload.errorCode,
      formName: payload.formName,
      method: payload.method,
      path: payload.path,
      releaseRing: payload.releaseRing,
      requestId: payload.requestId,
      result: payload.result,
      routeGroup: payload.routeGroup,
      surface: payload.surface,
      workspaceStatus: payload.workspaceStatus,
    },
  });

  sendFrontendRuntimePayload(payload);
}

export function reportFrontendRouteLoad(
  surface: FrontendSurface,
  pathname: string,
  durationMs: number,
): void {
  reportFrontendRuntimeEvent('route_load', surface, {
    durationMs,
    path: pathname,
    result: 'success',
  });
}

export function reportFrontendApiCall(
  surface: FrontendSurface,
  input: {
    durationMs: number;
    endpointTemplate: string;
    errorCode?: string;
    method: string;
    path?: string;
    requestId?: string;
    result: 'success' | 'failure';
  },
): void {
  reportFrontendRuntimeEvent('api_call', surface, {
    durationMs: input.durationMs,
    endpointTemplate: normalizeFrontendApiEndpointTemplate(input.endpointTemplate),
    errorCode: input.errorCode ? sanitizeFrontendObservabilityToken(input.errorCode) : undefined,
    method: sanitizeFrontendObservabilityToken(input.method),
    path: input.path,
    requestId: input.requestId,
    result: input.result,
  });
}

export function reportFrontendFormValidationError(
  surface: FrontendSurface,
  input: {
    errorCode: string;
    formName: string;
    path?: string;
  },
): void {
  reportFrontendRuntimeEvent('form_validation_error', surface, {
    errorCode: sanitizeFrontendObservabilityToken(input.errorCode),
    formName: sanitizeFrontendObservabilityToken(input.formName),
    path: input.path,
    result: 'failure',
  });
}

export function reportFrontendSubmitAttempt(
  surface: FrontendSurface,
  input: {
    formName: string;
    path?: string;
    result?: string;
  },
): void {
  reportFrontendRuntimeEvent('submit_attempt', surface, {
    formName: sanitizeFrontendObservabilityToken(input.formName),
    path: input.path,
    result: sanitizeFrontendObservabilityToken(input.result ?? 'attempted'),
  });
}

export function reportFrontendSubmitFailure(
  surface: FrontendSurface,
  input: {
    errorCode: string;
    formName: string;
    path?: string;
    requestId?: string;
  },
): void {
  reportFrontendRuntimeEvent('submit_failure', surface, {
    errorCode: sanitizeFrontendObservabilityToken(input.errorCode),
    formName: sanitizeFrontendObservabilityToken(input.formName),
    path: input.path,
    requestId: input.requestId,
    result: 'failure',
  });
}

export function reportFrontendUnhandledError(
  surface: FrontendSurface,
  input: {
    errorCode: string;
    path?: string;
  },
): void {
  reportFrontendRuntimeEvent('unhandled_error', surface, {
    errorCode: sanitizeFrontendObservabilityToken(input.errorCode),
    path: input.path,
    result: 'failure',
  });
}

export function reportFrontendRenderError(
  surface: FrontendSurface,
  input: {
    errorCode: string;
    path?: string;
  },
): void {
  reportFrontendRuntimeEvent('render_error', surface, {
    errorCode: sanitizeFrontendObservabilityToken(input.errorCode),
    path: input.path,
    result: 'failure',
  });
}

function deriveErrorCode(value: unknown): string {
  if (value instanceof Error) {
    return value.name || 'error';
  }

  if (typeof value === 'string') {
    return value;
  }

  return 'unknown';
}

export function installFrontendGlobalErrorReporting(surface: FrontendSurface): void {
  if (typeof window === 'undefined' || window[FRONTEND_ERROR_HANDLER_KEY]) {
    return;
  }

  window[FRONTEND_ERROR_HANDLER_KEY] = true;

  window.addEventListener('error', (event) => {
    reportFrontendUnhandledError(surface, {
      errorCode: deriveErrorCode(event.error ?? event.message),
      path: window.location.pathname,
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    reportFrontendUnhandledError(surface, {
      errorCode: deriveErrorCode(event.reason),
      path: window.location.pathname,
    });
  });
}

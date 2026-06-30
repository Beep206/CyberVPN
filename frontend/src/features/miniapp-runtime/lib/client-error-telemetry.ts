'use client';

type MiniAppClientErrorInput = {
  eventType: string;
  errorName?: string;
  errorMessage?: string;
  chunk?: string | null;
};

const MINIAPP_CLIENT_ERROR_ENDPOINT = '/api/v1/client-errors/miniapp';

const SENSITIVE_PATTERNS = [
  /\b(vless|vmess|trojan|ss):\/\/[^\s"']+/gi,
  /(tgWebAppData|initData|init_data|telegram_init_data|telegramInitData|access_token|refresh_token|customer_access_token)=\S+/gi,
  /\bquery_id=[^&\s]+&user=[^&\s]+&auth_date=\d+&hash=[A-Za-z0-9_-]+/gi,
  /\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{16,}\b/g,
];

function sanitize(value: unknown, fallback = '', maxLength = 500): string {
  let text = typeof value === 'string' ? value : fallback;
  text = text.trim().slice(0, maxLength);
  for (const pattern of SENSITIVE_PATTERNS) {
    text = text.replace(pattern, '[filtered]');
  }
  return text || fallback;
}

function isMiniAppPath(): boolean {
  return typeof window !== 'undefined' && /\/miniapp(?:\/|$)/.test(window.location.pathname);
}

function postMiniAppClientError(payload: Record<string, unknown>): void {
  const body = JSON.stringify(payload);
  if (navigator.sendBeacon) {
    const blob = new Blob([body], { type: 'application/json' });
    if (navigator.sendBeacon(MINIAPP_CLIENT_ERROR_ENDPOINT, blob)) {
      return;
    }
  }

  void fetch(MINIAPP_CLIENT_ERROR_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    keepalive: true,
    body,
  }).catch(() => undefined);
}

export function reportMiniAppClientError(input: MiniAppClientErrorInput): void {
  if (!isMiniAppPath()) {
    return;
  }

  const telegramWebApp = window.Telegram?.WebApp;
  postMiniAppClientError({
    surface: 'miniapp',
    route: sanitize(window.location.pathname, '/', 256),
    telegram_platform: sanitize(telegramWebApp?.platform, 'unknown', 40),
    telegram_version: sanitize(telegramWebApp?.version, 'unknown', 40),
    webapp_version: sanitize(telegramWebApp?.version, 'unknown', 40),
    error_name: sanitize(input.errorName, 'Error', 80),
    error_message: sanitize(input.errorMessage, '', 500),
    event_type: sanitize(input.eventType, 'miniapp_webview_js_error', 80),
    chunk: sanitize(input.chunk, 'none', 160),
    release: sanitize(process.env.NEXT_PUBLIC_SENTRY_RELEASE, 'unknown', 120),
    git_sha: sanitize(process.env.NEXT_PUBLIC_GIT_SHA, 'unknown', 80),
  });
}

export function installMiniAppClientErrorListeners(): () => void {
  if (typeof window === 'undefined') {
    return () => undefined;
  }

  const onError = (event: ErrorEvent) => {
    reportMiniAppClientError({
      eventType: 'miniapp_window_error',
      errorName: event.error instanceof Error ? event.error.name : 'Error',
      errorMessage: event.error instanceof Error ? event.error.message : event.message,
      chunk: event.filename,
    });
  };
  const onUnhandledRejection = (event: PromiseRejectionEvent) => {
    const reason = event.reason;
    reportMiniAppClientError({
      eventType: 'miniapp_unhandled_rejection',
      errorName: reason instanceof Error ? reason.name : 'UnhandledRejection',
      errorMessage: reason instanceof Error ? reason.message : String(reason ?? ''),
      chunk: null,
    });
  };

  window.addEventListener('error', onError);
  window.addEventListener('unhandledrejection', onUnhandledRejection);
  return () => {
    window.removeEventListener('error', onError);
    window.removeEventListener('unhandledrejection', onUnhandledRejection);
  };
}

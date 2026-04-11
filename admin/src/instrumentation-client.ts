import * as Sentry from "@sentry/nextjs";

function initSentry() {
  Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    tracesSampleRate: process.env.NODE_ENV === "production" ? 0.2 : 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
    integrations: [Sentry.browserTracingIntegration(), Sentry.replayIntegration()],
    environment: process.env.NODE_ENV,
  });
}

if ("requestIdleCallback" in window) {
  window.requestIdleCallback(() => initSentry());
} else {
  globalThis.setTimeout(initSentry, 500);
}

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;

import * as Sentry from "@sentry/nextjs";
import { installFrontendGlobalErrorReporting } from '@/shared/lib/frontend-observability';
import { scrubSentryEvent } from '@/shared/lib/sentry-privacy';

const environment =
  process.env.NEXT_PUBLIC_APP_ENV ??
  process.env.APP_ENV ??
  process.env.NODE_ENV ??
  "development";
const release =
  process.env.NEXT_PUBLIC_SENTRY_RELEASE ?? process.env.SENTRY_RELEASE;
const isProduction = environment === "production";

function initSentry() {
  Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
    tracesSampleRate: isProduction ? 0.2 : 1.0,
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    sendDefaultPii: false,
    environment,
    release,
    beforeSend(event) {
      return scrubSentryEvent(event);
    },
  });

  installFrontendGlobalErrorReporting('admin_portal');
}

if ("requestIdleCallback" in window) {
  window.requestIdleCallback(() => initSentry());
} else {
  globalThis.setTimeout(initSentry, 500);
}

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;

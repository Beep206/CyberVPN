import * as Sentry from "@sentry/nextjs";
import { scrubSentryEvent } from "./src/shared/lib/sentry-privacy";

const environment =
  process.env.APP_ENV ??
  process.env.NEXT_PUBLIC_APP_ENV ??
  process.env.NODE_ENV ??
  "development";
const release =
  process.env.SENTRY_RELEASE ?? process.env.NEXT_PUBLIC_SENTRY_RELEASE;
const isProduction = environment === "production";

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: isProduction ? 0.2 : 1.0,
  sendDefaultPii: false,
  environment,
  release,
  beforeSend(event) {
    return scrubSentryEvent(event);
  },
});

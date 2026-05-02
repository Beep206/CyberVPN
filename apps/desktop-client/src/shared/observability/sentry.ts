import * as Sentry from "@sentry/react";
import packageMetadata from "../../../package.json";

type DesktopRendererEnv = Pick<
  ImportMetaEnv,
  | "DEV"
  | "PROD"
  | "MODE"
  | "VITE_SENTRY_DSN"
  | "VITE_SENTRY_ENABLED"
  | "VITE_SENTRY_ENVIRONMENT"
  | "VITE_SENTRY_RELEASE"
  | "VITE_SENTRY_TRACES_SAMPLE_RATE"
  | "VITE_SENTRY_TRACE_PROPAGATION_TARGETS"
>;

export interface ResolvedDesktopSentryConfig {
  enabled: boolean;
  dsn: string;
  environment: string;
  release: string;
  tracesSampleRate: number;
  tracePropagationTargets: string[];
}

export const DEFAULT_DESKTOP_RENDERER_RELEASE = `desktop@${packageMetadata.version}+local`;

function parseBoolean(value: string | undefined): boolean | undefined {
  if (!value) {
    return undefined;
  }

  switch (value.trim().toLowerCase()) {
    case "1":
    case "true":
    case "yes":
    case "on":
      return true;
    case "0":
    case "false":
    case "no":
    case "off":
      return false;
    default:
      return undefined;
  }
}

function parseSampleRate(value: string | undefined): number {
  if (!value) {
    return 0;
  }

  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return 0;
  }

  return Math.min(Math.max(parsed, 0), 1);
}

function parseTracePropagationTargets(value: string | undefined): string[] {
  if (!value) {
    return [];
  }

  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export function resolveDesktopSentryConfig(
  env: DesktopRendererEnv = import.meta.env,
): ResolvedDesktopSentryConfig {
  const dsn = env.VITE_SENTRY_DSN?.trim() ?? "";
  const explicitEnabled = parseBoolean(env.VITE_SENTRY_ENABLED);
  const environment = env.VITE_SENTRY_ENVIRONMENT?.trim() || (env.DEV ? "development" : "production");
  const release = env.VITE_SENTRY_RELEASE?.trim() || DEFAULT_DESKTOP_RENDERER_RELEASE;

  return {
    enabled: explicitEnabled ?? Boolean(dsn),
    dsn,
    environment,
    release,
    tracesSampleRate: parseSampleRate(env.VITE_SENTRY_TRACES_SAMPLE_RATE),
    tracePropagationTargets: parseTracePropagationTargets(
      env.VITE_SENTRY_TRACE_PROPAGATION_TARGETS,
    ),
  };
}

export function initDesktopSentry(
  env: DesktopRendererEnv = import.meta.env,
): ResolvedDesktopSentryConfig {
  const config = resolveDesktopSentryConfig(env);
  if (!config.enabled) {
    return config;
  }

  if (!Sentry.getClient()) {
    Sentry.init({
      dsn: config.dsn,
      environment: config.environment,
      release: config.release,
      integrations: [Sentry.browserTracingIntegration()],
      tracesSampleRate: config.tracesSampleRate,
      tracePropagationTargets: config.tracePropagationTargets,
      sendDefaultPii: false,
      beforeSend(event) {
        if (event.user) {
          delete event.user.email;
          delete event.user.ip_address;
          delete event.user.username;
        }

        return event;
      },
    });
  }

  Sentry.setTags({
    runtime_surface: "desktop-client",
    runtime_layer: "renderer",
    "service.name": "desktop-renderer",
  });

  return config;
}

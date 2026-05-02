import { describe, expect, it } from "vitest";

import {
  DEFAULT_DESKTOP_RENDERER_RELEASE,
  resolveDesktopSentryConfig,
} from "../sentry";

describe("desktop renderer sentry config", () => {
  it("resolves the explicit renderer contract", () => {
    const config = resolveDesktopSentryConfig({
      DEV: false,
      PROD: true,
      MODE: "production",
      VITE_SENTRY_DSN: "https://public@example.com/42",
      VITE_SENTRY_ENABLED: "true",
      VITE_SENTRY_ENVIRONMENT: "staging",
      VITE_SENTRY_RELEASE: "desktop@0.1.5+build.42",
      VITE_SENTRY_TRACES_SAMPLE_RATE: "0.25",
      VITE_SENTRY_TRACE_PROPAGATION_TARGETS:
        "https://api.cybervpn.app, tauri://localhost",
    } as ImportMetaEnv);

    expect(config).toEqual({
      enabled: true,
      dsn: "https://public@example.com/42",
      environment: "staging",
      release: "desktop@0.1.5+build.42",
      tracesSampleRate: 0.25,
      tracePropagationTargets: ["https://api.cybervpn.app", "tauri://localhost"],
    });
  });

  it("falls back to a disabled local contract when dsn is absent", () => {
    const config = resolveDesktopSentryConfig({
      DEV: true,
      PROD: false,
      MODE: "development",
    } as ImportMetaEnv);

    expect(config.enabled).toBe(false);
    expect(config.environment).toBe("development");
    expect(config.release).toBe(DEFAULT_DESKTOP_RENDERER_RELEASE);
    expect(config.tracesSampleRate).toBe(0);
    expect(config.tracePropagationTargets).toEqual([]);
  });

  it("respects explicit disable even when dsn is present", () => {
    const config = resolveDesktopSentryConfig({
      DEV: false,
      PROD: true,
      MODE: "production",
      VITE_SENTRY_DSN: "https://public@example.com/42",
      VITE_SENTRY_ENABLED: "0",
    } as ImportMetaEnv);

    expect(config.enabled).toBe(false);
    expect(config.dsn).toBe("https://public@example.com/42");
  });
});

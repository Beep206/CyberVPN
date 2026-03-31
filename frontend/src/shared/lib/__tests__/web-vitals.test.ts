import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const metricsDistribution = vi.fn();
const addBreadcrumb = vi.fn();

vi.mock('@sentry/nextjs', () => ({
  addBreadcrumb,
  metrics: {
    distribution: metricsDistribution,
  },
}));

vi.mock('web-vitals', () => ({
  onCLS: (callback: (metric: { value: number; rating: string }) => void) => {
    callback({ value: 0.03, rating: 'good' });
  },
  onLCP: (callback: (metric: { value: number; rating: string }) => void) => {
    callback({ value: 1800, rating: 'good' });
  },
  onFCP: (callback: (metric: { value: number; rating: string }) => void) => {
    callback({ value: 900, rating: 'good' });
  },
  onTTFB: (callback: (metric: { value: number; rating: string }) => void) => {
    callback({ value: 250, rating: 'good' });
  },
  onINP: (callback: (metric: { value: number; rating: string }) => void) => {
    callback({ value: 120, rating: 'good' });
  },
}));

const ORIGINAL_MATCH_MEDIA = window.matchMedia;
const ORIGINAL_INNER_WIDTH = window.innerWidth;
const ORIGINAL_PATHNAME = window.location.pathname;
const ORIGINAL_SEND_BEACON = navigator.sendBeacon;
const sendBeacon = vi.fn();

function installMatchMedia(matchesByQuery: Record<string, boolean>) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn((query: string) => ({
      matches: matchesByQuery[query] ?? false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

function setNavigatorHints() {
  Object.defineProperty(window.navigator, 'hardwareConcurrency', {
    configurable: true,
    value: 8,
  });

  Object.defineProperty(window.navigator, 'deviceMemory', {
    configurable: true,
    value: 8,
  });

  Object.defineProperty(window.navigator, 'maxTouchPoints', {
    configurable: true,
    value: 5,
  });

  Object.defineProperty(window.navigator, 'connection', {
    configurable: true,
    value: {
      effectiveType: '4g',
      saveData: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    },
  });
}

describe('reportWebVitals', () => {
  beforeEach(() => {
    vi.resetModules();
    metricsDistribution.mockClear();
    addBreadcrumb.mockClear();
    sendBeacon.mockClear();

    installMatchMedia({
      '(hover: hover) and (pointer: fine)': false,
      '(pointer: coarse)': true,
      '(prefers-reduced-motion: reduce)': false,
    });
    setNavigatorHints();
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: 390,
    });
    window.location.pathname = '/en-EN/dashboard/servers';
    Object.defineProperty(window.navigator, 'sendBeacon', {
      configurable: true,
      value: sendBeacon,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: ORIGINAL_MATCH_MEDIA,
    });
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: ORIGINAL_INNER_WIDTH,
    });
    window.location.pathname = ORIGINAL_PATHNAME;
    Object.defineProperty(window.navigator, 'sendBeacon', {
      configurable: true,
      value: ORIGINAL_SEND_BEACON,
    });
  });

  it('attaches mobile context attributes to reported Sentry metrics', async () => {
    const { reportWebVitals } = await import('../web-vitals');

    await reportWebVitals();

    expect(metricsDistribution).toHaveBeenCalledTimes(5);
    expect(metricsDistribution).toHaveBeenCalledWith(
      'web-vitals.cls',
      0.03,
      expect.objectContaining({
        unit: 'none',
        attributes: expect.objectContaining({
          connection_type: '4g',
          device_bucket: 'mobile-touch',
          metric: 'cls',
          rating: 'good',
          reduced_motion: 'no-preference',
          route_group: 'dashboard',
          save_data: 'off',
          viewport_bucket: 'mobile-regular',
        }),
      }),
    );
    expect(sendBeacon).toHaveBeenCalledTimes(5);
  });
});

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

const addBreadcrumb = vi.fn();

vi.mock('@sentry/nextjs', () => ({
  addBreadcrumb,
}));

const ORIGINAL_SEND_BEACON = navigator.sendBeacon;
const sendBeacon = vi.fn();

describe('frontend observability helpers', () => {
  beforeEach(() => {
    addBreadcrumb.mockClear();
    sendBeacon.mockClear();
    Object.defineProperty(window.navigator, 'sendBeacon', {
      configurable: true,
      value: sendBeacon,
    });
    Object.defineProperty(window.navigator, 'connection', {
      configurable: true,
      value: {
        effectiveType: '4g',
        saveData: false,
      },
    });
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
      value: 0,
    });
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      value: 1440,
    });
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: vi.fn((query: string) => ({
        matches: query === '(hover: hover) and (pointer: fine)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
    window.location.pathname = '/ru-RU/dashboard';
  });

  afterEach(() => {
    Object.defineProperty(window.navigator, 'sendBeacon', {
      configurable: true,
      value: ORIGINAL_SEND_BEACON,
    });
  });

  it('normalizes high-cardinality endpoint segments', async () => {
    const { normalizeFrontendApiEndpointTemplate } = await import('../frontend-observability');

    expect(
      normalizeFrontendApiEndpointTemplate(
        '/api/v1/partner-workspaces/4f8731b2-d1e4-4bc7-a818-9dc0acdd80d1/review-requests/12345',
      ),
    ).toBe('/api/v1/partner-workspaces/:id/review-requests/:id');
  });

  it('sends runtime events through sendBeacon and records breadcrumbs', async () => {
    const { reportFrontendRouteGuardBlock } = await import('../frontend-observability');

    reportFrontendRouteGuardBlock('partner_portal', {
      blockedReason: 'release_ring',
      lane: 'creator_affiliate',
      releaseRing: 'R1',
      workspaceStatus: 'approved_probation',
    });

    expect(sendBeacon).toHaveBeenCalledTimes(1);
    expect(addBreadcrumb).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'frontend.runtime',
        message: 'route_guard_block',
      }),
    );
  });
});

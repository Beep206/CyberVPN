import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { createElement, type ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '@/test/mocks/server';
import {
  areInviteCodesEnabled,
  DISABLED_CLIENT_CAPABILITIES,
  hasManualInvoiceFallback,
  isAnyGrowthSurfaceEnabled,
  isClientCapabilitiesReady,
  isCustomerOnboardingAvailable,
  isCustomerSiteCabinetOnly,
  isCustomerSiteMaintenanceMode,
  isPostRegistrationCodePromptEnabled,
  isTelegramMiniAppOnboardingEnabled,
  isWebOtpOnboardingEnabled,
  useClientCapabilities,
} from '@/features/client-capabilities/useClientCapabilities';
import type { ClientCapabilitiesResponse } from '../client-capabilities';
import { clientCapabilitiesApi } from '../client-capabilities';

const API_BASE = '*/api/v1';

const RUNTIME_CAPABILITIES: ClientCapabilitiesResponse = {
  auth: {
    email_password: true,
    magic_link: true,
    telegram: true,
  },
  payments: {
    web_checkout: false,
    telegram_stars: true,
    cryptobot: false,
    manual_invoice: true,
    autorenewal: false,
  },
  growth: {
    invites: true,
    referral: true,
    promo_codes: true,
    gift_codes: true,
    checkout_code_discounts: true,
    growth_hub: true,
  },
  subscriptions: {
    multi_subscription: true,
    selected_subscription_required: true,
    addons: true,
    upgrade: true,
    trial: true,
    paid_provisioning: true,
  },
  partner: {
    portal: true,
    applications: true,
    codes: true,
    attribution: true,
    storefronts: true,
    reporting: true,
    settlement_sandbox: true,
    webhooks: true,
    payouts: false,
    event_backbone: true,
  },
  site: {
    customer_site_mode: 'cabinet_only',
    cabinet_only: true,
    version: 1,
    public_hosts: ['cyber-vpn.net'],
    cabinet_hosts: ['app.cyber-vpn.net'],
    cabinet_destination_path: '/dashboard',
    cabinet_marketing_route_action: 'redirect_public',
    public_marketing_destination_path: '/',
    allowed_path_prefixes: ['/dashboard', '/rewards'],
    preserve_query_keys: ['ref', 'partner'],
    registration_policy_independent: true,
  },
  onboarding: {
    post_registration_code_prompt: true,
    web_otp: true,
    telegram_miniapp: true,
    state_store: true,
    flow_key: 'post_registration_growth_code_v1',
    version: 1,
    allowed_code_types: ['promo', 'invite', 'gift'],
    allow_referral_input: false,
    allow_partner_input: false,
    available: true,
  },
};

const REQUIRED_RUNTIME_CAPABILITIES: ClientCapabilitiesResponse = {
  payments: {
    web_checkout: true,
    telegram_stars: false,
    cryptobot: true,
    manual_invoice: false,
    autorenewal: false,
  },
  growth: {
    invites: false,
    referral: false,
    promo_codes: false,
    gift_codes: false,
    checkout_code_discounts: false,
    growth_hub: false,
  },
  subscriptions: {
    multi_subscription: true,
    selected_subscription_required: true,
    addons: false,
    upgrade: true,
    trial: false,
    paid_provisioning: false,
  },
  partner: {
    portal: false,
    applications: false,
    codes: false,
    attribution: false,
    storefronts: false,
    reporting: false,
    settlement_sandbox: false,
    webhooks: false,
    payouts: false,
    event_backbone: false,
  },
};

function createQueryWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retryDelay: 0,
      },
    },
  });

  return function QueryWrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

describe('clientCapabilitiesApi', () => {
  it('loads runtime client capabilities', async () => {
    server.use(
      http.get(`${API_BASE}/client/capabilities`, () =>
        HttpResponse.json(RUNTIME_CAPABILITIES),
      ),
    );

    const response = await clientCapabilitiesApi.get();

    expect(response.data.growth.referral).toBe(true);
    expect(response.data.payments.web_checkout).toBe(false);
    expect(response.data.payments.manual_invoice).toBe(true);
    expect(response.data.partner.payouts).toBe(false);
    expect(response.data.site?.customer_site_mode).toBe('cabinet_only');
    expect(response.data.site?.cabinet_hosts).toEqual(['app.cyber-vpn.net']);
    expect(response.data.onboarding?.available).toBe(true);
    expect(response.data.onboarding?.allowed_code_types).toEqual([
      'promo',
      'invite',
      'gift',
    ]);
  });

  it('keeps runtime data authoritative when generated-default sections are omitted', async () => {
    server.use(
      http.get(`${API_BASE}/client/capabilities`, () =>
        HttpResponse.json(REQUIRED_RUNTIME_CAPABILITIES),
      ),
    );

    const response = await clientCapabilitiesApi.get();

    expect(response.data).toEqual(REQUIRED_RUNTIME_CAPABILITIES);
    expect(response.data.auth).toBeUndefined();
    expect(response.data.site).toBeUndefined();
    expect(response.data.onboarding).toBeUndefined();
    expect(isCustomerSiteCabinetOnly(response.data)).toBe(false);
    expect(isCustomerOnboardingAvailable(response.data)).toBe(false);
  });

  it('rejects degraded capability responses without converting them to empty success', async () => {
    server.use(
      http.get(`${API_BASE}/client/capabilities`, () =>
        HttpResponse.json(
          { detail: 'capabilities unavailable' },
          { status: 503 },
        ),
      ),
    );

    await expect(clientCapabilitiesApi.get()).rejects.toMatchObject({
      response: {
        status: 503,
      },
    });
  });

  it('rejects validation responses without replacing them with defaults', async () => {
    server.use(
      http.get(`${API_BASE}/client/capabilities`, () =>
        HttpResponse.json({ detail: 'invalid capability projection' }, { status: 422 }),
      ),
    );

    await expect(clientCapabilitiesApi.get()).rejects.toMatchObject({
      response: {
        status: 422,
      },
    });
  });

  it('does not run authenticated refresh or redirect on public capability 401', async () => {
    let refreshCalls = 0;
    window.location.href = 'http://localhost:3000/en-EN/pricing';

    server.use(
      http.get(`${API_BASE}/client/capabilities`, () =>
        HttpResponse.json({ detail: 'Unauthorized' }, { status: 401 }),
      ),
      http.post(`${API_BASE}/auth/refresh`, () => {
        refreshCalls += 1;
        return HttpResponse.json({ detail: 'unexpected refresh' });
      }),
    );

    await expect(clientCapabilitiesApi.get()).rejects.toMatchObject({
      response: {
        status: 401,
      },
    });

    expect(refreshCalls).toBe(0);
    expect(window.location.href).toBe('http://localhost:3000/en-EN/pricing');
  });
});

describe('useClientCapabilities', () => {
  it('fails closed for pending capability state and then exposes runtime readiness', async () => {
    let releaseCapabilities: () => void = () => undefined;
    const capabilitiesRequest = new Promise<void>((resolve) => {
      releaseCapabilities = resolve;
    });

    server.use(
      http.get(`${API_BASE}/client/capabilities`, async () => {
        await capabilitiesRequest;
        return HttpResponse.json(RUNTIME_CAPABILITIES);
      }),
    );

    const { result } = renderHook(() => useClientCapabilities(), {
      wrapper: createQueryWrapper(),
    });

    expect(result.current.data).toEqual(DISABLED_CLIENT_CAPABILITIES);
    expect(result.current.isPlaceholderData).toBe(true);
    expect(areInviteCodesEnabled(result.current.data)).toBe(false);
    expect(isAnyGrowthSurfaceEnabled(result.current.data)).toBe(false);
    expect(isCustomerOnboardingAvailable(result.current.data)).toBe(false);
    expect(isPostRegistrationCodePromptEnabled(result.current.data)).toBe(false);
    expect(isCustomerSiteCabinetOnly(result.current.data)).toBe(false);

    releaseCapabilities();

    await waitFor(() => {
      expect(result.current.isPlaceholderData).toBe(false);
      expect(result.current.data).toEqual(RUNTIME_CAPABILITIES);
    });

    expect(areInviteCodesEnabled(result.current.data)).toBe(true);
    expect(isAnyGrowthSurfaceEnabled(result.current.data)).toBe(true);
    expect(isCustomerSiteCabinetOnly(result.current.data)).toBe(true);
    expect(isCustomerOnboardingAvailable(result.current.data)).toBe(true);
    expect(isPostRegistrationCodePromptEnabled(result.current.data)).toBe(true);
    expect(isWebOtpOnboardingEnabled(result.current.data)).toBe(true);
    expect(isTelegramMiniAppOnboardingEnabled(result.current.data)).toBe(true);
  });

  it('uses disabled defaults for empty and degraded capability helpers', () => {
    expect(areInviteCodesEnabled(undefined)).toBe(false);
    expect(isAnyGrowthSurfaceEnabled(undefined)).toBe(false);
    expect(hasManualInvoiceFallback(undefined)).toBe(false);
    expect(isCustomerSiteCabinetOnly(undefined)).toBe(false);
    expect(isCustomerSiteMaintenanceMode(undefined)).toBe(false);
    expect(isCustomerOnboardingAvailable(undefined)).toBe(false);
    expect(isPostRegistrationCodePromptEnabled(undefined)).toBe(false);

    expect(DISABLED_CLIENT_CAPABILITIES.auth?.email_password).toBe(true);
    expect(DISABLED_CLIENT_CAPABILITIES.auth?.magic_link).toBe(true);
    expect(DISABLED_CLIENT_CAPABILITIES.auth?.telegram).toBe(true);
    expect(DISABLED_CLIENT_CAPABILITIES.payments).toEqual({
      web_checkout: false,
      telegram_stars: false,
      cryptobot: false,
      manual_invoice: false,
      autorenewal: false,
    });
    expect(hasManualInvoiceFallback(DISABLED_CLIENT_CAPABILITIES)).toBe(false);
    expect(DISABLED_CLIENT_CAPABILITIES.subscriptions).toEqual({
      multi_subscription: true,
      selected_subscription_required: true,
      addons: false,
      upgrade: true,
      trial: false,
      paid_provisioning: false,
    });
    expect(DISABLED_CLIENT_CAPABILITIES.site?.customer_site_mode).toBe(
      'full_site',
    );
    expect(DISABLED_CLIENT_CAPABILITIES.site?.cabinet_only).toBe(false);
    expect(DISABLED_CLIENT_CAPABILITIES.onboarding?.available).toBe(false);
    expect(DISABLED_CLIENT_CAPABILITIES.onboarding?.allowed_code_types).toEqual(
      [],
    );
    expect(
      isClientCapabilitiesReady({
        isSuccess: true,
        isPlaceholderData: true,
      }),
    ).toBe(false);
    expect(isClientCapabilitiesReady({ isSuccess: false })).toBe(false);
    expect(
      isClientCapabilitiesReady({
        isSuccess: true,
        isPlaceholderData: false,
      }),
    ).toBe(true);
  });

  it('keeps helpers disabled and retries once on terminal 503', async () => {
    let requestCount = 0;

    server.use(
      http.get(`${API_BASE}/client/capabilities`, () => {
        requestCount += 1;
        return HttpResponse.json(
          { detail: 'capabilities unavailable' },
          { status: 503 },
        );
      }),
    );

    const { result } = renderHook(() => useClientCapabilities(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(requestCount).toBe(2);
    expect(isClientCapabilitiesReady(result.current)).toBe(false);
    expect(areInviteCodesEnabled(result.current.data)).toBe(false);
    expect(isAnyGrowthSurfaceEnabled(result.current.data)).toBe(false);
    expect(isCustomerOnboardingAvailable(result.current.data)).toBe(false);
    expect(isCustomerSiteCabinetOnly(result.current.data)).toBe(false);
  });

  it('keeps helpers disabled and retries once on network failure', async () => {
    let requestCount = 0;

    server.use(
      http.get(`${API_BASE}/client/capabilities`, () => {
        requestCount += 1;
        return HttpResponse.error();
      }),
    );

    const { result } = renderHook(() => useClientCapabilities(), {
      wrapper: createQueryWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(requestCount).toBe(2);
    expect(isClientCapabilitiesReady(result.current)).toBe(false);
    expect(areInviteCodesEnabled(result.current.data)).toBe(false);
    expect(isAnyGrowthSurfaceEnabled(result.current.data)).toBe(false);
    expect(isCustomerOnboardingAvailable(result.current.data)).toBe(false);
    expect(isCustomerSiteCabinetOnly(result.current.data)).toBe(false);
  });
});

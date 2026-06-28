import type { ReactNode } from 'react';
import fs from 'node:fs';
import path from 'node:path';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuthStore } from '@/stores/auth-store';
import {
  GrowthFxConsole,
  GrowthOnboardingConsole,
  GrowthPrivateAccessConsole,
  GrowthRiskConsole,
} from '../growth-v6-operations-console';

const {
  mockGetClientCapabilities,
  mockGetPrivateCatalogGrant,
  mockGetGrowthFxStatus,
  mockListGrowthFxRates,
  mockApproveGrowthFxRate,
  mockRefreshGrowthFxRates,
  mockRejectGrowthFxRate,
  mockDisableGrowthFxProvider,
  mockEnableGrowthFxProvider,
  mockGetGrowthOnboardingSettings,
  mockListGrowthOnboardingStates,
  mockListPrivateCatalogTargets,
  mockListPrivateCatalogGrants,
  mockListGrowthRiskDecisions,
  mockListGrowthRiskModels,
  mockListGrowthRiskReviews,
  mockResetGrowthOnboardingState,
  mockResolveGrowthRiskReview,
  mockRevokePrivateCatalogGrant,
  mockSimulateGrowthFxConversion,
  mockUpdateGrowthOnboardingSettings,
} = vi.hoisted(() => ({
  mockGetClientCapabilities: vi.fn(),
  mockGetPrivateCatalogGrant: vi.fn(),
  mockGetGrowthFxStatus: vi.fn(),
  mockListGrowthFxRates: vi.fn(),
  mockApproveGrowthFxRate: vi.fn(),
  mockRefreshGrowthFxRates: vi.fn(),
  mockRejectGrowthFxRate: vi.fn(),
  mockDisableGrowthFxProvider: vi.fn(),
  mockEnableGrowthFxProvider: vi.fn(),
  mockGetGrowthOnboardingSettings: vi.fn(),
  mockListGrowthOnboardingStates: vi.fn(),
  mockListPrivateCatalogTargets: vi.fn(),
  mockListPrivateCatalogGrants: vi.fn(),
  mockListGrowthRiskDecisions: vi.fn(),
  mockListGrowthRiskModels: vi.fn(),
  mockListGrowthRiskReviews: vi.fn(),
  mockResetGrowthOnboardingState: vi.fn(),
  mockResolveGrowthRiskReview: vi.fn(),
  mockRevokePrivateCatalogGrant: vi.fn(),
  mockSimulateGrowthFxConversion: vi.fn(),
  mockUpdateGrowthOnboardingSettings: vi.fn(),
}));

vi.mock('@/lib/api/growth', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/growth')>('@/lib/api/growth');
  return {
    ...actual,
    growthApi: {
      ...actual.growthApi,
      getClientCapabilities: (...args: unknown[]) => mockGetClientCapabilities(...args),
      getPrivateCatalogGrant: (...args: unknown[]) => mockGetPrivateCatalogGrant(...args),
      getGrowthFxStatus: (...args: unknown[]) => mockGetGrowthFxStatus(...args),
      listGrowthFxRates: (...args: unknown[]) => mockListGrowthFxRates(...args),
      approveGrowthFxRate: (...args: unknown[]) => mockApproveGrowthFxRate(...args),
      refreshGrowthFxRates: (...args: unknown[]) => mockRefreshGrowthFxRates(...args),
      rejectGrowthFxRate: (...args: unknown[]) => mockRejectGrowthFxRate(...args),
      disableGrowthFxProvider: (...args: unknown[]) => mockDisableGrowthFxProvider(...args),
      enableGrowthFxProvider: (...args: unknown[]) => mockEnableGrowthFxProvider(...args),
      getGrowthOnboardingSettings: (...args: unknown[]) => mockGetGrowthOnboardingSettings(...args),
      listGrowthOnboardingStates: (...args: unknown[]) => mockListGrowthOnboardingStates(...args),
      listPrivateCatalogTargets: (...args: unknown[]) => mockListPrivateCatalogTargets(...args),
      listPrivateCatalogGrants: (...args: unknown[]) => mockListPrivateCatalogGrants(...args),
      listGrowthRiskDecisions: (...args: unknown[]) => mockListGrowthRiskDecisions(...args),
      listGrowthRiskModels: (...args: unknown[]) => mockListGrowthRiskModels(...args),
      listGrowthRiskReviews: (...args: unknown[]) => mockListGrowthRiskReviews(...args),
      resetGrowthOnboardingState: (...args: unknown[]) => mockResetGrowthOnboardingState(...args),
      resolveGrowthRiskReview: (...args: unknown[]) => mockResolveGrowthRiskReview(...args),
      revokePrivateCatalogGrant: (...args: unknown[]) => mockRevokePrivateCatalogGrant(...args),
      simulateGrowthFxConversion: (...args: unknown[]) => mockSimulateGrowthFxConversion(...args),
      updateGrowthOnboardingSettings: (...args: unknown[]) => mockUpdateGrowthOnboardingSettings(...args),
    },
  };
});

function renderWithQueryClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

function loadGrowthMessages(locale: 'en-EN' | 'ru-RU') {
  return JSON.parse(
    fs.readFileSync(path.join(process.cwd(), 'messages', locale, 'growth.json'), 'utf8'),
  ) as Record<string, unknown>;
}

function getMessage(messages: Record<string, unknown>, keyPath: string) {
  return keyPath.split('.').reduce<unknown>((currentValue, key) => {
    if (!currentValue || typeof currentValue !== 'object' || Array.isArray(currentValue)) {
      return undefined;
    }

    return (currentValue as Record<string, unknown>)[key];
  }, messages);
}

describe('Growth v6 operations consoles', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: {
        id: 'admin-1',
        email: 'admin@example.com',
        login: 'admin',
        role: 'admin',
        is_active: true,
        is_email_verified: true,
        created_at: '2026-06-26T00:00:00Z',
      },
      isAuthenticated: true,
      isLoading: false,
      error: null,
    });
    mockGetClientCapabilities.mockResolvedValue({
      data: {
        payments: {},
        growth: {
          invites: true,
          referral: true,
          promo_codes: true,
          gift_codes: false,
          checkout_code_discounts: true,
          growth_hub: true,
        },
        subscriptions: {},
        partner: {},
        site: {
          customer_site_mode: 'cabinet_only',
          cabinet_only: true,
          version: 4,
          public_hosts: ['cyber-vpn.net'],
          cabinet_hosts: ['my.cyber-vpn.net'],
          cabinet_destination_path: '/dashboard',
          allowed_path_prefixes: ['/login', '/register'],
          preserve_query_keys: ['ref', 'code'],
          registration_policy_independent: true,
        },
        onboarding: {
          post_registration_code_prompt: true,
          web_otp: true,
          telegram_miniapp: false,
          state_store: true,
          telegram_bot_code_apply: false,
          connection_bootstrap: true,
          flow_key: 'post_registration_growth_code_v1',
          version: 3,
          allowed_code_types: ['promo', 'invite', 'gift'],
          allow_referral_input: false,
          allow_partner_input: false,
          available: true,
        },
      },
    });
    mockGetGrowthFxStatus.mockResolvedValue({
      data: {
        generated_at: '2026-06-26T00:00:00Z',
        active_rate_count: 2,
        stale_rate_count: 0,
        disabled_rate_count: 0,
        latest_observed_at: '2026-06-26T00:00:00Z',
        latest_valid_until: '2026-06-27T00:00:00Z',
        providers: [
          {
            provider_key: 'ecb',
            enabled: true,
            priority: 10,
            requires_admin_approval: true,
            stale_after_seconds: 3600,
            status: 'active',
          },
        ],
      },
    });
    mockListGrowthFxRates.mockResolvedValue({
      data: {
        items: [
          {
            id: 'rate-1',
            provider_config_id: 'provider-config-1',
            base_currency: 'USD',
            quote_currency: 'RUB',
            rate: '92.5100',
            inverse_rate: '0.0108',
            source_type: 'provider',
            provider_key: 'ecb',
            provider_priority: 10,
            provider_rate_id: 'ecb-2026-06-26',
            observed_at: '2026-06-26T00:00:00Z',
            fetched_at: '2026-06-26T00:01:00Z',
            valid_until: '2026-06-27T00:00:00Z',
            status: 'pending_approval',
            approval_state: 'pending',
            approved_by_admin_id: null,
            approved_at: null,
            rejection_reason: null,
            checksum: 'a'.repeat(64),
            raw_provider_payload_hash: 'b'.repeat(64),
            metadata: {},
            created_at: '2026-06-26T00:01:00Z',
          },
        ],
        total: 1,
        limit: 8,
        offset: 0,
      },
    });
    mockApproveGrowthFxRate.mockResolvedValue({
      data: {
        id: 'rate-1',
        provider_config_id: 'provider-config-1',
        base_currency: 'USD',
        quote_currency: 'RUB',
        rate: '92.5100',
        inverse_rate: '0.0108',
        source_type: 'provider',
        provider_key: 'ecb',
        provider_priority: 10,
        provider_rate_id: 'ecb-2026-06-26',
        observed_at: '2026-06-26T00:00:00Z',
        fetched_at: '2026-06-26T00:01:00Z',
        valid_until: '2026-06-27T00:00:00Z',
        status: 'active',
        approval_state: 'approved',
        approved_by_admin_id: 'admin-checker',
        approved_at: '2026-06-26T00:02:00Z',
        rejection_reason: null,
        checksum: 'a'.repeat(64),
        raw_provider_payload_hash: 'b'.repeat(64),
        metadata: {},
        created_at: '2026-06-26T00:01:00Z',
      },
    });
    mockRefreshGrowthFxRates.mockResolvedValue({
      data: {
        runs: [
          {
            id: 'run-1',
            provider_config_id: 'provider-config-1',
            provider_key: 'ecb',
            run_key: 'fx-refresh:ecb:test',
            status: 'succeeded',
            trigger_type: 'admin',
            requested_by_admin_id: 'admin-1',
            started_at: '2026-06-26T00:00:00Z',
            finished_at: '2026-06-26T00:00:01Z',
            pairs_requested: [{ base_currency: 'USD', quote_currency: 'RUB' }],
            pairs_succeeded: [{ base_currency: 'USD', quote_currency: 'RUB' }],
            pairs_failed: [],
            created_snapshot_ids: ['rate-2'],
            provider_payload_hash: 'c'.repeat(64),
            error_code: null,
            error_message: null,
          },
        ],
        created_snapshots: [],
      },
    });
    mockRejectGrowthFxRate.mockResolvedValue({
      data: {
        id: 'rate-1',
        provider_config_id: 'provider-config-1',
        base_currency: 'USD',
        quote_currency: 'RUB',
        rate: '92.5100',
        inverse_rate: '0.0108',
        source_type: 'provider',
        provider_key: 'ecb',
        provider_priority: 10,
        provider_rate_id: 'ecb-2026-06-26',
        observed_at: '2026-06-26T00:00:00Z',
        fetched_at: '2026-06-26T00:01:00Z',
        valid_until: '2026-06-27T00:00:00Z',
        status: 'rejected',
        approval_state: 'rejected',
        approved_by_admin_id: null,
        approved_at: null,
        rejection_reason: 'growth_fx_lifecycle_review',
        checksum: 'a'.repeat(64),
        raw_provider_payload_hash: 'b'.repeat(64),
        metadata: {},
        created_at: '2026-06-26T00:01:00Z',
      },
    });
    mockDisableGrowthFxProvider.mockResolvedValue({ data: { providers: [] } });
    mockEnableGrowthFxProvider.mockResolvedValue({ data: { providers: [] } });
    mockSimulateGrowthFxConversion.mockResolvedValue({
      data: {
        source_amount: '10.00',
        source_currency: 'USD',
        target_currency: 'RUB',
        raw_converted_amount: '925.1000',
        rounded_amount: '925.10',
        applied_amount: '925.10',
        target_minor_units: 2,
        rounding_mode: 'ROUND_HALF_UP',
        conversion_mode: 'market',
        rate_snapshot: {},
        no_rerate: true,
      },
    });
    mockListPrivateCatalogTargets.mockResolvedValue({
      data: {
        items: [],
        total: 0,
        limit: 1,
        offset: 0,
      },
    });
    mockListPrivateCatalogGrants.mockResolvedValue({
      data: {
        items: [
          {
            id: 'grant-1',
            policy_id: 'policy-1',
            policy_version_id: 'policy-version-1',
            growth_code_id: 'growth-code-1',
            code_set_hash: 'hash-1',
            user_id: 'user-1',
            anonymous_session_id: null,
            risk_subject_id: null,
            auth_realm_id: 'realm-1',
            storefront_id: 'storefront-1',
            sale_channel: 'web',
            allowed_plan_ids: [],
            allowed_offer_ids: [],
            risk_decision_id: null,
            status: 'active',
            max_quote_conversions: null,
            quote_conversions_count: 0,
            issued_at: '2026-06-26T00:00:00Z',
            expires_at: '2026-06-27T00:00:00Z',
            attached_quote_session_id: null,
            attached_checkout_session_id: null,
            consumed_order_id: null,
            revoked_at: null,
            revoked_reason: null,
            metadata: {},
            created_at: '2026-06-26T00:00:00Z',
            updated_at: '2026-06-26T00:00:00Z',
          },
        ],
        total: 1,
        limit: 3,
        offset: 0,
      },
    });
    mockGetPrivateCatalogGrant.mockResolvedValue({
      data: {
        id: 'grant-1',
        status: 'active',
        code_set_hash: 'hash-1',
      },
    });
    mockRevokePrivateCatalogGrant.mockResolvedValue({
      data: {
        id: 'grant-1',
        status: 'revoked',
        code_set_hash: 'hash-1',
      },
    });
    mockGetGrowthOnboardingSettings.mockResolvedValue({
      data: {
        post_registration_code_prompt_enabled: true,
        web_otp_enabled: true,
        telegram_miniapp_enabled: false,
        state_store_ready: true,
        flow_key: 'post_registration_growth_code_v1',
        version: 3,
        allowed_code_types: ['promo', 'invite', 'gift'],
        allow_referral_input: false,
        allow_partner_input: false,
        available: true,
        config_updated_at: '2026-06-26T00:00:00Z',
        updated_by_admin_user_id: null,
      },
    });
    mockListGrowthOnboardingStates.mockResolvedValue({
      data: {
        items: [
          {
            id: 'state-1',
            mobile_user_id: 'mobile-user-1',
            flow_key: 'post_registration_growth_code_v1',
            flow_version: 3,
            source_channel: 'web',
            status: 'completed',
            skippable: true,
            policy_version_id: null,
            first_eligible_at: '2026-06-26T00:00:00Z',
            first_shown_at: '2026-06-26T00:00:00Z',
            last_shown_at: '2026-06-26T00:00:00Z',
            display_count: 2,
            submitted_at: '2026-06-26T00:00:00Z',
            completed_at: '2026-06-26T00:00:00Z',
            skipped_at: null,
            expires_at: null,
            result_code_application_id: null,
            signup_finalization_id: null,
            referral_terminal_state: null,
            canonical_identity_link_id: null,
            auth_channel: 'web_otp',
            return_route_key: null,
            result_payload: {},
            application_count: 1,
            created_at: '2026-06-26T00:00:00Z',
            updated_at: '2026-06-26T00:00:00Z',
          },
        ],
        total: 1,
        limit: 3,
        offset: 0,
      },
    });
    mockUpdateGrowthOnboardingSettings.mockResolvedValue({
      data: {
        post_registration_code_prompt_enabled: true,
        web_otp_enabled: true,
        telegram_miniapp_enabled: false,
        state_store_ready: true,
        flow_key: 'post_registration_growth_code_v1',
        version: 3,
        allowed_code_types: ['promo', 'invite', 'gift'],
        allow_referral_input: false,
        allow_partner_input: false,
        available: true,
        config_updated_at: '2026-06-26T00:00:00Z',
        updated_by_admin_user_id: null,
      },
    });
    mockResetGrowthOnboardingState.mockResolvedValue({
      data: {
        id: 'state-1',
        status: 'pending',
      },
    });
    mockListGrowthRiskModels.mockResolvedValue({
      data: {
        items: [
          {
            id: 'model-1',
            model_key: 'growth-risk',
            version: 'v1',
            artifact_uri: 's3://models/growth-risk/v1',
            artifact_checksum: 'checksum',
            feature_schema_version: 'growth-risk.v6.features.v1',
            model_type: 'gradient_boosted_trees',
            training_window_start: null,
            training_window_end: null,
            metrics: {},
            calibration: {},
            deployment_mode: 'shadow',
            approval_state: 'approved',
            status: 'active',
            created_by: null,
            approved_by: null,
            created_at: '2026-06-26T00:00:00Z',
            deployed_at: null,
            retired_at: null,
          },
        ],
        total: 1,
        limit: 3,
        offset: 0,
      },
    });
    mockListGrowthRiskDecisions.mockResolvedValue({
      data: {
        items: [
          {
            id: 'decision-1',
            risk_subject_id: 'subject-1',
            code_set_id: null,
            growth_code_id: null,
            private_grant_id: null,
            quote_session_id: null,
            order_id: null,
            action_context: 'checkout',
            rules_policy_version_id: 'policy-version-1',
            model_version_id: 'model-1',
            feature_snapshot_id: null,
            rules_outcome: 'allow',
            ml_score: null,
            risk_band: 'low',
            final_action: 'allow',
            reason_codes: [],
            fallback_mode: null,
            decided_at: '2026-06-26T00:00:00Z',
            created_at: '2026-06-26T00:00:00Z',
          },
        ],
        total: 1,
        limit: 3,
        offset: 0,
      },
    });
    mockListGrowthRiskReviews.mockResolvedValue({
      data: {
        items: [
          {
            id: 'review-1',
            risk_subject_id: 'subject-1',
            review_type: 'manual',
            status: 'open',
            decision: 'pending',
            reason: 'manual review',
            evidence: {},
            created_by_admin_user_id: null,
            resolved_by_admin_user_id: null,
            resolved_at: null,
            created_at: '2026-06-26T00:00:00Z',
            updated_at: '2026-06-26T00:00:00Z',
          },
        ],
        total: 1,
        limit: 3,
        offset: 0,
      },
    });
    mockResolveGrowthRiskReview.mockResolvedValue({
      data: {
        id: 'review-1',
        status: 'resolved',
      },
    });
  });

  it('renders the FX console from generated capabilities and generated FX status wrapper', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<GrowthFxConsole />);

    expect(await screen.findByText('fx.title')).toBeInTheDocument();
    expect(screen.getByText('/api/v1/client/capabilities')).toBeInTheDocument();
    expect(screen.getByText('/api/v3/admin/growth/fx/status')).toBeInTheDocument();
    expect(await screen.findByText('USD/RUB 92.5100')).toBeInTheDocument();
    expect(screen.getByText(/ecb \/ active/i)).toBeInTheDocument();
    expect(await screen.findAllByText('v6.common.generatedWrapper')).not.toHaveLength(0);
    await user.click(screen.getByRole('button', { name: 'fx.actions.simulate' }));
    expect(mockSimulateGrowthFxConversion).toHaveBeenCalledWith({
      source_amount: '10.00',
      source_currency: 'USD',
      target_currency: 'RUB',
      eligible_discount_base: '10.00',
      conversion_mode: 'market',
    });
    await user.click(screen.getByRole('button', { name: 'fx.actions.approveRate' }));
    expect(mockApproveGrowthFxRate).toHaveBeenCalledWith('rate-1', {
      change_reason: 'growth_fx_lifecycle_review',
    });
    await user.click(screen.getByRole('button', { name: 'fx.actions.refreshRates' }));
    expect(mockRefreshGrowthFxRates).toHaveBeenCalledWith({
      provider_key: 'ecb',
      idempotency_key: expect.stringMatching(/^admin-growth-fx-refresh-/),
      change_reason: 'growth_fx_lifecycle_review',
    });
    await user.click(screen.getByRole('button', { name: 'fx.actions.rejectRate' }));
    expect(mockRejectGrowthFxRate).toHaveBeenCalledWith('rate-1', {
      change_reason: 'growth_fx_lifecycle_review',
    });
    await user.click(screen.getByRole('button', { name: 'fx.actions.disableProvider' }));
    expect(mockDisableGrowthFxProvider).toHaveBeenCalledWith('ecb', {
      change_reason: 'growth_fx_lifecycle_review',
    });

    await user.click(await screen.findByRole('button', { name: 'v6.common.refresh' }));
    expect(mockGetClientCapabilities).toHaveBeenCalledTimes(2);
    expect(mockGetGrowthFxStatus).toHaveBeenCalled();
    expect(mockListGrowthFxRates).toHaveBeenCalledWith({ limit: 8, offset: 0 });
  });

  it('keeps FX lifecycle mutations read-only for roles without FX lifecycle permissions', async () => {
    const user = userEvent.setup();
    useAuthStore.setState({
      user: {
        id: 'viewer-1',
        email: 'viewer@example.com',
        login: 'viewer',
        role: 'viewer',
        is_active: true,
        is_email_verified: true,
        created_at: '2026-06-26T00:00:00Z',
      },
      isAuthenticated: true,
      isLoading: false,
      error: null,
    });

    renderWithQueryClient(<GrowthFxConsole />);

    expect(await screen.findByText('fx.readOnly')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'fx.actions.approveRate' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'fx.actions.refreshRates' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'fx.actions.rejectRate' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'fx.actions.disableProvider' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'fx.actions.enableProvider' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'fx.actions.approveRate' }));
    expect(mockApproveGrowthFxRate).not.toHaveBeenCalled();
  });

  it('renders private access with generated grant wrappers and executes support actions', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<GrowthPrivateAccessConsole />);

    expect(await screen.findByText('privateAccess.title')).toBeInTheDocument();
    expect(screen.getByText('/api/v3/admin/growth/private-grants/{id}/revoke')).toBeInTheDocument();
    expect(await screen.findAllByText('v6.common.generatedWrapper')).not.toHaveLength(0);
    await user.click(screen.getByRole('button', { name: 'privateAccess.actions.openGrant' }));
    expect(mockGetPrivateCatalogGrant).toHaveBeenCalledWith('grant-1');
    await user.type(screen.getByLabelText('privateAccess.fields.revokeReason'), 'support cleanup');
    await user.click(screen.getByRole('button', { name: 'privateAccess.actions.revokeGrant' }));
    expect(mockRevokePrivateCatalogGrant).toHaveBeenCalledWith('grant-1', {
      reason: 'support cleanup',
      expected_status: 'active',
    });
    expect(mockListPrivateCatalogTargets).toHaveBeenCalledWith({ limit: 1 });
    expect(mockListPrivateCatalogGrants).toHaveBeenCalledWith({ limit: 3 });
  });

  it('renders onboarding settings from generated wrappers and executes audited actions', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<GrowthOnboardingConsole />);

    expect(await screen.findByText('onboarding.title')).toBeInTheDocument();
    expect(await screen.findByText('post_registration_growth_code_v1 v3')).toBeInTheDocument();
    expect(screen.getByText('/api/v3/admin/growth/onboarding/settings')).toBeInTheDocument();
    expect(await screen.findAllByText('v6.common.generatedWrapper')).not.toHaveLength(0);
    expect(screen.getByText('Promo, Invite, Gift')).toBeInTheDocument();
    await user.type(screen.getByLabelText('onboarding.fields.settingsReason'), 'support validation');
    await user.click(screen.getByRole('button', { name: 'onboarding.actions.updateSettings' }));
    expect(mockUpdateGrowthOnboardingSettings).toHaveBeenCalledWith(
      expect.objectContaining({
        flow_key: 'post_registration_growth_code_v1',
        version: 3,
        change_reason: 'support validation',
      }),
    );
    await user.type(screen.getByLabelText('onboarding.fields.resetReason'), 'retry support flow');
    await user.click(screen.getByRole('button', { name: 'onboarding.actions.resetState' }));
    expect(mockResetGrowthOnboardingState).toHaveBeenCalledWith('state-1', {
      reason: 'retry support flow',
      expected_status: 'completed',
    });
    expect(mockGetGrowthOnboardingSettings).toHaveBeenCalled();
    expect(mockListGrowthOnboardingStates).toHaveBeenCalledWith({ limit: 3 });
  });

  it('renders growth risk with generated risk wrappers and resolves reviews', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<GrowthRiskConsole />);

    expect(await screen.findByText('risk.title')).toBeInTheDocument();
    expect(screen.getByText('/api/v3/admin/growth/risk/models')).toBeInTheDocument();
    expect(screen.getByText('/api/v3/admin/growth/risk/reviews/{id}/resolve')).toBeInTheDocument();
    await user.type(screen.getByLabelText('risk.fields.resolutionReason'), 'manual support allow');
    await user.click(screen.getByRole('button', { name: 'risk.actions.resolveReview' }));
    expect(mockResolveGrowthRiskReview).toHaveBeenCalledWith('review-1', {
      decision: 'allow',
      resolution_status: 'resolved',
      resolution_reason: 'manual support allow',
      resolution_evidence: {
        source: 'admin_growth_v6_operations_console',
        previous_status: 'open',
      },
    });
    expect(mockListGrowthRiskModels).toHaveBeenCalledWith({ limit: 3 });
    expect(mockListGrowthRiskDecisions).toHaveBeenCalledWith({ limit: 3 });
    expect(mockListGrowthRiskReviews).toHaveBeenCalledWith({ status: 'open', limit: 3 });
  });

  it('keeps EN and RU Growth i18n keys for every new AC-22 console', () => {
    for (const locale of ['en-EN', 'ru-RU'] as const) {
      const messages = loadGrowthMessages(locale);

      for (const key of [
        'nav.fx',
        'nav.privateAccess',
        'nav.onboarding',
        'fx.degraded.title',
        'fx.lifecycleTitle',
        'fx.actions.approveRate',
        'privateAccess.degraded.title',
        'onboarding.degraded.title',
        'risk.degraded.title',
        'rules.lifecycle.auditTitle',
        'rules.permission.readOnly',
        'siteMode.auditTitle',
        'referrals.riskReviewsTitle',
      ]) {
        expect(getMessage(messages, key)).toEqual(expect.any(String));
      }
    }
  });
});

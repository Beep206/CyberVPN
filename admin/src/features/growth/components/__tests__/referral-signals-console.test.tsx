import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ReferralSignalsConsole } from '../referral-signals-console';

const {
  mockGetGrowthSignalsOverview,
  mockListGrowthAbuseSignals,
  mockListRiskReviewQueue,
} = vi.hoisted(() => ({
  mockGetGrowthSignalsOverview: vi.fn(),
  mockListGrowthAbuseSignals: vi.fn(),
  mockListRiskReviewQueue: vi.fn(),
}));

vi.mock('@/lib/api/growth', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/growth')>('@/lib/api/growth');
  return {
    ...actual,
    growthApi: {
      ...actual.growthApi,
      getGrowthSignalsOverview: (...args: unknown[]) => mockGetGrowthSignalsOverview(...args),
      listGrowthAbuseSignals: (...args: unknown[]) => mockListGrowthAbuseSignals(...args),
    },
  };
});

vi.mock('@/lib/api/security', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/security')>('@/lib/api/security');
  return {
    ...actual,
    securityApi: {
      ...actual.securityApi,
      listRiskReviewQueue: (...args: unknown[]) => mockListRiskReviewQueue(...args),
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

describe('ReferralSignalsConsole risk queue coverage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetGrowthSignalsOverview.mockResolvedValue({
      data: {
        total_codes: 12,
        active_codes: 8,
        total_redemptions: 5,
        active_reservations: 2,
        blocked_reward_count: 1,
        available_referral_credit_usd: 12.5,
        code_status_breakdown: [],
        resolution_result_breakdown: [],
        rejection_reason_breakdown: [],
        redemption_breakdown: [],
        reward_status_breakdown: [{ key: 'blocked_by_risk', count: 1 }],
        reward_type_breakdown: [],
        recent_lifecycle_events: [],
      },
    });
    mockListGrowthAbuseSignals.mockResolvedValue({ data: { items: [] } });
    mockListRiskReviewQueue.mockResolvedValue({
      data: [
        {
          review: {
            id: '6631ddea-bd11-48f3-8ba6-c1d6c06e0001',
            risk_subject_id: '2c53cf97-7073-4904-8473-c497cab90001',
            review_type: 'growth_private_access',
            status: 'open',
            decision: 'pending',
            reason: 'private_launch_velocity',
            evidence: {},
            created_by_admin_user_id: null,
            resolved_by_admin_user_id: null,
            resolved_at: null,
            created_at: '2026-06-20T08:00:00Z',
            updated_at: '2026-06-20T09:00:00Z',
          },
          subject: {
            id: '2c53cf97-7073-4904-8473-c497cab90001',
            principal_class: 'mobile_user',
            principal_subject: 'masked-user',
            auth_realm_id: null,
            storefront_id: null,
            status: 'active',
            risk_level: 'high',
            metadata: {},
            created_at: '2026-06-20T08:00:00Z',
            updated_at: '2026-06-20T09:00:00Z',
          },
          attachment_count: 2,
          governance_action_count: 1,
        },
      ],
    });
  });

  it('renders generated security review queue data with masked subject identifiers', async () => {
    renderWithQueryClient(<ReferralSignalsConsole />);

    expect(await screen.findByText('referrals.riskReviewsTitle')).toBeInTheDocument();
    expect(await screen.findByText('Growth Private Access')).toBeInTheDocument();
    expect(screen.getByText('referrals.maskedSubject')).toBeInTheDocument();
    expect(screen.getByText('High')).toBeInTheDocument();
    expect(mockListRiskReviewQueue).toHaveBeenCalledWith({ status: 'open' });
    expect(screen.queryByText('masked-user')).not.toBeInTheDocument();
  });
});

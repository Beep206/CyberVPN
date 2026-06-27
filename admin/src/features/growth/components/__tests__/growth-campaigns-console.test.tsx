import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { GrowthCampaignsConsole } from '../growth-campaigns-console';

const {
  mockListGrowthCampaigns,
  mockGetGrowthCampaign,
  mockCreateGrowthCampaign,
  mockPublishGrowthCampaign,
} = vi.hoisted(() => ({
  mockListGrowthCampaigns: vi.fn(),
  mockGetGrowthCampaign: vi.fn(),
  mockCreateGrowthCampaign: vi.fn(),
  mockPublishGrowthCampaign: vi.fn(),
}));

vi.mock('@/lib/api/growth', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/growth')>('@/lib/api/growth');
  return {
    ...actual,
    growthApi: {
      ...actual.growthApi,
      listGrowthCampaigns: (...args: unknown[]) => mockListGrowthCampaigns(...args),
      getGrowthCampaign: (...args: unknown[]) => mockGetGrowthCampaign(...args),
      createGrowthCampaign: (...args: unknown[]) => mockCreateGrowthCampaign(...args),
      publishGrowthCampaign: (...args: unknown[]) => mockPublishGrowthCampaign(...args),
    },
  };
});

const campaign = {
  id: '1a61c4ba-9dd3-44e8-9323-3ab9c1fdc001',
  campaign_key: 'PR-PRO100-INV10',
  name: 'Pro annual invite promo',
  description: '100 percent promo with invite batch benefit',
  status: 'draft',
  priority: 10,
  starts_at: null,
  expires_at: null,
  stacking_mode: 'exclusive',
  stacking_group: 'pro',
  current_version: 3,
  created_by_admin_id: '4d4cefc3-35cc-483b-a03d-d48b5d565001',
  updated_by_admin_id: null,
  published_at: null,
  paused_at: null,
  archived_at: null,
  created_at: '2026-04-22T10:00:00Z',
  updated_at: '2026-04-22T10:05:00Z',
};

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

function getCreateForm() {
  const form = screen.getByRole('heading', { name: 'campaigns.createTitle' }).closest('form');
  if (!form) {
    throw new Error('Create form not found.');
  }
  return form;
}

describe('GrowthCampaignsConsole', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListGrowthCampaigns.mockResolvedValue({
      data: {
        items: [campaign],
        total: 1,
        offset: 0,
        limit: 50,
      },
    });
    mockGetGrowthCampaign.mockResolvedValue({ data: campaign });
    mockCreateGrowthCampaign.mockResolvedValue({
      data: {
        ...campaign,
        id: '20a53634-5a96-42e3-9b3e-18e4ad6a1001',
        campaign_key: 'SUMMER-100',
        name: 'Summer promo',
        current_version: 1,
      },
    });
    mockPublishGrowthCampaign.mockResolvedValue({
      data: {
        ...campaign,
        status: 'active',
        current_version: 4,
        published_at: '2026-04-22T10:10:00Z',
      },
    });
  });

  it('creates campaign drafts through the admin growth adapter', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<GrowthCampaignsConsole />);

    await screen.findByText('PR-PRO100-INV10');
    const createForm = getCreateForm();

    await user.type(within(createForm).getByLabelText('campaigns.fields.campaignKey'), 'SUMMER-100');
    await user.type(within(createForm).getByLabelText('campaigns.fields.name'), 'Summer promo');
    await user.clear(within(createForm).getByLabelText('campaigns.fields.priority'));
    await user.type(within(createForm).getByLabelText('campaigns.fields.priority'), '20');
    await user.type(within(createForm).getByLabelText('campaigns.fields.stackingGroup'), 'summer');
    await user.click(within(createForm).getByRole('button', { name: /campaigns.createAction/ }));

    await waitFor(() => {
      expect(mockCreateGrowthCampaign).toHaveBeenCalledWith(
        expect.objectContaining({
          campaign_key: 'SUMMER-100',
          name: 'Summer promo',
          priority: 20,
          stacking: {
            mode: 'exclusive',
            group: 'summer',
          },
        }),
      );
    });
  });

  it('requires typed campaign confirmation before publish mutation', async () => {
    const user = userEvent.setup();
    renderWithQueryClient(<GrowthCampaignsConsole />);

    await screen.findByText('PR-PRO100-INV10');
    await user.click(screen.getByRole('button', { name: 'campaigns.selectCampaign' }));
    const publishButton = await screen.findByRole('button', { name: 'campaigns.actions.publish' });

    expect(publishButton).toBeDisabled();
    await user.type(screen.getByLabelText('campaigns.fields.confirmation'), 'PR-PRO100-INV10');
    expect(publishButton).toBeEnabled();
    await user.click(publishButton);

    await waitFor(() => {
      expect(mockPublishGrowthCampaign).toHaveBeenCalledWith(campaign.id, {
        expected_version: 3,
        reason_code: 'growth_campaign_publish',
      });
    });
  });
});

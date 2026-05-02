/**
 * PlanCard Component Tests
 *
 * Tests plan display, pricing, features, and purchase interaction:
 * - Renders plan details (name, price, duration, traffic, devices)
 * - Shows features list when available
 * - Displays "CURRENT PLAN" badge for active subscription
 * - Disables purchase button for current plan
 * - Calls onPurchase callback with plan UUID
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PlanCard } from '../PlanCard';
import type { SubscriptionPlan } from '../../lib/plan-presenter';

// Mock next-intl
vi.mock('next-intl', () => ({
  useLocale: () => 'en-US',
  useTranslations: () => (key: string) => key,
}));

describe('PlanCard', () => {
  const gib = 1024 ** 3;

  const mockPlan: SubscriptionPlan = {
    uuid: 'plan-123',
    name: 'premium',
    plan_code: 'plus',
    display_name: 'Premium',
    catalog_visibility: 'public',
    duration_days: 30,
    traffic_limit_bytes: 500 * gib,
    devices_included: 5,
    price_usd: 9.99,
    price_rub: null,
    traffic_policy: {
      mode: 'quota',
      display_label: '',
      enforcement_profile: null,
    },
    connection_modes: ['standard', 'stealth'],
    server_pool: ['premium'],
    support_sla: 'priority',
    dedicated_ip: {
      included: 0,
      eligible: true,
    },
    sale_channels: ['official_web'],
    invite_bundle: {
      count: 0,
      friend_days: 0,
      expiry_days: 0,
    },
    trial_eligible: true,
    features: {
      marketing_badge: 'Premium access',
    },
    is_active: true,
    sort_order: 10,
  };

  const createPlan = (overrides: Partial<SubscriptionPlan> = {}): SubscriptionPlan => ({
    ...mockPlan,
    ...overrides,
    traffic_policy: {
      ...mockPlan.traffic_policy,
      ...overrides.traffic_policy,
    },
    dedicated_ip: {
      ...mockPlan.dedicated_ip,
      ...overrides.dedicated_ip,
    },
    invite_bundle: {
      ...mockPlan.invite_bundle,
      ...overrides.invite_bundle,
    },
  });

  const mockOnPurchase = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Plan Details Rendering', () => {
    it('test_renders_plan_name_and_price', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Premium')).toBeInTheDocument();
      expect(screen.getByText('$9.99')).toBeInTheDocument();
      expect(screen.getByText('Premium access')).toBeInTheDocument();
    });

    it('test_formats_30_day_duration_correctly', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('per 30 days')).toBeInTheDocument();
    });

    it('test_formats_365_day_duration_correctly', () => {
      const yearlyPlan = createPlan({ duration_days: 365 });
      render(<PlanCard plan={yearlyPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('per 365 days')).toBeInTheDocument();
    });

    it('test_formats_7_day_duration_correctly', () => {
      const weeklyPlan = createPlan({ duration_days: 7 });
      render(<PlanCard plan={weeklyPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('per 7 days')).toBeInTheDocument();
    });

    it('test_formats_custom_duration_in_days', () => {
      const customPlan = createPlan({ duration_days: 45 });
      render(<PlanCard plan={customPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('per 45 days')).toBeInTheDocument();
    });

    it('test_displays_traffic_limit_in_gb', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('500 GB')).toBeInTheDocument();
    });

    it('test_displays_unlimited_traffic_when_null', () => {
      const unlimitedPlan = createPlan({
        traffic_limit_bytes: null,
        traffic_policy: {
          mode: 'fair_use',
          display_label: 'Unlimited',
          enforcement_profile: null,
        },
      });
      render(<PlanCard plan={unlimitedPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Unlimited')).toBeInTheDocument();
    });

    it('test_displays_traffic_in_tb_for_large_values', () => {
      const largePlan = createPlan({ traffic_limit_bytes: 2000 * gib });
      render(<PlanCard plan={largePlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('2 TB')).toBeInTheDocument();
    });

    it('test_displays_max_devices_when_provided', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Devices')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('test_renders_connection_modes', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Modes')).toBeInTheDocument();
      expect(screen.getAllByText('Standard + Stealth')).toHaveLength(2);
    });
  });

  describe('Highlights List', () => {
    it('test_renders_generated_plan_highlights', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('5 devices')).toBeInTheDocument();
      expect(screen.getByText('Premium pool')).toBeInTheDocument();
      expect(screen.getByText('Dedicated IP available as add-on')).toBeInTheDocument();
      expect(screen.getByText('Priority support')).toBeInTheDocument();
    });

    it('test_uses_default_marketing_badge_for_plus_plan', () => {
      const noBadgePlan = createPlan({ features: {} });
      render(<PlanCard plan={noBadgePlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Most Popular')).toBeInTheDocument();
    });

    it('test_omits_badge_when_plan_has_no_badge_rule', () => {
      const noBadgePlan = createPlan({ plan_code: 'basic', features: {} });
      render(<PlanCard plan={noBadgePlan} onPurchase={mockOnPurchase} />);

      expect(screen.queryByText('Premium access')).not.toBeInTheDocument();
      expect(screen.queryByText('Most Popular')).not.toBeInTheDocument();
    });
  });

  describe('Current Plan Badge', () => {
    it('test_displays_current_plan_badge_when_active', () => {
      render(
        <PlanCard plan={mockPlan} isCurrentPlan={true} onPurchase={mockOnPurchase} />
      );

      expect(screen.getByText('CURRENT PLAN')).toBeInTheDocument();
    });

    it('test_hides_current_plan_badge_when_not_active', () => {
      render(
        <PlanCard plan={mockPlan} isCurrentPlan={false} onPurchase={mockOnPurchase} />
      );

      expect(screen.queryByText('CURRENT PLAN')).not.toBeInTheDocument();
    });

    it('test_button_shows_active_for_current_plan', () => {
      render(
        <PlanCard plan={mockPlan} isCurrentPlan={true} onPurchase={mockOnPurchase} />
      );

      expect(screen.getByText('Current Plan')).toBeInTheDocument();
      expect(screen.queryByText('Purchase')).not.toBeInTheDocument();
    });

    it('test_button_shows_purchase_for_other_plans', () => {
      render(
        <PlanCard plan={mockPlan} isCurrentPlan={false} onPurchase={mockOnPurchase} />
      );

      expect(screen.getByText('Purchase')).toBeInTheDocument();
      expect(screen.queryByText('Current Plan')).not.toBeInTheDocument();
    });
  });

  describe('Purchase Interaction', () => {
    it('test_calls_onPurchase_with_plan_uuid_when_clicked', async () => {
      const user = userEvent.setup();

      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      const purchaseButton = screen.getByText('Purchase');
      await user.click(purchaseButton);

      expect(mockOnPurchase).toHaveBeenCalledWith('plan-123');
      expect(mockOnPurchase).toHaveBeenCalledTimes(1);
    });

    it('test_purchase_button_disabled_for_current_plan', async () => {
      const user = userEvent.setup();

      render(
        <PlanCard plan={mockPlan} isCurrentPlan={true} onPurchase={mockOnPurchase} />
      );

      const activeButton = screen.getByText('Current Plan');
      expect(activeButton).toBeDisabled();

      await user.click(activeButton);
      expect(mockOnPurchase).not.toHaveBeenCalled();
    });

    it('test_purchase_button_enabled_for_other_plans', () => {
      render(
        <PlanCard plan={mockPlan} isCurrentPlan={false} onPurchase={mockOnPurchase} />
      );

      const purchaseButton = screen.getByText('Purchase');
      expect(purchaseButton).not.toBeDisabled();
    });
  });

  describe('Free Plan Rendering', () => {
    it('test_renders_free_plan_with_zero_price', () => {
      const freePlan = createPlan({
        display_name: 'Free',
        name: 'free',
        price_usd: 0,
      });
      render(<PlanCard plan={freePlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Free')).toBeInTheDocument();
      expect(screen.getByText('$0')).toBeInTheDocument();
    });
  });
});

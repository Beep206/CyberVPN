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

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

describe('PlanCard', () => {
  const mockPlan = {
    uuid: 'plan-123',
    name: 'Premium',
    price: 9.99,
    currency: 'USD',
    durationDays: 30,
    dataLimitGb: 500,
    maxDevices: 5,
    features: ['Unlimited bandwidth', 'All servers', 'Priority support'],
    isActive: true,
  };

  const mockOnPurchase = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Plan Details Rendering', () => {
    it('test_renders_plan_name_and_price', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Premium')).toBeInTheDocument();
      expect(screen.getByText('9.99')).toBeInTheDocument();
      expect(screen.getByText('USD')).toBeInTheDocument();
    });

    it('test_formats_monthly_duration_correctly', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('1 month')).toBeInTheDocument();
    });

    it('test_formats_yearly_duration_correctly', () => {
      const yearlyPlan = { ...mockPlan, durationDays: 365 };
      render(<PlanCard plan={yearlyPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('1 year')).toBeInTheDocument();
    });

    it('test_formats_weekly_duration_correctly', () => {
      const weeklyPlan = { ...mockPlan, durationDays: 7 };
      render(<PlanCard plan={weeklyPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('1 week')).toBeInTheDocument();
    });

    it('test_formats_custom_duration_in_days', () => {
      const customPlan = { ...mockPlan, durationDays: 45 };
      render(<PlanCard plan={customPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('45 days')).toBeInTheDocument();
    });

    it('test_displays_traffic_limit_in_gb', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Traffic')).toBeInTheDocument();
      expect(screen.getByText('500 GB')).toBeInTheDocument();
    });

    it('test_displays_unlimited_traffic_when_null', () => {
      const unlimitedPlan = { ...mockPlan, dataLimitGb: null };
      render(<PlanCard plan={unlimitedPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Unlimited')).toBeInTheDocument();
    });

    it('test_displays_traffic_in_tb_for_large_values', () => {
      const largePlan = { ...mockPlan, dataLimitGb: 2000 };
      render(<PlanCard plan={largePlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('2 TB')).toBeInTheDocument();
    });

    it('test_displays_max_devices_when_provided', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Devices')).toBeInTheDocument();
      expect(screen.getByText('5')).toBeInTheDocument();
    });

    it('test_hides_devices_section_when_null', () => {
      const noDevicePlan = { ...mockPlan, maxDevices: null };
      render(<PlanCard plan={noDevicePlan} onPurchase={mockOnPurchase} />);

      expect(screen.queryByText('Devices')).not.toBeInTheDocument();
    });
  });

  describe('Features List', () => {
    it('test_renders_all_features_from_list', () => {
      render(<PlanCard plan={mockPlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Unlimited bandwidth')).toBeInTheDocument();
      expect(screen.getByText('All servers')).toBeInTheDocument();
      expect(screen.getByText('Priority support')).toBeInTheDocument();
    });

    it('test_hides_features_section_when_empty', () => {
      const noFeaturesPlan = { ...mockPlan, features: [] };
      render(<PlanCard plan={noFeaturesPlan} onPurchase={mockOnPurchase} />);

      expect(screen.queryByText('Unlimited bandwidth')).not.toBeInTheDocument();
    });

    it('test_hides_features_section_when_null', () => {
      const noFeaturesPlan = { ...mockPlan, features: null };
      render(<PlanCard plan={noFeaturesPlan} onPurchase={mockOnPurchase} />);

      expect(screen.queryByText('Unlimited bandwidth')).not.toBeInTheDocument();
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

      expect(screen.getByText('Active')).toBeInTheDocument();
      expect(screen.queryByText('Purchase')).not.toBeInTheDocument();
    });

    it('test_button_shows_purchase_for_other_plans', () => {
      render(
        <PlanCard plan={mockPlan} isCurrentPlan={false} onPurchase={mockOnPurchase} />
      );

      expect(screen.getByText('Purchase')).toBeInTheDocument();
      expect(screen.queryByText('Active')).not.toBeInTheDocument();
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

      const activeButton = screen.getByText('Active');
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
      const freePlan = { ...mockPlan, price: 0, name: 'Free' };
      render(<PlanCard plan={freePlan} onPurchase={mockOnPurchase} />);

      expect(screen.getByText('Free')).toBeInTheDocument();
      expect(screen.getByText('0')).toBeInTheDocument();
    });
  });
});

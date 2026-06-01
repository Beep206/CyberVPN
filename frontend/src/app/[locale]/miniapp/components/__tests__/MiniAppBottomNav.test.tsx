/**
 * MiniAppBottomNav Component Tests
 *
 * Tests the bottom navigation for Telegram Mini App:
 * - Tab rendering and labels
 * - Active state detection
 * - Navigation link functionality
 * - Haptic feedback on tap
 * - Telegram theme integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MiniAppBottomNav } from '../MiniAppBottomNav';
import {
  setupTelegramWebAppMock,
  cleanupTelegramWebAppMock,
} from '@/test/mocks/telegram-webapp';
import { usePathname } from '@/i18n/navigation';

const { capabilitiesMock } = vi.hoisted(() => ({
  capabilitiesMock: {
    data: {
      growth: {
        checkout_code_discounts: false,
        gift_codes: false,
        growth_hub: false,
        invites: false,
        promo_codes: false,
        referral: false,
      },
    },
  },
}));

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock next/navigation
vi.mock('@/i18n/navigation', () => ({
  usePathname: vi.fn(() => '/miniapp/home'),
  Link: ({
    href,
    onClick,
    children,
    className,
    'aria-label': ariaLabel,
    'aria-current': ariaCurrent,
  }: {
    href: string;
    onClick?: React.MouseEventHandler<HTMLAnchorElement>;
    children: React.ReactNode;
    className?: string;
    'aria-label'?: string;
    'aria-current'?: 'page' | 'step' | 'location' | 'date' | 'time' | boolean;
  }) => (
    <a
      href={href}
      onClick={onClick}
      className={className}
      aria-label={ariaLabel}
      aria-current={ariaCurrent}
    >
      {children}
    </a>
  ),
}));

vi.mock(
  '@/features/client-capabilities/useClientCapabilities',
  async (importOriginal) => {
    const actual =
      await importOriginal<
        typeof import('@/features/client-capabilities/useClientCapabilities')
      >();

    return {
      ...actual,
      useClientCapabilities: () => capabilitiesMock,
    };
  },
);

describe('MiniAppBottomNav', () => {
  let telegramMock: ReturnType<typeof setupTelegramWebAppMock>;

  beforeEach(() => {
    capabilitiesMock.data.growth.checkout_code_discounts = false;
    capabilitiesMock.data.growth.gift_codes = false;
    capabilitiesMock.data.growth.growth_hub = false;
    capabilitiesMock.data.growth.invites = false;
    capabilitiesMock.data.growth.promo_codes = false;
    capabilitiesMock.data.growth.referral = false;
    vi.mocked(usePathname).mockReturnValue('/miniapp/home');
    telegramMock = setupTelegramWebAppMock();
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('test_renders_all_navigation_items', () => {
      render(<MiniAppBottomNav />);

      expect(screen.getByLabelText('nav.home')).toBeInTheDocument();
      expect(screen.getByLabelText('nav.vpn')).toBeInTheDocument();
      expect(screen.getByLabelText('nav.plans')).toBeInTheDocument();
      expect(screen.getByLabelText('nav.wallet')).toBeInTheDocument();
      expect(screen.getByLabelText('nav.profile')).toBeInTheDocument();
      expect(screen.queryByLabelText('nav.rewards')).not.toBeInTheDocument();
    });

    it('test_renders_referral_navigation_when_growth_surface_is_enabled', () => {
      capabilitiesMock.data.growth.referral = true;

      render(<MiniAppBottomNav />);

      expect(screen.getByLabelText('nav.rewards')).toBeInTheDocument();
      expect(screen.queryByLabelText('nav.wallet')).not.toBeInTheDocument();
    });

    it('test_renders_navigation_role', () => {
      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav).toHaveAttribute('role', 'navigation');
      expect(nav).toHaveAttribute('aria-label', 'nav.bottomNav');
    });

    it('test_renders_all_tab_icons', () => {
      render(<MiniAppBottomNav />);

      const icons = document.querySelectorAll('svg');
      // 4 navigation icons
      expect(icons.length).toBeGreaterThanOrEqual(4);
    });

    it('test_renders_all_tab_labels', () => {
      render(<MiniAppBottomNav />);

      expect(screen.getByText('nav.home')).toBeInTheDocument();
      expect(screen.getByText('nav.vpn')).toBeInTheDocument();
      expect(screen.getByText('nav.plans')).toBeInTheDocument();
      expect(screen.getByText('nav.wallet')).toBeInTheDocument();
      expect(screen.getByText('nav.profile')).toBeInTheDocument();
    });
  });

  describe('Active State', () => {
    it('test_marks_home_as_active_when_on_home_route', () => {
      vi.mocked(usePathname).mockReturnValue('/miniapp/home');

      render(<MiniAppBottomNav />);

      const homeLink = screen.getByLabelText('nav.home');
      expect(homeLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_marks_root_as_home_route', () => {
      vi.mocked(usePathname).mockReturnValue('/miniapp');

      render(<MiniAppBottomNav />);

      const homeLink = screen.getByLabelText('nav.home');
      expect(homeLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_marks_plans_as_active_when_on_plans_route', () => {
      vi.mocked(usePathname).mockReturnValue('/miniapp/plans');

      render(<MiniAppBottomNav />);

      const plansLink = screen.getByLabelText('nav.plans');
      expect(plansLink).toHaveAttribute('aria-current', 'page');

      const homeLink = screen.getByLabelText('nav.home');
      expect(homeLink).not.toHaveAttribute('aria-current');
    });

    it('test_marks_vpn_as_active_when_on_vpn_route', () => {
      vi.mocked(usePathname).mockReturnValue('/miniapp/vpn');

      render(<MiniAppBottomNav />);

      const vpnLink = screen.getByLabelText('nav.vpn');
      expect(vpnLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_marks_wallet_as_active_when_on_wallet_route', () => {
      vi.mocked(usePathname).mockReturnValue('/miniapp/wallet');

      render(<MiniAppBottomNav />);

      const walletLink = screen.getByLabelText('nav.wallet');
      expect(walletLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_marks_profile_as_active_when_on_profile_route', () => {
      vi.mocked(usePathname).mockReturnValue('/miniapp/profile');

      render(<MiniAppBottomNav />);

      const profileLink = screen.getByLabelText('nav.profile');
      expect(profileLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_matches_subroutes_for_plans', () => {
      vi.mocked(usePathname).mockReturnValue('/miniapp/plans/premium');

      render(<MiniAppBottomNav />);

      const plansLink = screen.getByLabelText('nav.plans');
      expect(plansLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_matches_nested_rewards_routes_and_legacy_referral_alias', () => {
      capabilitiesMock.data.growth.referral = true;
      vi.mocked(usePathname).mockReturnValue('/miniapp/rewards/gifts');

      render(<MiniAppBottomNav />);

      const rewardsLink = screen.getByLabelText('nav.rewards');
      expect(rewardsLink).toHaveAttribute('aria-current', 'page');

      vi.mocked(usePathname).mockReturnValue('/miniapp/referral');
      render(<MiniAppBottomNav />);
      expect(screen.getAllByLabelText('nav.rewards').at(-1)).toHaveAttribute(
        'aria-current',
        'page',
      );
    });

    it('test_matches_subroutes_for_wallet', () => {
      vi.mocked(usePathname).mockReturnValue('/miniapp/wallet/transactions');

      render(<MiniAppBottomNav />);

      const walletLink = screen.getByLabelText('nav.wallet');
      expect(walletLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_matches_subroutes_for_profile', () => {
      vi.mocked(usePathname).mockReturnValue('/miniapp/profile/settings');

      render(<MiniAppBottomNav />);

      const profileLink = screen.getByLabelText('nav.profile');
      expect(profileLink).toHaveAttribute('aria-current', 'page');
    });
  });

  describe('Haptic Feedback', () => {
    it('test_triggers_haptic_selection_on_tab_click', async () => {
      const user = userEvent.setup();

      render(<MiniAppBottomNav />);

      const homeLink = screen.getByLabelText('nav.home');
      await user.click(homeLink);

      expect(telegramMock.HapticFeedback.selectionChanged).toHaveBeenCalled();
    });

    it('test_triggers_haptic_on_each_tab_click', async () => {
      const user = userEvent.setup();

      render(<MiniAppBottomNav />);

      const plansLink = screen.getByLabelText('nav.plans');
      await user.click(plansLink);

      expect(
        telegramMock.HapticFeedback.selectionChanged,
      ).toHaveBeenCalledTimes(1);

      const walletLink = screen.getByLabelText('nav.wallet');
      await user.click(walletLink);

      expect(
        telegramMock.HapticFeedback.selectionChanged,
      ).toHaveBeenCalledTimes(2);
    });
  });

  describe('Theme Integration', () => {
    it('test_uses_scoped_miniapp_nav_surface', () => {
      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav?.className).toContain('miniapp-nav');
      expect(nav?.className).toContain('border-t');
    });

    it('test_keeps_scoped_surface_when_telegram_uses_light_mode', () => {
      cleanupTelegramWebAppMock();
      setupTelegramWebAppMock({ colorScheme: 'light' });

      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav?.className).toContain('miniapp-nav');
    });

    it('test_applies_telegram_theme_params', () => {
      cleanupTelegramWebAppMock();
      setupTelegramWebAppMock({
        themeParams: {
          bg_color: '#000000',
          hint_color: '#888888',
          link_color: '#00ff00',
        },
      });

      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav).toBeInTheDocument();
    });
  });

  describe('Navigation Links', () => {
    it('test_home_link_points_to_home_route', () => {
      render(<MiniAppBottomNav />);

      const homeLink = screen.getByLabelText('nav.home');
      expect(homeLink).toHaveAttribute('href', '/miniapp/home');
    });

    it('test_plans_link_points_to_plans_route', () => {
      render(<MiniAppBottomNav />);

      const plansLink = screen.getByLabelText('nav.plans');
      expect(plansLink).toHaveAttribute('href', '/miniapp/plans');
    });

    it('test_vpn_link_points_to_vpn_route', () => {
      render(<MiniAppBottomNav />);

      const vpnLink = screen.getByLabelText('nav.vpn');
      expect(vpnLink).toHaveAttribute('href', '/miniapp/vpn');
    });

    it('test_wallet_link_points_to_wallet_route', () => {
      render(<MiniAppBottomNav />);

      const walletLink = screen.getByLabelText('nav.wallet');
      expect(walletLink).toHaveAttribute('href', '/miniapp/wallet');
    });

    it('test_profile_link_points_to_profile_route', () => {
      render(<MiniAppBottomNav />);

      const profileLink = screen.getByLabelText('nav.profile');
      expect(profileLink).toHaveAttribute('href', '/miniapp/profile');
    });

    it('test_rewards_link_points_to_rewards_route_when_growth_is_enabled', () => {
      capabilitiesMock.data.growth.referral = true;

      render(<MiniAppBottomNav />);

      const rewardsLink = screen.getByLabelText('nav.rewards');
      expect(rewardsLink).toHaveAttribute('href', '/miniapp/rewards');
    });
  });

  describe('Accessibility', () => {
    it('test_has_navigation_role_and_label', () => {
      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav).toHaveAttribute('role', 'navigation');
      expect(nav).toHaveAttribute('aria-label', 'nav.bottomNav');
    });

    it('test_all_links_have_aria_labels', () => {
      render(<MiniAppBottomNav />);

      expect(screen.getByLabelText('nav.home')).toBeInTheDocument();
      expect(screen.getByLabelText('nav.vpn')).toBeInTheDocument();
      expect(screen.getByLabelText('nav.plans')).toBeInTheDocument();
      expect(screen.getByLabelText('nav.wallet')).toBeInTheDocument();
      expect(screen.getByLabelText('nav.profile')).toBeInTheDocument();
    });

    it('test_active_link_has_aria_current_page', () => {
      vi.mocked(usePathname).mockReturnValue('/miniapp/wallet');

      render(<MiniAppBottomNav />);

      const walletLink = screen.getByLabelText('nav.wallet');
      expect(walletLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_icons_have_aria_hidden', () => {
      render(<MiniAppBottomNav />);

      const icons = document.querySelectorAll('svg');
      icons.forEach((icon) => {
        expect(icon).toHaveAttribute('aria-hidden', 'true');
      });
    });

    it('test_has_touch_manipulation_class', () => {
      render(<MiniAppBottomNav />);

      const homeLink = screen.getByLabelText('nav.home');
      expect(homeLink.className).toContain('touch-manipulation');
    });
  });

  describe('Fixed Positioning', () => {
    it('test_has_fixed_bottom_positioning', () => {
      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav?.className).toContain('fixed');
      expect(nav?.className).toContain('bottom-0');
    });

    it('test_spans_full_width', () => {
      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav?.className).toContain('left-0');
      expect(nav?.className).toContain('right-0');
    });

    it('test_has_high_z_index', () => {
      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav?.className).toContain('z-50');
    });
  });
});

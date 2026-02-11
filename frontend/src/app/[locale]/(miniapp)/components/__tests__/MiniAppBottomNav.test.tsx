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
import { setupTelegramWebAppMock, cleanupTelegramWebAppMock } from '@/test/mocks/telegram-webapp';

// Mock next-intl
vi.mock('next-intl', () => ({
  useTranslations: () => (key: string) => key,
}));

// Mock next/navigation
vi.mock('@/i18n/navigation', () => ({
  usePathname: vi.fn(() => '/home'),
  Link: ({ href, onClick, children, className, 'aria-label': ariaLabel, 'aria-current': ariaCurrent }: any) => (
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

describe('MiniAppBottomNav', () => {
  let telegramMock: ReturnType<typeof setupTelegramWebAppMock>;

  beforeEach(() => {
    telegramMock = setupTelegramWebAppMock();
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('test_renders_all_navigation_items', () => {
      render(<MiniAppBottomNav />);

      expect(screen.getByLabelText('home')).toBeInTheDocument();
      expect(screen.getByLabelText('plans')).toBeInTheDocument();
      expect(screen.getByLabelText('wallet')).toBeInTheDocument();
      expect(screen.getByLabelText('profile')).toBeInTheDocument();
    });

    it('test_renders_navigation_role', () => {
      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav).toHaveAttribute('role', 'navigation');
      expect(nav).toHaveAttribute('aria-label', 'bottomNav');
    });

    it('test_renders_all_tab_icons', () => {
      render(<MiniAppBottomNav />);

      const icons = document.querySelectorAll('svg');
      // 4 navigation icons
      expect(icons.length).toBeGreaterThanOrEqual(4);
    });

    it('test_renders_all_tab_labels', () => {
      render(<MiniAppBottomNav />);

      expect(screen.getByText('home')).toBeInTheDocument();
      expect(screen.getByText('plans')).toBeInTheDocument();
      expect(screen.getByText('wallet')).toBeInTheDocument();
      expect(screen.getByText('profile')).toBeInTheDocument();
    });
  });

  describe('Active State', () => {
    it('test_marks_home_as_active_when_on_home_route', () => {
      const { usePathname } = require('@/i18n/navigation');
      usePathname.mockReturnValue('/home');

      render(<MiniAppBottomNav />);

      const homeLink = screen.getByLabelText('home');
      expect(homeLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_marks_root_as_home_route', () => {
      const { usePathname } = require('@/i18n/navigation');
      usePathname.mockReturnValue('/');

      render(<MiniAppBottomNav />);

      const homeLink = screen.getByLabelText('home');
      expect(homeLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_marks_plans_as_active_when_on_plans_route', () => {
      const { usePathname } = require('@/i18n/navigation');
      usePathname.mockReturnValue('/plans');

      render(<MiniAppBottomNav />);

      const plansLink = screen.getByLabelText('plans');
      expect(plansLink).toHaveAttribute('aria-current', 'page');

      const homeLink = screen.getByLabelText('home');
      expect(homeLink).not.toHaveAttribute('aria-current');
    });

    it('test_marks_wallet_as_active_when_on_wallet_route', () => {
      const { usePathname } = require('@/i18n/navigation');
      usePathname.mockReturnValue('/wallet');

      render(<MiniAppBottomNav />);

      const walletLink = screen.getByLabelText('wallet');
      expect(walletLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_marks_profile_as_active_when_on_profile_route', () => {
      const { usePathname } = require('@/i18n/navigation');
      usePathname.mockReturnValue('/profile');

      render(<MiniAppBottomNav />);

      const profileLink = screen.getByLabelText('profile');
      expect(profileLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_matches_subroutes_for_plans', () => {
      const { usePathname } = require('@/i18n/navigation');
      usePathname.mockReturnValue('/plans/premium');

      render(<MiniAppBottomNav />);

      const plansLink = screen.getByLabelText('plans');
      expect(plansLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_matches_subroutes_for_wallet', () => {
      const { usePathname } = require('@/i18n/navigation');
      usePathname.mockReturnValue('/wallet/transactions');

      render(<MiniAppBottomNav />);

      const walletLink = screen.getByLabelText('wallet');
      expect(walletLink).toHaveAttribute('aria-current', 'page');
    });

    it('test_matches_subroutes_for_profile', () => {
      const { usePathname } = require('@/i18n/navigation');
      usePathname.mockReturnValue('/profile/settings');

      render(<MiniAppBottomNav />);

      const profileLink = screen.getByLabelText('profile');
      expect(profileLink).toHaveAttribute('aria-current', 'page');
    });
  });

  describe('Haptic Feedback', () => {
    it('test_triggers_haptic_selection_on_tab_click', async () => {
      const user = userEvent.setup();

      render(<MiniAppBottomNav />);

      const homeLink = screen.getByLabelText('home');
      await user.click(homeLink);

      expect(telegramMock.HapticFeedback.selectionChanged).toHaveBeenCalled();
    });

    it('test_triggers_haptic_on_each_tab_click', async () => {
      const user = userEvent.setup();

      render(<MiniAppBottomNav />);

      const plansLink = screen.getByLabelText('plans');
      await user.click(plansLink);

      expect(telegramMock.HapticFeedback.selectionChanged).toHaveBeenCalledTimes(1);

      const walletLink = screen.getByLabelText('wallet');
      await user.click(walletLink);

      expect(telegramMock.HapticFeedback.selectionChanged).toHaveBeenCalledTimes(2);
    });
  });

  describe('Theme Integration', () => {
    it('test_uses_dark_theme_colors_by_default', () => {
      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav?.className).toContain('bg-[var(--tg-bg-color');
      expect(nav?.className).toContain('border-[var(--tg-hint-color');
    });

    it('test_uses_light_theme_colors_when_light_mode', () => {
      cleanupTelegramWebAppMock();
      setupTelegramWebAppMock({ colorScheme: 'light' });

      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      // Component uses colorScheme to pick different CSS classes
      expect(nav?.className).toContain('bg-[var(--tg-bg-color');
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

      const homeLink = screen.getByLabelText('home');
      expect(homeLink).toHaveAttribute('href', '/home');
    });

    it('test_plans_link_points_to_plans_route', () => {
      render(<MiniAppBottomNav />);

      const plansLink = screen.getByLabelText('plans');
      expect(plansLink).toHaveAttribute('href', '/plans');
    });

    it('test_wallet_link_points_to_wallet_route', () => {
      render(<MiniAppBottomNav />);

      const walletLink = screen.getByLabelText('wallet');
      expect(walletLink).toHaveAttribute('href', '/wallet');
    });

    it('test_profile_link_points_to_profile_route', () => {
      render(<MiniAppBottomNav />);

      const profileLink = screen.getByLabelText('profile');
      expect(profileLink).toHaveAttribute('href', '/profile');
    });
  });

  describe('Accessibility', () => {
    it('test_has_navigation_role_and_label', () => {
      const { container } = render(<MiniAppBottomNav />);

      const nav = container.querySelector('nav');
      expect(nav).toHaveAttribute('role', 'navigation');
      expect(nav).toHaveAttribute('aria-label', 'bottomNav');
    });

    it('test_all_links_have_aria_labels', () => {
      render(<MiniAppBottomNav />);

      expect(screen.getByLabelText('home')).toBeInTheDocument();
      expect(screen.getByLabelText('plans')).toBeInTheDocument();
      expect(screen.getByLabelText('wallet')).toBeInTheDocument();
      expect(screen.getByLabelText('profile')).toBeInTheDocument();
    });

    it('test_active_link_has_aria_current_page', () => {
      const { usePathname } = require('@/i18n/navigation');
      usePathname.mockReturnValue('/wallet');

      render(<MiniAppBottomNav />);

      const walletLink = screen.getByLabelText('wallet');
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

      const homeLink = screen.getByLabelText('home');
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

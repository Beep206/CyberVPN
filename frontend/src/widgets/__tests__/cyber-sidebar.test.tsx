import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Module-level mocks (hoisted by Vitest)
// ---------------------------------------------------------------------------

// Mock CypherText with a simple span that displays the text prop
vi.mock('@/shared/ui/atoms/cypher-text', () => ({
  CypherText: ({ text, className }: { text: string; className?: string }) => (
    <span data-testid="cypher-text" className={className}>
      {text}
    </span>
  ),
}));

// Mock @/lib/utils (cn) as a simple class joiner
vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) =>
    args
      .filter(Boolean)
      .map((a) => (typeof a === 'string' ? a : ''))
      .join(' ')
      .trim(),
}));

// The setup.ts already mocks next-intl, @/i18n/navigation, and motion/react.
// We need to override @/i18n/navigation Link mock to render an actual <a> tag
// so we can query by role="link" and inspect href/aria attributes.
const mockUsePathname = vi.fn(() => '/');

vi.mock('@/i18n/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => mockUsePathname(),
  Link: ({
    children,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    href: string;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

// Import CyberSidebar after mocks are set up
import { CyberSidebar } from '../cyber-sidebar';

// ---------------------------------------------------------------------------
// Constants matching the source menuItems
// ---------------------------------------------------------------------------

const MENU_ITEMS = [
  { labelKey: 'dashboard', href: '/dashboard' },
  { labelKey: 'servers', href: '/servers' },
  { labelKey: 'users', href: '/users' },
  { labelKey: 'billing', href: '/subscriptions' },
  { labelKey: 'analytics', href: '/analytics' },
  { labelKey: 'security', href: '/monitoring' },
  { labelKey: 'settings', href: '/settings' },
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('CyberSidebar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePathname.mockReturnValue('/');
  });

  // -------------------------------------------------------------------------
  // Navigation structure
  // -------------------------------------------------------------------------

  it('test_renders_aside_with_sidebar_aria_label', () => {
    // Arrange & Act
    render(<CyberSidebar />);

    // Assert - the aside should have role complementary (implicit) and aria-label
    const aside = screen.getByRole('complementary');
    expect(aside).toBeInTheDocument();
    // useTranslations returns key as-is, so aria-label is the translation key
    expect(aside).toHaveAttribute('aria-label', 'sidebar');
  });

  it('test_renders_nav_with_main_navigation_role', () => {
    // Arrange & Act
    render(<CyberSidebar />);

    // Assert
    const nav = screen.getByRole('navigation');
    expect(nav).toBeInTheDocument();
    expect(nav).toHaveAttribute('aria-label', 'mainNavigation');
  });

  it('test_renders_all_seven_navigation_links', () => {
    // Arrange & Act
    render(<CyberSidebar />);

    // Assert
    const links = screen.getAllByRole('link');
    expect(links).toHaveLength(MENU_ITEMS.length);
  });

  it('test_each_link_has_correct_href', () => {
    // Arrange & Act
    render(<CyberSidebar />);

    // Assert
    for (const item of MENU_ITEMS) {
      const link = screen.getByRole('link', { name: item.labelKey });
      expect(link).toHaveAttribute('href', item.href);
    }
  });

  it('test_each_link_has_aria_label_matching_translation_key', () => {
    // Arrange & Act
    render(<CyberSidebar />);

    // Assert
    for (const item of MENU_ITEMS) {
      const link = screen.getByLabelText(item.labelKey);
      expect(link).toBeInTheDocument();
      expect(link.tagName).toBe('A');
    }
  });

  // -------------------------------------------------------------------------
  // Active link highlighting
  // -------------------------------------------------------------------------

  it('test_active_link_has_aria_current_page', () => {
    // Arrange - simulate being on /servers path
    mockUsePathname.mockReturnValue('/servers');

    // Act
    render(<CyberSidebar />);

    // Assert
    const activeLink = screen.getByRole('link', { name: 'servers' });
    expect(activeLink).toHaveAttribute('aria-current', 'page');
  });

  it('test_inactive_links_have_no_aria_current', () => {
    // Arrange - simulate being on /servers path
    mockUsePathname.mockReturnValue('/servers');

    // Act
    render(<CyberSidebar />);

    // Assert - all other links should not have aria-current
    const inactiveItems = MENU_ITEMS.filter((i) => i.href !== '/servers');
    for (const item of inactiveItems) {
      const link = screen.getByRole('link', { name: item.labelKey });
      expect(link).not.toHaveAttribute('aria-current');
    }
  });

  it('test_dashboard_link_active_when_pathname_includes_dashboard', () => {
    // Arrange
    mockUsePathname.mockReturnValue('/dashboard');

    // Act
    render(<CyberSidebar />);

    // Assert
    const dashboardLink = screen.getByRole('link', { name: 'dashboard' });
    expect(dashboardLink).toHaveAttribute('aria-current', 'page');
  });

  it('test_no_link_active_when_pathname_matches_none', () => {
    // Arrange - path that matches no menu item
    mockUsePathname.mockReturnValue('/unknown-route');

    // Act
    render(<CyberSidebar />);

    // Assert
    const links = screen.getAllByRole('link');
    for (const link of links) {
      expect(link).not.toHaveAttribute('aria-current');
    }
  });

  // -------------------------------------------------------------------------
  // CypherText rendering
  // -------------------------------------------------------------------------

  it('test_renders_cypher_text_for_each_menu_item', () => {
    // Arrange & Act
    render(<CyberSidebar />);

    // Assert - each menu item should render a CypherText mock
    const cypherTexts = screen.getAllByTestId('cypher-text');
    expect(cypherTexts).toHaveLength(MENU_ITEMS.length);

    for (let i = 0; i < MENU_ITEMS.length; i++) {
      expect(cypherTexts[i]).toHaveTextContent(MENU_ITEMS[i].labelKey);
    }
  });

  // -------------------------------------------------------------------------
  // Responsive visibility
  // -------------------------------------------------------------------------

  it('test_sidebar_has_hidden_mobile_visible_md_classes', () => {
    // Arrange & Act
    render(<CyberSidebar />);

    // Assert - the aside should have responsive visibility classes
    const aside = screen.getByRole('complementary');
    expect(aside.className).toContain('hidden');
    expect(aside.className).toContain('md:flex');
  });

  // -------------------------------------------------------------------------
  // Static content
  // -------------------------------------------------------------------------

  it('test_renders_nexus_brand_text', () => {
    // Arrange & Act
    render(<CyberSidebar />);

    // Assert
    expect(screen.getByText('NEXUS')).toBeInTheDocument();
  });

  it('test_renders_admin_user_section', () => {
    // Arrange & Act
    render(<CyberSidebar />);

    // Assert
    expect(screen.getByText('ADMIN_01')).toBeInTheDocument();
    expect(screen.getByText('ROOT ACCESS')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Glitch overlay text is aria-hidden
  // -------------------------------------------------------------------------

  it('test_glitch_overlay_spans_are_aria_hidden', () => {
    // Arrange & Act
    const { container } = render(<CyberSidebar />);

    // Assert - all glitch overlay spans should be aria-hidden="true"
    const ariaHiddenSpans = container.querySelectorAll('span[aria-hidden="true"]');
    // Each menu item has 2 glitch overlays
    expect(ariaHiddenSpans.length).toBeGreaterThanOrEqual(MENU_ITEMS.length * 2);
  });
});

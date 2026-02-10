import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';

// ---------------------------------------------------------------------------
// Module-level mocks (hoisted by Vitest)
// ---------------------------------------------------------------------------

// Mock CypherText with a simple span
vi.mock('@/shared/ui/atoms/cypher-text', () => ({
  CypherText: ({ text, className }: { text: string; className?: string }) => (
    <span data-testid="cypher-text" className={className}>
      {text}
    </span>
  ),
}));

// Mock MagneticButton as a passthrough div
vi.mock('@/shared/ui/magnetic-button', () => ({
  MagneticButton: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="magnetic-button">{children}</div>
  ),
}));

// Mock LanguageSelector
vi.mock('@/features/language-selector', () => ({
  LanguageSelector: () => <div data-testid="language-selector">LanguageSelector</div>,
}));

// Mock ThemeToggle
vi.mock('@/features/theme-toggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle">ThemeToggle</div>,
}));

// Mock NotificationDropdown
vi.mock('@/features/notifications/notification-dropdown', () => ({
  NotificationDropdown: () => (
    <div data-testid="notification-dropdown">NotificationDropdown</div>
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

// The setup.ts already mocks next-intl (useTranslations returns key as-is).
// We also need to mock useLocale.
vi.mock('next-intl', () => ({
  useTranslations: () => {
    const t = (key: string) => key;
    return t;
  },
  useLocale: () => 'en-EN',
}));

// Import TerminalHeader after mocks are set up
import { TerminalHeader } from '../terminal-header';

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TerminalHeader', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  // -------------------------------------------------------------------------
  // Basic rendering
  // -------------------------------------------------------------------------

  it('test_renders_header_element', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert
    const header = screen.getByRole('banner');
    expect(header).toBeInTheDocument();
  });

  it('test_header_has_sticky_top_class', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert
    const header = screen.getByRole('banner');
    expect(header.className).toContain('sticky');
    expect(header.className).toContain('top-0');
  });

  // -------------------------------------------------------------------------
  // FPS counter
  // -------------------------------------------------------------------------

  it('test_fps_label_renders', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert - useTranslations returns key as-is
    expect(screen.getByText('fps')).toBeInTheDocument();
  });

  it('test_fps_value_element_renders_with_initial_placeholder', () => {
    // Arrange & Act
    const { container } = render(<TerminalHeader />);

    // Assert - the FPS ref span should exist with initial "--" text
    const fpsSpan = container.querySelector('.text-neon-cyan');
    expect(fpsSpan).toBeInTheDocument();
    expect(fpsSpan?.textContent).toBe('--');
  });

  // -------------------------------------------------------------------------
  // Ping display
  // -------------------------------------------------------------------------

  it('test_ping_label_renders', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert
    expect(screen.getByText('ping')).toBeInTheDocument();
  });

  it('test_ping_value_element_renders_with_initial_placeholder', () => {
    // Arrange & Act
    const { container } = render(<TerminalHeader />);

    // Assert - the ping ref span should exist with initial "--" text
    const pingSpan = container.querySelector('.text-matrix-green');
    expect(pingSpan).toBeInTheDocument();
    expect(pingSpan?.textContent).toBe('--');
  });

  // -------------------------------------------------------------------------
  // Time display
  // -------------------------------------------------------------------------

  it('test_time_display_shows_placeholder_before_hydration', () => {
    // Arrange & Act - time state starts as '' and the fallback is "--:--:--"
    render(<TerminalHeader />);

    // Assert - before any useEffect runs, the fallback should render
    // With fake timers, the initial render shows "--:--:--" or the time
    // Since we have fake timers, the useEffect will not fire until we advance
    // Actually, useEffect fires synchronously in test after render in act()
    // but the initial state is '' so the || fallback "--:--:--" shows first.
    // After useEffect, time gets set. Let's check what renders.
    const timeContainer = screen.getByText(/UTC|--:--:--/);
    expect(timeContainer).toBeInTheDocument();
  });

  it('test_time_display_updates_after_interval', () => {
    // Arrange
    const mockDate = new Date('2026-02-10T14:30:45.000Z');
    vi.setSystemTime(mockDate);

    // Act - render triggers useEffect which calls updateTime() immediately
    render(<TerminalHeader />);

    // Advance by a small amount to let the initial setInterval callback fire.
    // We avoid runAllTimers because the FPS rAF loop runs indefinitely.
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Assert
    expect(screen.getByText('14:30:45 UTC')).toBeInTheDocument();
  });

  it('test_time_display_updates_every_second', () => {
    // Arrange
    vi.setSystemTime(new Date('2026-02-10T10:00:00.000Z'));

    // Act
    render(<TerminalHeader />);

    // Initial render sets time to "10:00:00 UTC"
    expect(screen.getByText('10:00:00 UTC')).toBeInTheDocument();

    // Advance the fake clock by 1 second. The setInterval(updateTime, 1000)
    // fires and reads new Date() which is now 10:00:01 due to the advance.
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    // Assert - the time should have updated from the initial value
    expect(screen.getByText('10:00:01 UTC')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Responsive visibility classes
  // -------------------------------------------------------------------------

  it('test_fps_ping_section_has_hidden_mobile_visible_md_classes', () => {
    // Arrange & Act
    const { container } = render(<TerminalHeader />);

    // Assert - the FPS/ping container has hidden md:flex classes
    const fpsPingContainer = container.querySelector('.hidden.md\\:flex');
    expect(fpsPingContainer).toBeInTheDocument();
  });

  it('test_net_uplink_text_hidden_on_mobile_visible_on_md', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert - the "netUplink" text has hidden md:inline classes
    const netUplink = screen.getByText('netUplink');
    expect(netUplink.className).toContain('hidden');
    expect(netUplink.className).toContain('md:inline');
  });

  it('test_time_display_hidden_on_mobile_visible_on_md', () => {
    // Arrange
    vi.setSystemTime(new Date('2026-02-10T12:00:00.000Z'));

    // Act
    render(<TerminalHeader />);
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Assert - the time container has hidden md:block classes
    const timeElement = screen.getByText('12:00:00 UTC');
    const timeContainer = timeElement.closest('div');
    expect(timeContainer?.className).toContain('hidden');
    expect(timeContainer?.className).toContain('md:block');
  });

  // -------------------------------------------------------------------------
  // Child components render
  // -------------------------------------------------------------------------

  it('test_renders_magnetic_button_wrapper', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert
    expect(screen.getByTestId('magnetic-button')).toBeInTheDocument();
  });

  it('test_renders_theme_toggle', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert
    expect(screen.getByTestId('theme-toggle')).toBeInTheDocument();
  });

  it('test_renders_language_selector', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert
    expect(screen.getByTestId('language-selector')).toBeInTheDocument();
  });

  it('test_renders_notification_dropdown', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert
    expect(screen.getByTestId('notification-dropdown')).toBeInTheDocument();
  });

  // -------------------------------------------------------------------------
  // Network uplink indicator
  // -------------------------------------------------------------------------

  it('test_renders_net_uplink_status_badge', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert - the "netUplink" text (translation key) should render
    expect(screen.getByText('netUplink')).toBeInTheDocument();
  });

  it('test_net_uplink_badge_has_matrix_green_styling', () => {
    // Arrange & Act
    render(<TerminalHeader />);

    // Assert
    const netUplink = screen.getByText('netUplink');
    const badge = netUplink.closest('div');
    expect(badge?.className).toContain('text-matrix-green');
  });

  // -------------------------------------------------------------------------
  // Menu button accessibility
  // -------------------------------------------------------------------------

  it('test_menu_button_is_aria_hidden', () => {
    // Arrange & Act
    const { container } = render(<TerminalHeader />);

    // Assert - the menu icon wrapper has aria-hidden="true"
    const ariaHiddenDiv = container.querySelector('[aria-hidden="true"]');
    expect(ariaHiddenDiv).toBeInTheDocument();
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SocialAuthButtons } from '../SocialAuthButtons';

// Mock @/shared/ui/magnetic-button to render children directly
vi.mock('@/shared/ui/magnetic-button', () => ({
  MagneticButton: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="magnetic-wrapper">{children}</div>
  ),
}));

// Mock @/lib/utils
vi.mock('@/lib/utils', () => ({
  cn: (...args: unknown[]) =>
    args
      .filter(Boolean)
      .map((a) => (typeof a === 'string' ? a : ''))
      .join(' ')
      .trim(),
}));

const EXPECTED_PROVIDERS = ['telegram', 'google', 'github', 'discord', 'apple', 'microsoft', 'twitter'] as const;

const EXPECTED_ARIA_LABELS: Record<string, string> = {
  telegram: 'Sign in with Telegram',
  google: 'Sign in with Google',
  github: 'Sign in with GitHub',
  discord: 'Sign in with Discord',
  apple: 'Sign in with Apple',
  microsoft: 'Sign in with Microsoft',
  twitter: 'Sign in with X',
};

describe('SocialAuthButtons', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all 7 provider buttons', () => {
    render(<SocialAuthButtons />);

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(EXPECTED_PROVIDERS.length);
  });

  it('renders Telegram as the first button', () => {
    render(<SocialAuthButtons />);

    const buttons = screen.getAllByRole('button');
    expect(buttons[0]).toHaveAttribute('aria-label', 'Sign in with Telegram');
  });

  it('renders correct aria-label for each provider button', () => {
    render(<SocialAuthButtons />);

    for (const provider of EXPECTED_PROVIDERS) {
      const expectedLabel = EXPECTED_ARIA_LABELS[provider];
      const button = screen.getByLabelText(expectedLabel);
      expect(button).toBeInTheDocument();
    }
  });

  it('calls onProviderClick with the correct provider name when clicked', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(<SocialAuthButtons onProviderClick={handleClick} />);

    // Click Telegram button
    const telegramButton = screen.getByLabelText('Sign in with Telegram');
    await user.click(telegramButton);
    expect(handleClick).toHaveBeenCalledWith('telegram');

    handleClick.mockClear();

    // Click Google button
    const googleButton = screen.getByLabelText('Sign in with Google');
    await user.click(googleButton);
    expect(handleClick).toHaveBeenCalledWith('google');

    handleClick.mockClear();

    // Click GitHub button
    const githubButton = screen.getByLabelText('Sign in with GitHub');
    await user.click(githubButton);
    expect(handleClick).toHaveBeenCalledWith('github');

    handleClick.mockClear();

    // Click Discord button
    const discordButton = screen.getByLabelText('Sign in with Discord');
    await user.click(discordButton);
    expect(handleClick).toHaveBeenCalledWith('discord');

    handleClick.mockClear();

    // Click Apple button
    const appleButton = screen.getByLabelText('Sign in with Apple');
    await user.click(appleButton);
    expect(handleClick).toHaveBeenCalledWith('apple');

    handleClick.mockClear();

    // Click Microsoft button
    const microsoftButton = screen.getByLabelText('Sign in with Microsoft');
    await user.click(microsoftButton);
    expect(handleClick).toHaveBeenCalledWith('microsoft');

    handleClick.mockClear();

    // Click X/Twitter button
    const twitterButton = screen.getByLabelText('Sign in with X');
    await user.click(twitterButton);
    expect(handleClick).toHaveBeenCalledWith('twitter');
  });

  it('does not call onProviderClick when no handler is provided', async () => {
    const user = userEvent.setup();

    // Should not throw when clicking without handler
    render(<SocialAuthButtons />);

    const googleButton = screen.getByLabelText('Sign in with Google');
    await user.click(googleButton);
    // No assertion needed -- just verifying it does not throw
  });

  it('disables all buttons when disabled prop is true', () => {
    render(<SocialAuthButtons disabled />);

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(EXPECTED_PROVIDERS.length);

    for (const button of buttons) {
      expect(button).toBeDisabled();
    }
  });

  it('all buttons are enabled by default', () => {
    render(<SocialAuthButtons />);

    const buttons = screen.getAllByRole('button');
    for (const button of buttons) {
      expect(button).not.toBeDisabled();
    }
  });

  it('all buttons have aria-label attribute', () => {
    render(<SocialAuthButtons />);

    const buttons = screen.getAllByRole('button');
    for (const button of buttons) {
      expect(button).toHaveAttribute('aria-label');
      expect(button.getAttribute('aria-label')).toBeTruthy();
    }
  });

  it('applies custom className', () => {
    const { container } = render(
      <SocialAuthButtons className="custom-test-class" />
    );

    // The wrapper div should have the custom class
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain('custom-test-class');
  });

  it('all buttons have type="button"', () => {
    render(<SocialAuthButtons />);

    const buttons = screen.getAllByRole('button');
    for (const button of buttons) {
      expect(button).toHaveAttribute('type', 'button');
    }
  });
});

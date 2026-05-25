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

const EXPECTED_PROVIDERS = ['google', 'github', 'telegram'] as const;

const EXPECTED_ARIA_LABELS: Record<string, string> = {
  telegram: 'Sign in with Telegram',
  google: 'Sign in with Google',
  github: 'Sign in with GitHub',
};

describe('SocialAuthButtons', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders only the public S2 provider buttons', () => {
    render(<SocialAuthButtons />);

    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(EXPECTED_PROVIDERS.length);
  });

  it('renders public S2 provider buttons in the approved order', () => {
    render(<SocialAuthButtons />);

    const buttons = screen.getAllByRole('button');
    expect(buttons.map((button) => button.getAttribute('data-provider'))).toEqual([
      'google',
      'github',
      'telegram',
    ]);
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

  it('does not render disabled or non-public providers', () => {
    render(<SocialAuthButtons />);

    expect(screen.queryByLabelText('Sign in with Apple')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Sign in with Discord')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Sign in with Facebook')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Sign in with Microsoft')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Sign in with X')).not.toBeInTheDocument();
  });
});

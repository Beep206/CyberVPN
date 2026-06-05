import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { CyberInput } from '../CyberInput';

describe('CyberInput', () => {
  it('keeps password controls mobile-safe and keyboard reachable', async () => {
    const user = userEvent.setup();

    render(
      <CyberInput
        label="Password"
        prefix="pass"
        type="password"
        placeholder="Password"
      />,
    );

    const input = screen.getByLabelText('Password');
    const revealButton = screen.getByRole('button', { name: 'Show password' });
    const inputWrapper = input.parentElement;

    expect(inputWrapper?.className).toContain('min-w-0');
    expect(inputWrapper?.className).toContain('focus-within:ring-2');
    expect(input.className).toContain('min-w-0');
    expect(input.className).toContain('focus-visible:shadow-[inset_0_-2px_0_var(--color-neon-cyan)]');
    expect(revealButton.className).toContain('h-11');
    expect(revealButton.className).toContain('w-11');
    expect(revealButton.className).toContain('shrink-0');
    expect(revealButton).not.toHaveAttribute('tabindex', '-1');

    await user.click(revealButton);

    await waitFor(() => {
      expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'text');
      expect(screen.getByRole('button', { name: 'Hide password' })).toBeInTheDocument();
    });
  });
});

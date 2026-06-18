import { useState } from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CyberOtpInput, normalizeOtpValue } from '../CyberOtpInput';

function ControlledOtpInput({
  onComplete,
  onEnter,
  disabled = false,
}: {
  onComplete?: (value: string) => void;
  onEnter?: () => void;
  disabled?: boolean;
}) {
  const [value, setValue] = useState('');

  return (
    <CyberOtpInput
      value={value}
      onChange={setValue}
      onComplete={onComplete}
      disabled={disabled}
      ariaLabel="Authenticator code"
      onEnter={onEnter}
    />
  );
}

describe('CyberOtpInput', () => {
  it('normalizes formatted codes into six separate slots', async () => {
    const onComplete = vi.fn();

    render(<ControlledOtpInput onComplete={onComplete} />);

    expect(normalizeOtpValue('123-456')).toBe('123456');
    expect(normalizeOtpValue('12a34b567')).toBe('123456');

    const input = screen.getByLabelText('Authenticator code');
    fireEvent.change(input, { target: { value: normalizeOtpValue('123-456') } });

    await waitFor(() => {
      expect(screen.getByLabelText('Authenticator code')).toHaveValue('123456');
      expect(onComplete).toHaveBeenCalledWith('123456');
    });

    for (const digit of ['1', '2', '3', '4', '5', '6']) {
      expect(screen.getByText(digit)).toBeInTheDocument();
    }
  });

  it('keeps typed values digit-only and caps at six cells', async () => {
    render(<ControlledOtpInput />);

    const input = screen.getByLabelText('Authenticator code');
    fireEvent.change(input, { target: { value: '1234567' } });

    await waitFor(() => {
      expect(screen.getByLabelText('Authenticator code')).toHaveValue('123456');
    });
  });

  it('supports disabled and enter-key modal flows', async () => {
    const onEnter = vi.fn();
    const { rerender } = render(<ControlledOtpInput onEnter={onEnter} />);

    const input = screen.getByLabelText('Authenticator code');
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(onEnter).toHaveBeenCalledTimes(1);

    rerender(<ControlledOtpInput disabled />);
    expect(screen.getByLabelText('Authenticator code')).toBeDisabled();
  });
});

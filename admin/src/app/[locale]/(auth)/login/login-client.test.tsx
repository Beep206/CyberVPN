import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { LoginClient } from './login-client';

describe('Admin LoginClient passkey UX', () => {
  it('renders explicit passkey action and WebAuthn autocomplete anchor', () => {
    render(<LoginClient />);

    expect(screen.getByRole('button', { name: 'passkeyButton' })).toBeInTheDocument();
    expect(screen.getByLabelText('emailLabel')).toHaveAttribute(
      'autocomplete',
      'username webauthn',
    );
  });
});

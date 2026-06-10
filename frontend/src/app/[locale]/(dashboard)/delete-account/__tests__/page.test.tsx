import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import DeleteAccountPage from '../page';

vi.mock('@/widgets/delete-account/delete-account-client', () => ({
  DeleteAccountClient: () => <section data-testid="delete-account-client" />,
}));

describe('dashboard delete-account page', () => {
  it('renders the delete account surface inside the dashboard page frame', () => {
    render(<DeleteAccountPage />);

    expect(screen.getByTestId('delete-account-client')).toBeInTheDocument();
  });
});

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LinkedAccountsSection } from '../LinkedAccountsSection';

// Mock useUser from auth store
const mockUseUser = vi.fn();
vi.mock('@/stores/auth-store', () => ({
  useUser: () => mockUseUser(),
}));

// Mock authApi
const mockTelegramLinkAuthorize = vi.fn();
const mockTelegramLinkCallback = vi.fn();
const mockUnlinkProvider = vi.fn();
vi.mock('@/lib/api/auth', () => ({
  authApi: {
    telegramLinkAuthorize: (...args: unknown[]) => mockTelegramLinkAuthorize(...args),
    telegramLinkCallback: (...args: unknown[]) => mockTelegramLinkCallback(...args),
    unlinkProvider: (...args: unknown[]) => mockUnlinkProvider(...args),
  },
}));

// Mock Modal component
vi.mock('@/shared/ui/modal', () => ({
  Modal: ({
    isOpen,
    children,
    onClose,
  }: {
    isOpen: boolean;
    children: React.ReactNode;
    title: string;
    onClose: () => void;
  }) =>
    isOpen ? (
      <div data-testid="modal" onClick={onClose}>
        {children}
      </div>
    ) : null,
}));

const USER_LINKED_TELEGRAM = {
  id: 'user-1',
  email: 'test@example.com',
  username: 'testuser',
  is_email_verified: true,
  telegram_id: 'tg_user_123',
};

const USER_NOT_LINKED = {
  id: 'user-1',
  email: 'test@example.com',
  username: 'testuser',
  is_email_verified: true,
  telegram_id: null,
};

const USER_TELEGRAM_ONLY = {
  id: 'user-1',
  email: '',
  username: 'testuser',
  is_email_verified: false,
  telegram_id: 'tg_user_123',
};

describe('LinkedAccountsSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // -- Rendering tests (4dux) --

  it('renders section heading', () => {
    mockUseUser.mockReturnValue(USER_NOT_LINKED);
    render(<LinkedAccountsSection />);

    expect(screen.getByText('linkedAccounts')).toBeInTheDocument();
  });

  it('renders Telegram provider name', () => {
    mockUseUser.mockReturnValue(USER_NOT_LINKED);
    render(<LinkedAccountsSection />);

    expect(screen.getByText('Telegram')).toBeInTheDocument();
  });

  it('shows "Not linked" when Telegram is not linked', () => {
    mockUseUser.mockReturnValue(USER_NOT_LINKED);
    render(<LinkedAccountsSection />);

    expect(screen.getByText('Not linked')).toBeInTheDocument();
  });

  it('shows "Link Telegram" button when not linked', () => {
    mockUseUser.mockReturnValue(USER_NOT_LINKED);
    render(<LinkedAccountsSection />);

    const linkButton = screen.getByRole('button', { name: 'linkTelegram' });
    expect(linkButton).toBeInTheDocument();
    expect(linkButton).not.toBeDisabled();
  });

  it('shows linked username when Telegram is linked', () => {
    mockUseUser.mockReturnValue(USER_LINKED_TELEGRAM);
    render(<LinkedAccountsSection />);

    // The i18n mock returns the key, so we expect the key with params
    expect(screen.queryByText('Not linked')).not.toBeInTheDocument();
  });

  it('shows Unlink button when Telegram is linked and has alternative login', () => {
    mockUseUser.mockReturnValue(USER_LINKED_TELEGRAM);
    render(<LinkedAccountsSection />);

    const unlinkButton = screen.getByRole('button', { name: 'unlinkTelegram' });
    expect(unlinkButton).toBeInTheDocument();
    expect(unlinkButton).not.toBeDisabled();
  });

  it('disables Unlink button when Telegram is only login method', () => {
    mockUseUser.mockReturnValue(USER_TELEGRAM_ONLY);
    render(<LinkedAccountsSection />);

    const unlinkButton = screen.getByRole('button', { name: 'unlinkTelegram' });
    expect(unlinkButton).toBeDisabled();
  });

  it('shows "cannot unlink" message when Telegram is only login method', () => {
    mockUseUser.mockReturnValue(USER_TELEGRAM_ONLY);
    render(<LinkedAccountsSection />);

    expect(screen.getByText('cantUnlinkOnly')).toBeInTheDocument();
  });

  it('does not show "cannot unlink" message when alternative login exists', () => {
    mockUseUser.mockReturnValue(USER_LINKED_TELEGRAM);
    render(<LinkedAccountsSection />);

    expect(screen.queryByText('cantUnlinkOnly')).not.toBeInTheDocument();
  });

  // -- Link/Unlink flow tests (36bp) --

  it('opens confirmation dialog when Unlink button is clicked', async () => {
    const user = userEvent.setup();
    mockUseUser.mockReturnValue(USER_LINKED_TELEGRAM);
    render(<LinkedAccountsSection />);

    const unlinkButton = screen.getByRole('button', { name: 'unlinkTelegram' });
    await user.click(unlinkButton);

    // Modal should be visible
    expect(screen.getByTestId('modal')).toBeInTheDocument();
    expect(screen.getByText('unlinkConfirm')).toBeInTheDocument();
  });

  it('closes confirmation dialog when Cancel is clicked', async () => {
    const user = userEvent.setup();
    mockUseUser.mockReturnValue(USER_LINKED_TELEGRAM);
    render(<LinkedAccountsSection />);

    // Open dialog
    const unlinkButton = screen.getByRole('button', { name: 'unlinkTelegram' });
    await user.click(unlinkButton);
    expect(screen.getByTestId('modal')).toBeInTheDocument();

    // Click Cancel
    const cancelButton = screen.getByRole('button', { name: 'Cancel' });
    await user.click(cancelButton);

    expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
  });

  it('calls unlinkProvider API when unlink is confirmed', async () => {
    const user = userEvent.setup();
    mockUseUser.mockReturnValue(USER_LINKED_TELEGRAM);
    mockUnlinkProvider.mockResolvedValue({ data: { status: 'unlinked', provider: 'telegram' } });
    render(<LinkedAccountsSection />);

    // Open dialog
    await user.click(screen.getByRole('button', { name: 'unlinkTelegram' }));

    // Confirm unlink (second button with unlinkTelegram label inside modal)
    const confirmButtons = screen.getAllByRole('button', { name: 'unlinkTelegram' });
    // The confirm button is inside the modal
    const confirmButton = confirmButtons[confirmButtons.length - 1];
    await user.click(confirmButton);

    expect(mockUnlinkProvider).toHaveBeenCalledWith('telegram');
  });

  it('shows error message on unlink API failure', async () => {
    const user = userEvent.setup();
    mockUseUser.mockReturnValue(USER_LINKED_TELEGRAM);
    mockUnlinkProvider.mockRejectedValue({
      response: { data: { detail: 'Cannot unlink provider' } },
    });
    render(<LinkedAccountsSection />);

    // Open dialog and confirm
    await user.click(screen.getByRole('button', { name: 'unlinkTelegram' }));
    const confirmButtons = screen.getAllByRole('button', { name: 'unlinkTelegram' });
    await user.click(confirmButtons[confirmButtons.length - 1]);

    // Wait for error to appear
    expect(await screen.findByText('Cannot unlink provider')).toBeInTheDocument();
  });

  it('does not show Link or Unlink buttons when user is null', () => {
    mockUseUser.mockReturnValue(null);
    render(<LinkedAccountsSection />);

    // Section heading should still render
    expect(screen.getByText('linkedAccounts')).toBeInTheDocument();
    // Link button should be shown (not linked state)
    expect(screen.getByRole('button', { name: 'linkTelegram' })).toBeInTheDocument();
  });
});

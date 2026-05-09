import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { CustomerDetail } from '../customer-detail';

const {
  mockGetMobileUser,
  mockGetWallet,
  mockGetHistory,
  mockGetReferralUserDetail,
  mockListSupportNotes,
  mockGetVpnUser,
  mockGetSubscriptionSnapshot,
  mockGetTimeline,
  mockRegenerateVpnCredentials,
} = vi.hoisted(() => ({
  mockGetMobileUser: vi.fn(),
  mockGetWallet: vi.fn(),
  mockGetHistory: vi.fn(),
  mockGetReferralUserDetail: vi.fn(),
  mockListSupportNotes: vi.fn(),
  mockGetVpnUser: vi.fn(),
  mockGetSubscriptionSnapshot: vi.fn(),
  mockGetTimeline: vi.fn(),
  mockRegenerateVpnCredentials: vi.fn(),
}));

vi.mock('@/features/customers/components/customer-operations-insight', () => ({
  CustomerOperationsInsight: () => <div data-testid="customer-operations-insight" />,
}));

vi.mock('@/shared/ui/admin-action-dialog', async () => {
  const React = await vi.importActual<typeof import('react')>('react');

  return {
    AdminActionDialog: ({
      isOpen,
      title,
      confirmLabel,
      cancelLabel,
      onClose,
      onConfirm,
      subject,
      reasonLabel,
      reasonRequired,
      reasonValidationMessage,
    }: {
      isOpen: boolean;
      title: string;
      confirmLabel: string;
      cancelLabel: string;
      onClose: () => void;
      onConfirm: (reason?: string) => Promise<void> | void;
      subject?: ReactNode;
      reasonLabel?: string;
      reasonRequired?: boolean;
      reasonValidationMessage?: string;
    }) => {
      const [reason, setReason] = React.useState('');
      const [error, setError] = React.useState<string | null>(null);

      if (!isOpen) {
        return null;
      }

      return (
        <div role="dialog" aria-label={title}>
          {subject}
          {reasonLabel ? (
            <label>
              {reasonLabel}
              <textarea
                aria-label={reasonLabel}
                value={reason}
                onChange={(event) => {
                  setReason(event.target.value);
                  setError(null);
                }}
              />
            </label>
          ) : null}
          {error ? <p>{error}</p> : null}
          <button type="button" onClick={onClose}>
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={() => {
              const normalizedReason = reason.trim();
              if (reasonRequired && !normalizedReason) {
                setError(reasonValidationMessage ?? 'Reason is required.');
                return;
              }
              void onConfirm(normalizedReason || undefined);
            }}
          >
            {confirmLabel}
          </button>
        </div>
      );
    },
  };
});

vi.mock('@/lib/api/customers', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/customers')>('@/lib/api/customers');
  return {
    ...actual,
    customersApi: {
      ...actual.customersApi,
      getMobileUser: (...args: unknown[]) => mockGetMobileUser(...args),
      listSupportNotes: (...args: unknown[]) => mockListSupportNotes(...args),
      getVpnUser: (...args: unknown[]) => mockGetVpnUser(...args),
      getSubscriptionSnapshot: (...args: unknown[]) => mockGetSubscriptionSnapshot(...args),
      getTimeline: (...args: unknown[]) => mockGetTimeline(...args),
      regenerateVpnCredentials: (...args: unknown[]) => mockRegenerateVpnCredentials(...args),
    },
  };
});

vi.mock('@/lib/api/wallet', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/wallet')>('@/lib/api/wallet');
  return {
    ...actual,
    adminWalletApi: {
      ...actual.adminWalletApi,
      getWallet: (...args: unknown[]) => mockGetWallet(...args),
    },
  };
});

vi.mock('@/lib/api/payments', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/payments')>('@/lib/api/payments');
  return {
    ...actual,
    paymentsApi: {
      ...actual.paymentsApi,
      getHistory: (...args: unknown[]) => mockGetHistory(...args),
    },
  };
});

vi.mock('@/lib/api/growth', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api/growth')>('@/lib/api/growth');
  return {
    ...actual,
    growthApi: {
      ...actual.growthApi,
      getReferralUserDetail: (...args: unknown[]) => mockGetReferralUserDetail(...args),
    },
  };
});

function renderWithQueryClient(ui: ReactNode) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      {ui}
    </QueryClientProvider>,
  );
}

function arrangeCustomerDetailQueries() {
  mockGetMobileUser.mockResolvedValue({
    data: {
      id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      email: 'customer@example.com',
      username: 'customer',
      status: 'active',
      is_active: true,
      is_partner: false,
      telegram_id: 123456,
      telegram_username: 'customer_tg',
      remnawave_uuid: '56b5f2d9-2c79-4826-a6fe-ccbbcfb3ca22',
      referral_code: 'REF-001',
      referred_by_user_id: null,
      partner_user_id: null,
      partner_promoted_at: null,
      created_at: '2026-04-10T11:00:00Z',
      last_login_at: '2026-04-10T12:00:00Z',
      device_count: 0,
      subscription_url: null,
      updated_at: '2026-04-10T14:00:00Z',
      devices: [],
    },
  });
  mockGetWallet.mockResolvedValue({
    data: {
      user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      balance: 0,
      frozen: 0,
      currency: 'USD',
    },
  });
  mockGetHistory.mockResolvedValue({ data: { payments: [] } });
  mockGetReferralUserDetail.mockResolvedValue({
    data: {
      user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      total_earned: 0,
      commission_count: 0,
      referred_users: 0,
      referred_by_user_id: null,
      recent_commissions: [],
    },
  });
  mockListSupportNotes.mockResolvedValue({ data: [] });
  mockGetVpnUser.mockResolvedValue({
    data: {
      exists: true,
      remnawave_uuid: '56b5f2d9-2c79-4826-a6fe-ccbbcfb3ca22',
      username: 'customer',
      email: 'customer@example.com',
      status: 'active',
      short_uuid: 'vpn-safe-preview',
      subscription_uuid: '2a0668df-7a6a-4f00-b208-d4f71c25c887',
      expire_at: '2026-06-03T09:30:00Z',
      traffic_limit_bytes: 10737418240,
      used_traffic_bytes: 1073741824,
      created_at: '2026-04-10T11:00:00Z',
      updated_at: '2026-04-10T12:00:00Z',
      telegram_id: 123456,
    },
  });
  mockGetSubscriptionSnapshot.mockResolvedValue({
    data: {
      exists: true,
      remnawave_uuid: '56b5f2d9-2c79-4826-a6fe-ccbbcfb3ca22',
      status: 'active',
      short_uuid: 'vpn-safe-preview',
      subscription_uuid: '2a0668df-7a6a-4f00-b208-d4f71c25c887',
      expires_at: '2026-06-03T09:30:00Z',
      days_left: 30,
      traffic_limit_bytes: 10737418240,
      used_traffic_bytes: 1073741824,
      download_bytes: 536870912,
      upload_bytes: 536870912,
      lifetime_used_traffic_bytes: 1073741824,
      online_at: null,
      sub_last_user_agent: null,
      sub_revoked_at: null,
      last_traffic_reset_at: null,
      hwid_device_limit: 5,
      subscription_url: null,
      config_available: false,
      config: null,
      config_client_type: null,
      config_error: null,
      links: [],
      ss_conf_links: {},
    },
  });
  mockGetTimeline.mockResolvedValue({ data: { items: [] } });
  mockRegenerateVpnCredentials.mockResolvedValue({
    data: {
      user_id: '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
      remnawave_uuid: '56b5f2d9-2c79-4826-a6fe-ccbbcfb3ca22',
      status: 'active',
      short_uuid_changed: true,
      subscription_url_changed: true,
      revoke_only_passwords: true,
      expires_at: '2026-06-03T09:30:00Z',
      regenerated_at: '2026-05-04T09:30:00Z',
      config_delivery_required: true,
      audit_action: 'customer_vpn_credentials_regenerated',
      short_uuid: 'raw-short-secret',
      subscription_url: 'https://sub.example.local/raw-subscription-secret',
    },
  });
}

describe('CustomerDetail VPN credential regeneration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    arrangeCustomerDetailQueries();
  });

  it('opens a reason-gated credential regeneration dialog and renders only audit-safe result fields', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(<CustomerDetail userId="9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0" />);

    await user.click(await screen.findByRole('button', { name: 'detail.regenerateVpnCredentials' }));

    const dialog = await screen.findByRole('dialog', {
      name: 'detail.regenerateVpnCredentialsTitle',
    });

    const reasonField = within(dialog).getByRole('textbox', { name: 'detail.dialogs.reasonLabel' });
    await user.type(reasonField, 'Verified stolen-device recovery with customer');
    expect(reasonField).toHaveValue('Verified stolen-device recovery with customer');
    await user.click(within(dialog).getByRole('checkbox', { name: 'detail.revokeOnlyVpnPasswords' }));
    const confirmButton = within(dialog).getByRole('button', { name: 'detail.regenerateVpnCredentials' });
    expect(confirmButton).not.toBeDisabled();
    await user.click(confirmButton);

    expect(screen.queryByText('detail.credentialRegenerationReasonRequired')).not.toBeInTheDocument();

    await waitFor(() => {
      expect(mockRegenerateVpnCredentials).toHaveBeenCalledWith(
        '9ea92e5e-8267-4d46-9a83-f2ed9f55c7f0',
        {
          reason: 'Verified stolen-device recovery with customer',
          revoke_only_passwords: true,
        },
      );
    });

    expect(await screen.findByText('detail.credentialRegenerationResultTitle')).toBeVisible();
    expect(screen.getByText('customer_vpn_credentials_regenerated')).toBeVisible();
    expect(document.body.textContent).not.toContain('raw-short-secret');
    expect(document.body.textContent).not.toContain('raw-subscription-secret');
  });
});

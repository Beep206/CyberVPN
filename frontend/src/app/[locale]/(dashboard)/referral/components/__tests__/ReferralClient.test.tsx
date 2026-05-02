import type { ChangeEventHandler, KeyboardEventHandler } from 'react';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ReferralClient } from '../ReferralClient';

const messages = vi.hoisted(
  () =>
    ({
      copied: 'Copied!',
      shareTitle: 'Share your referral code',
      shareDescription:
        'Use your referral code with friends and keep invite access separate from checkout discounts.',
      yourCode: 'Your code',
      copyCode: 'Copy code',
      shareCode: 'Share code',
      shareMessage: 'Join CyberVPN with my referral code: {code}',
      programUnavailable:
        'The referral program is temporarily unavailable. Your existing invites stay visible here, but new referral actions may be paused until the program is restored.',
      redeemTitle: 'Redeem a code',
      redeemSubtitle:
        'Invite and gift codes redeem here. Promo and referral discounts still apply later in checkout.',
      redeemInputLabel: 'Invite or gift code',
      redeemPlaceholder: 'ENTER-CODE',
      redeemButton: 'Redeem code',
      redeeming: 'Redeeming...',
      redeemSuccessInvite: 'Invite redeemed. Added {days} free days to your account.',
      redeemSuccessGift: 'Gift redeemed. Added {plan} for {days} days to your account.',
      promoNoteTitle: 'Checkout policy',
      promoNoteBody:
        'Promo and referral discounts belong in checkout. This hub handles invite and gift redemption without creating a second pricing source of truth.',
      giftsTitle: 'My gifts',
      giftsSubtitle: 'Purchased or issued gift codes that you can share or track.',
      noGifts: 'No gift codes available yet.',
      'giftStatus.active': 'Active',
      'giftStatus.redeemed': 'Redeemed',
      'giftStatus.expired': 'Expired',
      'giftStatus.revoked': 'Revoked',
      giftPlan: '{plan} · {days} days',
      giftCreated: 'Created {date}',
      giftRedeemed: 'Redeemed {date}',
      giftRecipient: 'Recipient {recipient}',
      giftRecipientFallback: 'not specified',
      'giftPurchase.title': 'Buy Gift VPN',
      'giftPurchase.subtitle':
        'Create a gift checkout for a friend without mixing it into referral or promo pricing.',
      'giftPurchase.planLabel': 'Gift plan',
      'giftPurchase.planPlaceholder': 'Select a plan',
      'giftPurchase.recipientHintLabel': 'Recipient hint',
      'giftPurchase.recipientHintPlaceholder': 'friend@example.com or internal note',
      'giftPurchase.messageLabel': 'Gift message',
      'giftPurchase.messagePlaceholder': 'Optional note for the recipient',
      'giftPurchase.action': 'Create gift checkout',
      'giftPurchase.processing': 'Preparing gift checkout...',
      'giftPurchase.successPaymentPending':
        'Gift checkout created. Complete payment in the opened window.',
      'giftPurchase.successIssued': 'Gift issued successfully. Share this code: {code}',
      'giftPurchase.successQueued': 'Gift checkout created successfully.',
      'giftPurchase.errors.planRequired': 'Choose a plan before creating a gift checkout.',
      'giftPurchase.errors.default': 'Failed to create gift checkout.',
      invitesTitle: 'My invites',
      invitesSubtitle: 'Codes issued to your account and their current availability.',
      noInvites: 'No invite codes available yet.',
      inviteDays: '{days} free days',
      inviteExpires: 'Expires {date}',
      inviteCreated: 'Issued {date}',
      activityTitle: 'Recent referral activity',
      activitySubtitle:
        'Current backend contract still reports referral activity as reward entries tied to the active program.',
      noActivity: 'No referral activity yet.',
      activityReward: 'Reward entry {amount}',
      activityBase: 'Based on {amount} at {rate}%',
      hubEyebrow: 'SHARE & TRACK',
      'overview.activeInvites': 'Active invites',
      'overview.activeInvitesHint': 'Unused invite codes ready to share.',
      'overview.totalReferrals': 'Total referrals',
      'overview.totalReferralsHint': 'Accounts attributed to your current referral program.',
      'overview.totalRewards': 'Rewards earned',
      'overview.totalRewardsHint': 'Current backend reward total for this account.',
      'overview.currentRate': 'Current rate',
      'overview.currentRateHint': 'Program rate returned by the current referral contract.',
      'notifications.title': 'Growth notifications',
      'notifications.subtitle': 'Durable updates for invites, referral rewards, and gift codes.',
      'notifications.loading': 'Loading growth notifications...',
      'notifications.empty': 'No growth notifications are visible right now.',
      'notifications.unread': 'Unread',
      'notifications.actionRequired': 'Action required',
      'notifications.markRead': 'Mark read',
      'notifications.archive': 'Archive',
      'notifications.archived': 'Archived',
      'notifications.showArchived': 'Show archived',
      'notifications.showActive': 'Show active',
      'notifications.detailsButton': 'Details',
      'notifications.detailsTitle': 'Delivery details',
      'notifications.detailsLoading': 'Loading delivery details...',
      'notifications.detailsEmpty': 'Select a notification to inspect delivery details.',
      'notifications.supportTitle': 'Support handoff',
      'notifications.supportActionHint':
        'If the automated recovery path is blocked, use the guided repair or support flow below.',
      'notifications.copySupportSummary': 'Copy support summary',
      'notifications.openPreferences': 'Open preferences',
      'notifications.openTelegramLinking': 'Link Telegram',
      'notifications.reviewProfile': 'Review profile',
      'notifications.openSupportTicket': 'Open support ticket',
      'notifications.emailSupport': 'Email support',
      'notifications.openTelegramSupport': 'Open Telegram support',
      'notifications.openHelpCenter': 'Open help center',
      'notifications.openingSupport': 'Opening support...',
      'notifications.deliveryHistoryTitle': 'Delivery history',
      'notifications.noDeliveryHistory': 'No delivery history is attached to this notification.',
      'notifications.requestRetry': 'Request another send',
      'notifications.retrying': 'Requesting...',
      'notifications.deliveryPlannedAt': 'Planned {date}',
      'notifications.deliveryCompletedAt': 'Completed {date}',
      'notifications.counters.total': 'Total {count}',
      'notifications.counters.unread': 'Unread {count}',
      'notifications.counters.actionRequired': 'Action {count}',
      'preferences.title': 'Delivery preferences',
      'preferences.subtitle': 'Choose which growth events stay in-app, email, or Telegram.',
      'preferences.saving': 'Saving...',
      'preferences.note':
        'In-app preferences control this rewards inbox. Email and Telegram plan external delivery without creating a second source of truth.',
      'preferences.categories.invites': 'Invites',
      'preferences.categories.referralRewards': 'Referral rewards',
      'preferences.categories.gifts': 'Gift codes',
      'preferences.channels.inApp': 'In-app',
      'preferences.channels.email': 'Email',
      'preferences.channels.telegram': 'Telegram',
      'redeemErrors.empty': 'Enter a code first.',
      'inviteStatus.active': 'Active',
      'inviteStatus.used': 'Used',
      'inviteStatus.expired': 'Expired',
    }) as const,
);

const clipboardWriteTextMock = vi.hoisted(() => vi.fn(() => Promise.resolve()));

const referralHooks = vi.hoisted(() => ({
  useReferralCode: vi.fn(),
  useReferralStats: vi.fn(),
  useReferralStatus: vi.fn(),
  useInviteCodes: vi.fn(),
  useGiftCodes: vi.fn(),
  useGiftCatalogPlans: vi.fn(),
  useGiftPurchase: vi.fn(),
  useGrowthNotifications: vi.fn(),
  useGrowthNotificationCounters: vi.fn(),
  useGrowthNotificationDetail: vi.fn(),
  useGrowthNotificationPreferences: vi.fn(),
  useUpdateGrowthNotificationPreferences: vi.fn(),
  useMarkGrowthNotificationRead: vi.fn(),
  useArchiveGrowthNotification: vi.fn(),
  useRequestGrowthNotificationRecovery: vi.fn(),
  useRequestGrowthNotificationSupportEscalation: vi.fn(),
  useRecentReferralActivity: vi.fn(),
  useRedeemGrowthCode: vi.fn(),
  getGrowthNotificationRecoveryErrorMessage: vi.fn(
    () => 'Failed to request another delivery attempt.',
  ),
  getGrowthNotificationSupportEscalationErrorMessage: vi.fn(
    () => 'Failed to open guided support escalation.',
  ),
  getGrowthRedeemErrorMessage: vi.fn(() => 'Code not found or no longer available.'),
}));

vi.mock('next-intl', () => ({
  useLocale: () => 'en-US',
  useTranslations: () => (key: string, values?: Record<string, unknown>) => {
    const template = String(messages[key as keyof typeof messages] ?? key);
    if (!values) {
      return template;
    }

    return Object.entries(values).reduce<string>(
      (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
      template,
    );
  },
}));

vi.mock('@/features/auth/components/CyberInput', () => ({
  CyberInput: ({
    label,
    value,
    onChange,
    error,
    placeholder,
    onKeyDown,
    disabled,
  }: {
    label?: string;
    value?: string;
    onChange?: ChangeEventHandler<HTMLInputElement>;
    error?: string;
    placeholder?: string;
    onKeyDown?: KeyboardEventHandler<HTMLInputElement>;
    disabled?: boolean;
  }) => (
    <div>
      <label>{label}</label>
      <input
        aria-label={label}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        onKeyDown={onKeyDown}
        disabled={disabled}
      />
      {error ? <span role="alert">{error}</span> : null}
    </div>
  ),
}));

vi.mock('../../hooks/useReferral', () => referralHooks);

describe('ReferralClient', () => {
  const redeemMutateAsync = vi.fn();
  const purchaseMutateAsync = vi.fn();
  const markReadMutate = vi.fn();
  const archiveMutate = vi.fn();
  const requestRecoveryMutate = vi.fn();
  const requestSupportEscalationMutate = vi.fn();
  const updatePreferencesMutate = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    clipboardWriteTextMock.mockClear();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: clipboardWriteTextMock,
      },
    });

    referralHooks.useReferralCode.mockReturnValue({
      data: { referral_code: 'CYBER-REF' },
      isLoading: false,
    });
    referralHooks.useReferralStats.mockReturnValue({
      data: {
        total_referrals: 6,
        total_earned: 24,
        commission_rate: 10,
      },
      isLoading: false,
    });
    referralHooks.useReferralStatus.mockReturnValue({
      data: {
        enabled: true,
        commission_rate: 10,
      },
      isLoading: false,
    });
    referralHooks.useInviteCodes.mockReturnValue({
      data: [
        {
          id: 'invite-1',
          code: 'INVITE-AAA',
          free_days: 14,
          is_used: false,
          expires_at: '2026-05-01T00:00:00Z',
          created_at: '2026-04-15T00:00:00Z',
        },
        {
          id: 'invite-2',
          code: 'INVITE-BBB',
          free_days: 7,
          is_used: true,
          expires_at: '2026-04-10T00:00:00Z',
          created_at: '2026-04-01T00:00:00Z',
        },
      ],
      isLoading: false,
    });
    referralHooks.useGiftCodes.mockReturnValue({
      data: [
        {
          id: 'gift-1',
          masked_code: 'ABCD••••',
          raw_code: 'GIFT-AAA',
          code_type: 'gift',
          status: 'active',
          issuer_type: 'purchase',
          plan_family: 'max',
          duration_days: 365,
          recipient_hint: 'friend@example.com',
          created_at: '2026-04-18T00:00:00Z',
        },
      ],
      isLoading: false,
    });
    referralHooks.useGiftCatalogPlans.mockReturnValue({
      data: [
        {
          uuid: 'plan-max-365',
          display_name: 'Max',
          duration_days: 365,
          price_usd: 99,
          is_active: true,
        },
      ],
      isLoading: false,
    });
    referralHooks.useRecentReferralActivity.mockReturnValue({
      data: [
        {
          id: 'comm-1',
          commission_amount: 12,
          base_amount: 120,
          commission_rate: 10,
          created_at: '2026-04-20T09:00:00Z',
        },
      ],
      isLoading: false,
    });
    referralHooks.useGrowthNotifications.mockReturnValue({
      data: [
        {
          id: 'invite-issued:invite-1',
          kind: 'invite_issued',
          tone: 'info',
          route_slug: '/referral',
          title: 'Invite ready to share',
          message: 'Your account received an invite code for 14 free days.',
          notes: ['Source: purchase.'],
          action_required: true,
          unread: true,
          created_at: '2026-04-21T09:00:00Z',
        },
      ],
      isLoading: false,
    });
    referralHooks.useGrowthNotificationCounters.mockReturnValue({
      data: {
        total_notifications: 1,
        unread_notifications: 1,
        action_required_notifications: 1,
      },
      isLoading: false,
    });
    referralHooks.useGrowthNotificationDetail.mockImplementation((notificationId: string | null) => ({
      data: notificationId
        ? {
            notification: {
              id: notificationId,
              kind: 'invite_issued',
              tone: 'warning',
              route_slug: '/referral',
              title: 'Invite ready to share',
              message: 'Your account received an invite code for 14 free days.',
              notes: ['Source: purchase.'],
              action_required: true,
              unread: true,
              created_at: '2026-04-21T09:00:00Z',
              archived_at: null,
            },
            deliveries: [
              {
                delivery_id: 'delivery-email-1',
                delivery_channel: 'email',
                delivery_status: 'failed',
                troubleshooting_state: 'paused_admin',
                customer_message_key: 'growth_notifications.delivery.support_review',
                customer_summary: 'Email delivery is paused and needs support review.',
                recovery_allowed: false,
                support_required: true,
                planned_at: '2026-04-21T09:00:00Z',
                delivered_at: null,
                repair_target: {
                  kind: 'support_contact',
                  summary: 'Support review is required before email delivery can resume.',
                },
                events: [],
              },
            ],
            support_handoff: {
              reference_code: 'GROWTH::invite-issued:invite-1',
              troubleshooting_summary: 'Email delivery paused by support.',
              copy_text: 'Reference: GROWTH::invite-issued:invite-1',
              suggested_escalation_channel: 'support_email',
              contact_subject: '[GROWTH::invite-issued:invite-1] Growth delivery issue',
              contact_body: 'Reference: GROWTH::invite-issued:invite-1',
            },
          }
        : null,
      isLoading: false,
    }));
    referralHooks.useGrowthNotificationPreferences.mockReturnValue({
      data: {
        growth_in_app_invites: true,
        growth_email_invites: false,
        growth_telegram_invites: true,
        growth_in_app_referral_rewards: true,
        growth_email_referral_rewards: true,
        growth_telegram_referral_rewards: true,
        growth_in_app_gifts: true,
        growth_email_gifts: true,
        growth_telegram_gifts: true,
      },
      isLoading: false,
    });
    referralHooks.useRedeemGrowthCode.mockReturnValue({
      mutateAsync: redeemMutateAsync,
      isPending: false,
    });
    referralHooks.useGiftPurchase.mockReturnValue({
      mutateAsync: purchaseMutateAsync,
      isPending: false,
    });
    referralHooks.useMarkGrowthNotificationRead.mockReturnValue({
      mutate: markReadMutate,
      isPending: false,
    });
    referralHooks.useArchiveGrowthNotification.mockReturnValue({
      mutate: archiveMutate,
      isPending: false,
    });
    referralHooks.useRequestGrowthNotificationRecovery.mockReturnValue({
      mutate: requestRecoveryMutate,
      isPending: false,
    });
    referralHooks.useRequestGrowthNotificationSupportEscalation.mockReturnValue({
      mutate: requestSupportEscalationMutate,
      isPending: false,
    });
    referralHooks.useUpdateGrowthNotificationPreferences.mockReturnValue({
      mutate: updatePreferencesMutate,
      isPending: false,
    });
    redeemMutateAsync.mockResolvedValue({
      codeType: 'invite',
      inviteCode: {
        id: 'invite-3',
        code: 'NEWCODE',
        free_days: 7,
        is_used: true,
        expires_at: null,
        created_at: '2026-04-21T10:00:00Z',
      },
    });
    purchaseMutateAsync.mockResolvedValue({
      status: 'pending',
      quote: { gateway_amount: 99 },
      invoice: {
        payment_url: 'https://payments.example/gift-1',
      },
      gift_code: null,
    });
    vi.stubGlobal('open', vi.fn());
  });

  it('renders the growth hub overview, invites, gifts, and activity', () => {
    render(<ReferralClient />);

    expect(screen.getByText('CYBER-REF')).toBeInTheDocument();
    expect(screen.getByText('Active invites')).toBeInTheDocument();
    expect(screen.getByText('Total referrals')).toBeInTheDocument();
    expect(screen.getByText('Rewards earned')).toBeInTheDocument();
    expect(screen.getByText('Current rate')).toBeInTheDocument();
    expect(screen.getByText('INVITE-AAA')).toBeInTheDocument();
    expect(screen.getByText('INVITE-BBB')).toBeInTheDocument();
    expect(screen.getByText('My gifts')).toBeInTheDocument();
    expect(screen.getByText('GIFT-AAA')).toBeInTheDocument();
    expect(screen.getByText('Growth notifications')).toBeInTheDocument();
    expect(screen.getByText('Invite ready to share')).toBeInTheDocument();
    expect(screen.getByText('Delivery preferences')).toBeInTheDocument();
    expect(screen.getByText('Recent referral activity')).toBeInTheDocument();
    expect(screen.getByText(/Reward entry \$12/i)).toBeInTheDocument();
  });

  it('redeems an invite code and shows the success message', async () => {
    const user = userEvent.setup();

    render(<ReferralClient />);

    await user.type(screen.getByLabelText('Invite or gift code'), 'newcode');
    await user.click(screen.getByRole('button', { name: 'Redeem code' }));

    await waitFor(() => {
      expect(redeemMutateAsync).toHaveBeenCalledWith('NEWCODE');
    });

    expect(screen.getByText('Invite redeemed. Added 7 free days to your account.')).toBeInTheDocument();
  });

  it('creates a gift checkout from the rewards hub', async () => {
    const user = userEvent.setup();

    render(<ReferralClient />);

    await user.selectOptions(screen.getByLabelText('Gift plan'), 'plan-max-365');
    await user.type(screen.getByLabelText('Recipient hint'), 'friend@example.com');
    await user.click(screen.getByRole('button', { name: 'Create gift checkout' }));

    await waitFor(() => {
      expect(purchaseMutateAsync).toHaveBeenCalledWith({
        plan_id: 'plan-max-365',
        recipient_hint: 'friend@example.com',
        gift_message: null,
        channel: 'web',
      });
    });

    expect(screen.getByText('Gift checkout created. Complete payment in the opened window.')).toBeInTheDocument();
  });

  it('updates growth delivery preferences from the rewards hub', async () => {
    const user = userEvent.setup();

    render(<ReferralClient />);

    await user.click(screen.getAllByRole('button', { name: 'Email' })[0]);

    expect(updatePreferencesMutate).toHaveBeenCalledWith({
      growth_email_invites: true,
    });
  });

  it('opens guided support escalation for blocked deliveries', async () => {
    const user = userEvent.setup();

    render(<ReferralClient />);

    await user.click(screen.getByRole('button', { name: 'Details' }));
    await user.click(screen.getByRole('button', { name: 'Email support' }));

    expect(requestSupportEscalationMutate).toHaveBeenCalledWith(
      {
        notificationId: 'invite-issued:invite-1',
        deliveryChannel: 'email',
        escalationChannel: 'support_email',
      },
      expect.objectContaining({
        onSuccess: expect.any(Function),
        onError: expect.any(Function),
      }),
    );
  });

});

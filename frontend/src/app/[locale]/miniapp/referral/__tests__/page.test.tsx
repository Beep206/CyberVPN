import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import MiniAppReferralPage from '../page';
import {
  cleanupTelegramWebAppMock,
  setupTelegramWebAppMock,
} from '@/test/mocks/telegram-webapp';

const messages = vi.hoisted(
  () =>
    ({
      title: 'Rewards Hub',
      hubEyebrow: 'SHARE & TRACK',
      shareTitle: 'Share your referral code',
      shareDescription:
        'Keep referral sharing, invite and gift redemption, and issued code tracking in one place. Promo discounts still belong in checkout.',
      yourCode: 'Your referral code',
      copyCode: 'Copy code',
      shareCode: 'Share link',
      qrCodeTitle: 'Telegram QR',
      qrCodeHint:
        'Scan to open CyberVPN in Telegram with your referral code prefilled.',
      copied: 'Copied',
      copyFailed: 'Failed to copy code.',
      shareText: 'Join CyberVPN with my referral code: {code}',
      programUnavailable:
        'The referral program is temporarily unavailable. Existing invites remain visible here, but new referral actions may be paused until the program is restored.',
      redeemTitle: 'Redeem a code',
      redeemSubtitle:
        'Invite and gift codes redeem here. Promo discounts and referral friend discounts apply later in checkout.',
      redeemInputLabel: 'Invite or gift code',
      redeemPlaceholder: 'ENTER-CODE',
      redeemButton: 'Redeem code',
      redeeming: 'Redeeming...',
      redeemSuccessInvite:
        'Invite redeemed. Added {days} free days to your account.',
      redeemSuccessGift:
        'Gift redeemed. Added {plan} for {days} days to your account.',
      promoNoteTitle: 'Checkout policy',
      promoNoteBody:
        'Promo and referral discounts stay in checkout, not in this screen. This hub only handles sharing, tracking, and invite or gift redemption.',
      giftsTitle: 'My gifts',
      giftsSubtitle:
        'Purchased or issued gift codes you can share from Telegram.',
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
        'Create a gift checkout inside Telegram without mixing it into referral or promo pricing.',
      'giftPurchase.planLabel': 'Gift plan',
      'giftPurchase.planPlaceholder': 'Select a plan',
      'giftPurchase.recipientHintLabel': 'Recipient hint',
      'giftPurchase.recipientHintPlaceholder': 'friend@example.com or note',
      'giftPurchase.messageLabel': 'Gift message',
      'giftPurchase.messagePlaceholder': 'Optional note for the recipient',
      'giftPurchase.action': 'Create gift checkout',
      'giftPurchase.processing': 'Preparing gift checkout...',
      'giftPurchase.successPaymentPending':
        'Gift checkout created. Complete payment in Telegram.',
      'giftPurchase.successIssued':
        'Gift issued successfully. Share this code: {code}',
      'giftPurchase.successQueued': 'Gift checkout created successfully.',
      'giftPurchase.errors.planRequired':
        'Choose a plan before creating a gift checkout.',
      'giftPurchase.errors.default': 'Failed to create gift checkout.',
      invitesTitle: 'My invites',
      invitesSubtitle: 'Invite codes already issued to your account.',
      noInvites: 'No invite codes available yet.',
      activityTitle: 'Recent referral activity',
      activitySubtitle:
        'Current backend contract still reports referral activity as reward entries tied to your account.',
      noActivity: 'No referral activity yet.',
      activityReward: 'Reward entry {amount}',
      activityBase: 'Based on {amount} at {rate}%',
      'redeemErrors.empty': 'Enter a code first.',
      'inviteStatus.active': 'Active',
      'inviteStatus.used': 'Used',
      'inviteStatus.expired': 'Expired',
      inviteDays: '{days} free days',
      inviteExpires: 'Expires {date}',
      inviteCreated: 'Issued {date}',
      'overview.activeInvites': 'Active invites',
      'overview.activeInvitesHint': 'Unused invite codes ready to share.',
      'overview.totalReferrals': 'Total referrals',
      'overview.totalReferralsHint':
        'Accounts attributed to your current referral program.',
      'overview.totalRewards': 'Rewards earned',
      'overview.totalRewardsHint':
        'Current backend reward total for this account.',
      'overview.currentRate': 'Current rate',
      'overview.currentRateHint':
        'Program rate returned by the current referral contract.',
      'notifications.title': 'Growth notifications',
      'notifications.subtitle':
        'Durable updates for invites, referral rewards, and gift codes.',
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
      'notifications.detailsEmpty':
        'Select a notification to inspect delivery details.',
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
      'notifications.noDeliveryHistory':
        'No delivery history is attached to this notification.',
      'notifications.requestRetry': 'Request another send',
      'notifications.retrying': 'Requesting...',
      'notifications.deliveryPlannedAt': 'Planned {date}',
      'notifications.deliveryCompletedAt': 'Completed {date}',
      'notifications.counters.total': 'Total {count}',
      'notifications.counters.unread': 'Unread {count}',
      'notifications.counters.actionRequired': 'Action {count}',
      'preferences.title': 'Delivery preferences',
      'preferences.subtitle':
        'Choose which growth events stay in-app, email, or Telegram.',
      'preferences.saving': 'Saving...',
      'preferences.note':
        'In-app preferences control this rewards inbox. Email and Telegram plan external delivery without creating a second source of truth.',
      'preferences.categories.invites': 'Invites',
      'preferences.categories.referralRewards': 'Referral rewards',
      'preferences.categories.gifts': 'Gift codes',
      'preferences.channels.inApp': 'In-app',
      'preferences.channels.email': 'Email',
      'preferences.channels.telegram': 'Telegram',
    }) as const,
);

const clipboardWriteTextMock = vi.hoisted(() => vi.fn(() => Promise.resolve()));

const capabilitiesMock = vi.hoisted(() => ({
  data: {
    growth: {
      checkout_code_discounts: false,
      gift_codes: false,
      growth_hub: false,
      invites: false,
      promo_codes: false,
      referral: false,
    },
  },
}));

const growthHooks = vi.hoisted(() => ({
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
  getGrowthRedeemErrorMessage: vi.fn(
    () => 'Code not found or no longer available.',
  ),
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

vi.mock('next/dynamic', () => ({
  default:
    () =>
    ({ value }: { value: string }) => (
      <div data-testid="qr-code" data-value={value}>
        qr
      </div>
    ),
}));

vi.mock(
  '@/features/customer-growth/hooks/useCustomerGrowth',
  () => growthHooks,
);

vi.mock(
  '@/features/client-capabilities/useClientCapabilities',
  async (importOriginal) => {
    const actual =
      await importOriginal<
        typeof import('@/features/client-capabilities/useClientCapabilities')
      >();
    return {
      ...actual,
      useClientCapabilities: () => capabilitiesMock,
    };
  },
);

describe('MiniAppReferralPage', () => {
  const redeemMutateAsync = vi.fn();
  const purchaseMutateAsync = vi.fn();
  const markReadMutate = vi.fn();
  const archiveMutate = vi.fn();
  const requestRecoveryMutate = vi.fn();
  const requestSupportEscalationMutate = vi.fn();
  const updatePreferencesMutate = vi.fn();

  beforeEach(() => {
    setupTelegramWebAppMock();
    vi.clearAllMocks();
    clipboardWriteTextMock.mockClear();
    capabilitiesMock.data.growth.checkout_code_discounts = false;
    capabilitiesMock.data.growth.gift_codes = false;
    capabilitiesMock.data.growth.growth_hub = false;
    capabilitiesMock.data.growth.invites = false;
    capabilitiesMock.data.growth.promo_codes = false;
    capabilitiesMock.data.growth.referral = false;

    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: clipboardWriteTextMock,
      },
    });

    growthHooks.useReferralCode.mockReturnValue({
      data: { referral_code: 'CYBER-REF' },
      isLoading: false,
    });
    growthHooks.useReferralStats.mockReturnValue({
      data: {
        total_referrals: 6,
        total_earned: 24,
        commission_rate: 10,
      },
      isLoading: false,
    });
    growthHooks.useReferralStatus.mockReturnValue({
      data: {
        enabled: true,
        commission_rate: 10,
      },
      isLoading: false,
    });
    growthHooks.useInviteCodes.mockReturnValue({
      data: [
        {
          id: 'invite-1',
          code: 'INVITE-AAA',
          free_days: 14,
          is_used: false,
          expires_at: '2026-05-01T00:00:00Z',
          created_at: '2026-04-15T00:00:00Z',
        },
      ],
      isLoading: false,
    });
    growthHooks.useGiftCodes.mockReturnValue({
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
    growthHooks.useGiftCatalogPlans.mockReturnValue({
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
    growthHooks.useRecentReferralActivity.mockReturnValue({
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
    growthHooks.useGrowthNotifications.mockReturnValue({
      data: [
        {
          id: 'gift-issued:gift-1',
          kind: 'gift_available',
          tone: 'success',
          route_slug: '/referral',
          title: 'Gift code available',
          message: 'A max gift for 365 days was issued to your account.',
          notes: ['Recipient: friend@example.com.'],
          action_required: true,
          unread: true,
          created_at: '2026-04-21T09:00:00Z',
        },
      ],
      isLoading: false,
    });
    growthHooks.useGrowthNotificationCounters.mockReturnValue({
      data: {
        total_notifications: 1,
        unread_notifications: 1,
        action_required_notifications: 1,
      },
      isLoading: false,
    });
    growthHooks.useGrowthNotificationDetail.mockImplementation(
      (notificationId: string | null) => ({
        data: notificationId
          ? {
              notification: {
                id: notificationId,
                kind: 'gift_available',
                tone: 'warning',
                route_slug: '/referral',
                title: 'Gift code available',
                message: 'A max gift for 365 days was issued to your account.',
                notes: ['Recipient: friend@example.com.'],
                action_required: true,
                unread: true,
                created_at: '2026-04-21T09:00:00Z',
                archived_at: null,
              },
              deliveries: [
                {
                  delivery_id: 'delivery-telegram-1',
                  delivery_channel: 'telegram',
                  delivery_status: 'paused',
                  troubleshooting_state: 'paused_admin',
                  customer_message_key:
                    'growth_notifications.delivery.support_review',
                  customer_summary:
                    'Telegram delivery is paused and needs support review.',
                  recovery_allowed: false,
                  support_required: true,
                  planned_at: '2026-04-21T09:00:00Z',
                  delivered_at: null,
                  repair_target: {
                    kind: 'support_contact',
                    summary:
                      'Support review is required before Telegram delivery can resume.',
                  },
                  events: [],
                },
              ],
              support_handoff: {
                reference_code: 'GROWTH::gift-issued:gift-1',
                troubleshooting_summary: 'Telegram delivery paused by support.',
                copy_text: 'Reference: GROWTH::gift-issued:gift-1',
                suggested_escalation_channel: 'telegram_support',
                contact_subject:
                  '[GROWTH::gift-issued:gift-1] Growth delivery issue',
                contact_body: 'Reference: GROWTH::gift-issued:gift-1',
              },
            }
          : null,
        isLoading: false,
      }),
    );
    growthHooks.useGrowthNotificationPreferences.mockReturnValue({
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
    growthHooks.useRedeemGrowthCode.mockReturnValue({
      mutateAsync: redeemMutateAsync,
      isPending: false,
    });
    growthHooks.useGiftPurchase.mockReturnValue({
      mutateAsync: purchaseMutateAsync,
      isPending: false,
    });
    growthHooks.useMarkGrowthNotificationRead.mockReturnValue({
      mutate: markReadMutate,
      isPending: false,
    });
    growthHooks.useArchiveGrowthNotification.mockReturnValue({
      mutate: archiveMutate,
      isPending: false,
    });
    growthHooks.useRequestGrowthNotificationRecovery.mockReturnValue({
      mutate: requestRecoveryMutate,
      isPending: false,
    });
    growthHooks.useRequestGrowthNotificationSupportEscalation.mockReturnValue({
      mutate: requestSupportEscalationMutate,
      isPending: false,
    });
    growthHooks.useUpdateGrowthNotificationPreferences.mockReturnValue({
      mutate: updatePreferencesMutate,
      isPending: false,
    });
    redeemMutateAsync.mockResolvedValue({
      codeType: 'invite',
      inviteCode: {
        id: 'invite-2',
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
  });

  afterEach(() => {
    cleanupTelegramWebAppMock();
  });

  it('renders the runtime paused state when every growth surface is disabled', () => {
    render(<MiniAppReferralPage />);

    expect(screen.getByText('Rewards hub is paused')).toBeInTheDocument();
    expect(
      screen.queryByText('Share your referral code'),
    ).not.toBeInTheDocument();
  });

  it('shows referral, gift, promo, and invite surfaces from runtime capabilities', () => {
    capabilitiesMock.data.growth.checkout_code_discounts = true;
    capabilitiesMock.data.growth.gift_codes = true;
    capabilitiesMock.data.growth.growth_hub = true;
    capabilitiesMock.data.growth.invites = true;
    capabilitiesMock.data.growth.promo_codes = true;
    capabilitiesMock.data.growth.referral = true;

    render(<MiniAppReferralPage />);

    expect(screen.getByText('Share your referral code')).toBeInTheDocument();
    expect(screen.getByText('Checkout policy')).toBeInTheDocument();
    expect(screen.getByText('Buy Gift VPN')).toBeInTheDocument();
    expect(screen.getByText('My invites')).toBeInTheDocument();
    expect(screen.getByText('My gifts')).toBeInTheDocument();
  });
});

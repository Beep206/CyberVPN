import { apiClient } from './client';
import type { AddonRecord } from './addons';
import type {
  CheckoutCommitResponse,
  CheckoutQuoteRequest,
  CheckoutQuoteResponse,
  PaymentStatusResponse,
} from './payments';
import type { PlanRecord } from './plans';
import type { CurrentEntitlementsResponse } from './subscriptions';

export type MiniAppBootstrap = {
  session: {
    authenticated: boolean;
    userId: string | null;
    telegramUserId: string | null;
    authRealm: 'customer' | 'partner_customer';
  };
  runtime: {
    surface: 'telegram_miniapp';
    tenant: {
      kind: 'platform' | 'partner';
      partnerId?: string | null;
      workspaceId?: string | null;
      storefrontId?: string | null;
      botId?: string | null;
    };
    brand: {
      name: string;
      logoUrl?: string | null;
      primaryColor?: string | null;
      supportUrl?: string | null;
      legalName?: string | null;
    };
    commercialPolicy: {
      pricingPolicyId: string;
      currencyPolicy: string;
      revenueSharePolicyId?: string | null;
      trialPolicyId?: string | null;
    };
    attribution: {
      source: string;
      surface: string;
      referralCode?: string | null;
      campaign?: string | null;
      startParam?: string | null;
    };
  };
  user: {
    firstName?: string | null;
    username?: string | null;
    photoUrl?: string | null;
    locale: string;
    rtl: boolean;
  };
  subscription: {
    status: string;
    planId?: string | null;
    planName?: string | null;
    expiresAt?: string | null;
    autoRenew: boolean;
  };
  trial: {
    eligible: boolean;
    reason?: string | null;
    durationDays?: number | null;
    trialStart?: string | null;
    trialEnd?: string | null;
    daysRemaining: number;
  };
  wallet: {
    balance: number;
    currency: string;
    bonusesAvailable: number;
  };
  devices: {
    activeCount: number;
    limit: number;
    hasConfig: boolean;
  };
  usage: {
    usageAvailable: boolean;
    usageSource: 'remnawave' | 'unavailable';
    usageUnavailableReason?: 'upstream_user_not_found' | 'upstream_unavailable' | null;
    bandwidthUsedBytes: number;
    bandwidthLimitBytes: number;
    connectionsActive: number;
    connectionsLimit: number;
    periodStart?: string | null;
    periodEnd?: string | null;
    lastConnectionAt?: string | null;
  };
  serviceState: {
    providerName?: string | null;
    channelType?: string | null;
  };
  recommendedServer: null | {
    id: string;
    countryCode: string;
    city?: string | null;
    publicName: string;
    latencyMs?: number | null;
    speedMbps?: number | null;
    uptimePct30d?: number | null;
    dpiScore?: number | null;
    status: 'online' | 'degraded' | 'offline';
    recommendedReason?: string | null;
  };
  primaryCta: {
    kind: 'start_trial' | 'buy_plan' | 'renew' | 'get_config' | 'select_server';
    label: string;
  };
  referral: {
    code?: string | null;
    inviteUrl?: string | null;
    shareText?: string | null;
  };
  payment: {
    unresolvedPaymentId?: string | null;
    lastStatus?: 'pending' | 'paid' | 'cancelled' | 'failed' | null;
  };
  support: {
    url?: string | null;
    paysupportCommandAvailable: boolean;
  };
  rollout: {
    enabled: boolean;
    mode: 'live' | 'canary' | 'maintenance' | 'rollback';
    trialEnabled: boolean;
    checkoutEnabled: boolean;
    configEnabled: boolean;
    accessGranted: boolean;
    isCanaryUser: boolean;
    gateReasonCode?:
      | 'runtime_disabled'
      | 'maintenance'
      | 'rollback'
      | 'feature_disabled'
      | 'canary_not_allowed'
      | null;
    maintenanceMessage?: string | null;
  };
  featureFlags: Record<string, boolean>;
  freshness: {
    generatedAt: string;
  };
};

export type MiniAppTrialStatus = {
  is_trial_active: boolean;
  trial_start?: string | null;
  trial_end?: string | null;
  days_remaining: number;
  is_eligible: boolean;
};

export type MiniAppTrialActivateResponse = {
  activated: boolean;
  trial_end: string;
  message: string;
};

export type MiniAppOffers = {
  plans: PlanRecord[];
  addons: AddonRecord[];
  trial: MiniAppTrialStatus;
  currentEntitlements: CurrentEntitlementsResponse;
  freshness: {
    generatedAt: string;
  };
};

export type MiniAppConfig = {
  config: string;
  configString: string;
  clientType: string;
  source: 'remnawave_generated' | 'legacy_subscription_url';
  isFound: boolean;
  links: string[];
  ssConfLinks: Record<string, string>;
  subscriptionUrl?: string | null;
  generatedAt: string;
};

export type MiniAppCheckoutFlow = 'checkout' | 'upgrade' | 'addons';

export type MiniAppCheckoutRequest = Omit<CheckoutQuoteRequest, 'channel'> & {
  flow: MiniAppCheckoutFlow;
};

export const miniappApi = {
  getBootstrap: (params?: { locale?: string; startParam?: string | null }) =>
    apiClient.get<MiniAppBootstrap>('/miniapp/bootstrap', { params }),
  getOffers: () =>
    apiClient.get<MiniAppOffers>('/miniapp/offers'),
  activateTrial: () =>
    apiClient.post<MiniAppTrialActivateResponse>('/miniapp/trial/activate', {}),
  quoteCheckout: (data: MiniAppCheckoutRequest) =>
    apiClient.post<CheckoutQuoteResponse>('/miniapp/checkout/quote', data),
  commitCheckout: (data: MiniAppCheckoutRequest) =>
    apiClient.post<CheckoutCommitResponse>('/miniapp/checkout/commit', data),
  getPayment: (paymentId: string) =>
    apiClient.get<PaymentStatusResponse>(`/miniapp/payments/${paymentId}`),
  getConfig: () =>
    apiClient.get<MiniAppConfig>('/miniapp/config'),
};

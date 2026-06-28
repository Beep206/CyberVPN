import { useQuery } from '@tanstack/react-query';
import {
  clientCapabilitiesApi,
  type ClientCapabilitiesResponse,
} from '@/lib/api/client-capabilities';

export const CLIENT_CAPABILITIES_QUERY_KEY = ['client-capabilities'] as const;

export const DISABLED_CLIENT_CAPABILITIES: ClientCapabilitiesResponse = {
  auth: {
    email_password: true,
    magic_link: true,
    telegram: true,
  },
  payments: {
    web_checkout: false,
    telegram_stars: false,
    cryptobot: false,
    manual_invoice: false,
    autorenewal: false,
  },
  growth: {
    invites: false,
    referral: false,
    promo_codes: false,
    gift_codes: false,
    checkout_code_discounts: false,
    growth_hub: false,
  },
  subscriptions: {
    multi_subscription: true,
    selected_subscription_required: true,
    addons: false,
    upgrade: true,
    trial: false,
    paid_provisioning: false,
  },
  partner: {
    portal: false,
    applications: false,
    codes: false,
    attribution: false,
    storefronts: false,
    reporting: false,
    settlement_sandbox: false,
    webhooks: false,
    payouts: false,
    event_backbone: false,
  },
  site: {
    customer_site_mode: 'full_site',
    cabinet_only: false,
    version: 1,
    public_hosts: [],
    cabinet_hosts: [],
    cabinet_destination_path: '/dashboard',
    cabinet_marketing_route_action: 'redirect_public',
    public_marketing_destination_path: '/',
    allowed_path_prefixes: [],
    preserve_query_keys: [],
    registration_policy_independent: true,
  },
  onboarding: {
    post_registration_code_prompt: false,
    web_otp: false,
    telegram_miniapp: false,
    state_store: false,
    flow_key: 'post_registration_growth_code_v1',
    version: 1,
    allowed_code_types: [],
    allow_referral_input: false,
    allow_partner_input: false,
    available: false,
  },
};

export function useClientCapabilities() {
  return useQuery({
    queryKey: CLIENT_CAPABILITIES_QUERY_KEY,
    queryFn: async () => {
      const response = await clientCapabilitiesApi.get();
      return response.data;
    },
    staleTime: 60_000,
    gcTime: 10 * 60_000,
    retry: 1,
    placeholderData: DISABLED_CLIENT_CAPABILITIES,
  });
}

export function isClientCapabilitiesReady(query: {
  data?: ClientCapabilitiesResponse;
  isPlaceholderData?: boolean;
  isLoading?: boolean;
  isPending?: boolean;
  isSuccess?: boolean;
}): boolean {
  if (query.isPlaceholderData === true) {
    return false;
  }
  if (query.isSuccess === true) {
    return true;
  }
  return (
    query.data !== undefined &&
    query.isLoading !== true &&
    query.isPending !== true
  );
}

export function isWebCheckoutRailEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.payments.web_checkout === true;
}

export function isGenericCheckoutRailEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return (
    capabilities?.payments.web_checkout === true ||
    capabilities?.payments.cryptobot === true
  );
}

export function isTelegramStarsRailEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.payments.telegram_stars === true;
}

export function isMiniAppCheckoutRailEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return (
    isGenericCheckoutRailEnabled(capabilities) ||
    isTelegramStarsRailEnabled(capabilities)
  );
}

export function hasManualInvoiceFallback(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.payments.manual_invoice === true;
}

export function areSubscriptionAddonsEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.subscriptions.addons === true;
}

export function areSubscriptionUpgradesEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.subscriptions.upgrade !== false;
}

export function areInviteCodesEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.growth.invites === true;
}

export function isReferralProgramEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.growth.referral === true;
}

export function arePromoCodesEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.growth.promo_codes === true;
}

export function areGiftCodesEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.growth.gift_codes === true;
}

export function areCheckoutCodeDiscountsEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.growth.checkout_code_discounts === true;
}

export function isGrowthHubEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.growth.growth_hub === true;
}

export function isAnyGrowthSurfaceEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return (
    areInviteCodesEnabled(capabilities) ||
    isReferralProgramEnabled(capabilities) ||
    arePromoCodesEnabled(capabilities) ||
    areGiftCodesEnabled(capabilities) ||
    areCheckoutCodeDiscountsEnabled(capabilities) ||
    isGrowthHubEnabled(capabilities)
  );
}

export function isCustomerSiteCabinetOnly(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return (
    capabilities?.site?.cabinet_only === true ||
    capabilities?.site?.customer_site_mode === 'cabinet_only'
  );
}

export function isCustomerSiteMaintenanceMode(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.site?.customer_site_mode === 'maintenance';
}

export function isCustomerOnboardingAvailable(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return capabilities?.onboarding?.available === true;
}

export function isPostRegistrationCodePromptEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return (
    isCustomerOnboardingAvailable(capabilities) &&
    capabilities?.onboarding?.post_registration_code_prompt === true
  );
}

export function isWebOtpOnboardingEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return (
    isCustomerOnboardingAvailable(capabilities) &&
    capabilities?.onboarding?.web_otp === true
  );
}

export function isTelegramMiniAppOnboardingEnabled(
  capabilities: ClientCapabilitiesResponse | undefined,
): boolean {
  return (
    isCustomerOnboardingAvailable(capabilities) &&
    capabilities?.onboarding?.telegram_miniapp === true
  );
}

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
    manual_invoice: true,
    autorenewal: false,
  },
  growth: {
    invites: true,
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
  return capabilities?.growth.invites !== false;
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

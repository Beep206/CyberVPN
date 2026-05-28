import { apiClient } from './client';

export interface ClientAuthCapabilities {
  email_password: boolean;
  magic_link: boolean;
  telegram: boolean;
}

export interface ClientPaymentCapabilities {
  web_checkout: boolean;
  telegram_stars: boolean;
  cryptobot: boolean;
  manual_invoice: boolean;
  autorenewal: boolean;
}

export interface ClientGrowthCapabilities {
  invites: boolean;
  referral: boolean;
  promo_codes: boolean;
  gift_codes: boolean;
  checkout_code_discounts: boolean;
  growth_hub: boolean;
}

export interface ClientSubscriptionCapabilities {
  multi_subscription: boolean;
  selected_subscription_required: boolean;
  addons: boolean;
  upgrade: boolean;
  trial: boolean;
  paid_provisioning: boolean;
}

export interface ClientPartnerCapabilities {
  portal: boolean;
  applications: boolean;
  codes: boolean;
  attribution: boolean;
  storefronts: boolean;
  reporting: boolean;
  settlement_sandbox: boolean;
  webhooks: boolean;
  payouts: boolean;
  event_backbone: boolean;
}

export interface ClientCapabilitiesResponse {
  auth: ClientAuthCapabilities;
  payments: ClientPaymentCapabilities;
  growth: ClientGrowthCapabilities;
  subscriptions: ClientSubscriptionCapabilities;
  partner: ClientPartnerCapabilities;
}

export const clientCapabilitiesApi = {
  get: () => apiClient.get<ClientCapabilitiesResponse>('/client/capabilities'),
};


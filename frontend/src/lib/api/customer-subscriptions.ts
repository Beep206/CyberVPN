import { apiClient } from './client';

export type CustomerSubscriptionKind = 'entitlement_grant' | 'legacy_payment' | 'trial';
export type CustomerSubscriptionManagementScope = 'account_vpn_identity' | 'subscription_entitlement';

export type CustomerSubscriptionSummary = {
  subscription_key: string;
  kind: CustomerSubscriptionKind;
  status: string;
  display_name: string | null;
  plan_uuid: string | null;
  plan_code: string | null;
  source_type: string | null;
  source_order_id: string | null;
  entitlement_grant_id: string | null;
  service_identity_id: string | null;
  provider_name: string | null;
  expires_at: string | null;
  created_at: string | null;
  effective_entitlements: Record<string, unknown>;
  invite_bundle: Record<string, number>;
  is_trial: boolean;
  addons: Array<Record<string, unknown>>;
  can_manage: boolean;
  can_deliver_config: boolean;
  management_scope: CustomerSubscriptionManagementScope;
};

export type CustomerSubscriptionsResponse = {
  customer_account_id: string;
  auth_realm_id: string;
  selected_subscription_key: string | null;
  default_subscription_key: string | null;
  items: CustomerSubscriptionSummary[];
  limitations: string[];
};

export type CustomerSubscriptionEntitlementsResponse = {
  status: string;
  plan_uuid: string | null;
  plan_code: string | null;
  display_name: string | null;
  period_days: number | null;
  expires_at: string | null;
  effective_entitlements: Record<string, unknown>;
  invite_bundle: Record<string, number>;
  is_trial: boolean;
  addons: Array<Record<string, unknown>>;
};

export const customerSubscriptionsApi = {
  list: (selectedSubscriptionKey?: string | null) => {
    const params = selectedSubscriptionKey
      ? `?selected_subscription_key=${encodeURIComponent(selectedSubscriptionKey)}`
      : '';

    return apiClient.get<CustomerSubscriptionsResponse>(`/customer-subscriptions/${params}`);
  },

  get: (subscriptionKey: string) =>
    apiClient.get<CustomerSubscriptionSummary>(
      `/customer-subscriptions/${encodeURIComponent(subscriptionKey)}`,
    ),

  getEntitlements: (subscriptionKey: string) =>
    apiClient.get<CustomerSubscriptionEntitlementsResponse>(
      `/customer-subscriptions/${encodeURIComponent(subscriptionKey)}/entitlements`,
    ),
};

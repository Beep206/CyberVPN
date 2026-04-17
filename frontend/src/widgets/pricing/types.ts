export type PricingTierCode = 'basic' | 'plus' | 'pro' | 'max';

export type PricingInviteBundle = {
  count: number;
  friend_days: number;
  expiry_days: number;
};

export type PricingDedicatedIp = {
  included: number;
  eligible: boolean;
};

export type PricingTrafficPolicy = {
  mode: string;
  display_label: string;
  enforcement_profile?: string | null;
};

export type PricingPlanPeriod = {
  uuid: string;
  name: string;
  duration_days: number;
  price_usd: number;
  price_rub?: number | null;
  invite_bundle: PricingInviteBundle;
  trial_eligible: boolean;
  sort_order: number;
};

export type PricingPlanFamily = {
  code: PricingTierCode;
  display_name: string;
  devices_included: number;
  traffic_policy: PricingTrafficPolicy;
  connection_modes: string[];
  server_pool: string[];
  support_sla: string;
  dedicated_ip: PricingDedicatedIp;
  features: Record<string, unknown>;
  periods: PricingPlanPeriod[];
  sort_order: number;
  is_active: boolean;
};

export type PricingAddon = {
  uuid: string;
  code: string;
  display_name: string;
  duration_mode: string;
  is_stackable: boolean;
  quantity_step: number;
  price_usd: number;
  price_rub?: number | null;
  max_quantity_by_plan: Record<string, number>;
  delta_entitlements: Record<string, unknown>;
  requires_location: boolean;
  sale_channels: string[];
  is_active: boolean;
};

export type PricingCatalogData = {
  plans: PricingPlanFamily[];
  addons: PricingAddon[];
  periods: number[];
  source: 'api' | 'fallback';
};

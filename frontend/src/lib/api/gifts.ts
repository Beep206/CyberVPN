import type { CheckoutQuoteResponse, CheckoutCommitResponse } from './payments';
import { apiClient } from './client';

export interface GiftCodeRecord {
  id: string;
  masked_code: string;
  raw_code?: string | null;
  code_type: 'gift';
  status: string;
  issuer_type: string;
  source_type?: string | null;
  plan_family?: string | null;
  duration_days?: number | null;
  recipient_hint?: string | null;
  gift_message?: string | null;
  expires_at?: string | null;
  created_at: string;
  redeemed_at?: string | null;
  redeemed_by_user_id?: string | null;
  source_order_id?: string | null;
  source_payment_id?: string | null;
}

export interface GiftPurchaseRequest {
  storefront_key?: string | null;
  plan_id: string;
  use_wallet?: number;
  currency?: string;
  channel?: string;
  recipient_hint?: string | null;
  gift_message?: string | null;
}

export interface GiftPurchaseQuoteResponse {
  quote: CheckoutQuoteResponse;
}

export interface GiftPurchaseCommitResponse {
  quote: CheckoutQuoteResponse;
  payment_id?: string | null;
  status: string;
  invoice?: CheckoutCommitResponse['invoice'] | null;
  gift_code?: GiftCodeRecord | null;
}

export interface GiftRedeemResponse {
  gift_code: GiftCodeRecord;
  entitlement_grant_id: string;
  entitlement_snapshot: Record<string, unknown>;
}

export const giftsApi = {
  quotePurchase: (data: GiftPurchaseRequest) =>
    apiClient.post<GiftPurchaseQuoteResponse>('/gifts/purchase/quote', data),

  commitPurchase: (data: GiftPurchaseRequest) =>
    apiClient.post<GiftPurchaseCommitResponse>('/gifts/purchase/commit', data),

  listMyGifts: () =>
    apiClient.get<GiftCodeRecord[]>('/gifts/my'),

  redeem: (data: { code: string }) =>
    apiClient.post<GiftRedeemResponse>('/gifts/redeem', data),
};

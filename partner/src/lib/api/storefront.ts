import { apiClient } from './client';
import type { components, operations } from './generated/types';

export type OfferResponse = components['schemas']['OfferResponse'];
export type PricebookResponse = components['schemas']['PricebookResponse'];
export type LegalDocumentSetResponse = components['schemas']['LegalDocumentSetResponse'];
export type LegalDocumentResponse = components['schemas']['LegalDocumentResponse'];
export type AcceptedLegalDocumentResponse = components['schemas']['AcceptedLegalDocumentResponse'];
export type CreatePolicyAcceptanceRequest =
  operations['create_policy_acceptance_api_v1_policy_acceptance__post']['requestBody']['content']['application/json'];
export type ListMyPolicyAcceptanceResponse =
  operations['list_my_policy_acceptance_api_v1_policy_acceptance_me_get']['responses'][200]['content']['application/json'];
export type ResolvePricebooksParams =
  operations['resolve_pricebooks_api_v1_pricebooks_resolve_get']['parameters']['query'];
export type ResolveLegalDocumentSetParams =
  operations['resolve_legal_document_set_api_v1_legal_documents_sets_resolve_get']['parameters']['query'];

export interface StorefrontRouteContractResponse {
  storefront_key: string;
  host: string;
  preview_api_path: string;
  customer_entry_path: string;
  route_status: 'preview' | 'inactive';
  public_launch_requires_stages?: string[];
  checkout_side_effects: boolean;
}

export interface StorefrontBrandingBoundaryResponse {
  brand_id: string;
  brand_key: string;
  brand_display_name: string;
  brand_status: string;
  allowed_customizations?: string[];
  prohibited_claims?: string[];
  legal_copy_source: string;
}

export interface StorefrontPricingOfferResponse {
  pricebook_id: string;
  pricebook_key: string;
  pricebook_display_name: string;
  currency_code: string;
  region_code?: string | null;
  offer_id: string;
  offer_key: string;
  offer_display_name: string;
  plan_id: string;
  visible_price: number;
  compare_at_price?: number | null;
  sale_channels?: string[];
  pricing_source: 'storefront_pricebook';
}

export interface StorefrontPricingBoundaryResponse {
  display_policy: string;
  finance_policy: string;
  offers?: StorefrontPricingOfferResponse[];
}

export interface StorefrontAttributionContractResponse {
  owner_type: 'direct_store' | 'affiliate' | 'reseller';
  owner_source: 'none' | 'explicit_code';
  partner_account_id?: string | null;
  partner_account_key?: string | null;
  partner_account_status?: string | null;
  partner_code_id?: string | null;
  partner_code?: string | null;
  partner_code_required_for_reseller: boolean;
  touchpoint_policy: string;
}

export interface StorefrontAnalyticsContractResponse {
  preview_records_touchpoint: boolean;
  checkout_records_storefront_origin: boolean;
  checkout_records_explicit_code: boolean;
  expected_dimensions?: string[];
}

export interface StorefrontPreviewResponse {
  storefront_id: string;
  storefront_key: string;
  display_name: string;
  status: string;
  route_contract: StorefrontRouteContractResponse;
  branding_boundary: StorefrontBrandingBoundaryResponse;
  pricing_boundary: StorefrontPricingBoundaryResponse;
  attribution_contract: StorefrontAttributionContractResponse;
  analytics_contract: StorefrontAnalyticsContractResponse;
  generated_at: string;
}

export const storefrontApi = {
  listOffers: (params?: { sale_channel?: string | null; subscription_plan_id?: string | null }) =>
    apiClient.get<OfferResponse[]>('/offers/', { params }),

  resolvePricebooks: (params: ResolvePricebooksParams) =>
    apiClient.get<PricebookResponse[]>('/pricebooks/resolve', { params }),

  listLegalDocuments: (params?: { document_type?: string | null; locale?: string | null }) =>
    apiClient.get<LegalDocumentResponse[]>('/legal-documents/', { params }),

  resolveLegalDocumentSet: (params: ResolveLegalDocumentSetParams) =>
    apiClient.get<LegalDocumentSetResponse>('/legal-documents/sets/resolve', { params }),

  createPolicyAcceptance: (data: CreatePolicyAcceptanceRequest) =>
    apiClient.post<AcceptedLegalDocumentResponse>('/policy-acceptance/', data),

  listMyPolicyAcceptance: () =>
    apiClient.get<ListMyPolicyAcceptanceResponse>('/policy-acceptance/me'),

  previewContract: (storefrontKey: string, params?: { partner_code?: string | null }) =>
    apiClient.get<StorefrontPreviewResponse>(
      `/storefronts/${encodeURIComponent(storefrontKey)}/preview`,
      { params },
    ),
};

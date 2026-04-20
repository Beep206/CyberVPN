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
};

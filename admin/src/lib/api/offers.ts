import { apiClient } from './client';
import type { operations } from './generated/types';

type ListOffersOperation = operations['list_offers_api_v1_offers__get'];
type ListAdminOffersOperation =
  operations['list_admin_offers_api_v1_offers_admin_get'];
type CreateOfferOperation = operations['create_offer_api_v1_offers__post'];

export type OffersResponse =
  ListOffersOperation['responses'][200]['content']['application/json'];
export type OfferRecord = OffersResponse[number];
export type ListOffersParams = ListOffersOperation['parameters']['query'];
export type AdminOffersResponse =
  ListAdminOffersOperation['responses'][200]['content']['application/json'];
export type ListAdminOffersParams =
  ListAdminOffersOperation['parameters']['query'];
export type CreateOfferRequest =
  CreateOfferOperation['requestBody']['content']['application/json'];
export type CreateOfferResponse =
  CreateOfferOperation['responses'][201]['content']['application/json'];

export const offersApi = {
  list: (params?: ListOffersParams) =>
    apiClient.get<OffersResponse>('/offers/', { params }),

  listAdmin: (params?: ListAdminOffersParams) =>
    apiClient.get<AdminOffersResponse>('/offers/admin', { params }),

  create: (data: CreateOfferRequest) =>
    apiClient.post<CreateOfferResponse>('/offers/', data),
};

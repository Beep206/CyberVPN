import { apiClient, resolveApiBaseUrl } from './client';
import type { components, operations } from './generated/types';

export type PrivateCatalogPreflightRequest =
  operations['preflight_growth_code_set_api_v3_growth_code_sets_preflight_post']['requestBody']['content']['application/json'];
export type PrivateCatalogPreflightResponse =
  operations['preflight_growth_code_set_api_v3_growth_code_sets_preflight_post']['responses'][200]['content']['application/json'];
export type PrivateCatalogPreflightOffer = components['schemas']['CodeSetPrivateOfferResponse'];

function resolveApiV3BaseUrl(): string {
  return resolveApiBaseUrl().replace(/\/api\/v1$/, '/api/v3');
}

export const privateCatalogApi = {
  preflight: (data: PrivateCatalogPreflightRequest) =>
    apiClient.post<PrivateCatalogPreflightResponse>('/growth/code-sets/preflight', data, {
      baseURL: resolveApiV3BaseUrl(),
    }),
};

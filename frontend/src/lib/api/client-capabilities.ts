import { AxiosError, type AxiosResponse } from 'axios';
import { apiClient } from './client';
import type { components, operations } from './generated/types';

type GetClientCapabilitiesOperation =
  operations['get_client_capabilities_api_v1_client_capabilities_get'];

export type ClientCapabilitiesResponse =
  GetClientCapabilitiesOperation['responses'][200]['content']['application/json'];
export type ClientAuthCapabilities =
  components['schemas']['ClientAuthCapabilities'];
export type ClientPaymentCapabilities =
  components['schemas']['ClientPaymentCapabilities'];
export type ClientGrowthCapabilities =
  components['schemas']['ClientGrowthCapabilities'];
export type ClientSubscriptionCapabilities =
  components['schemas']['ClientSubscriptionCapabilities'];
export type ClientPartnerCapabilities =
  components['schemas']['ClientPartnerCapabilities'];
export type ClientSiteCapabilities =
  components['schemas']['ClientSiteCapabilities'];
export type ClientOnboardingCapabilities =
  components['schemas']['ClientOnboardingCapabilities'];

function rejectPublicCapabilityResponse(
  response: AxiosResponse<ClientCapabilitiesResponse>,
): never {
  throw new AxiosError(
    `Request failed with status code ${response.status}`,
    AxiosError.ERR_BAD_REQUEST,
    response.config,
    response.request,
    response,
  );
}

export const clientCapabilitiesApi = {
  get: async () => {
    const response = await apiClient.get<ClientCapabilitiesResponse>(
      '/client/capabilities',
      {
        validateStatus: (status) =>
          (status >= 200 && status < 300) || status === 401,
      },
    );

    if (response.status === 401) {
      rejectPublicCapabilityResponse(response);
    }

    return response;
  },
};

import { apiClient } from './client';
import type { components, operations } from './generated/types';

export type CurrentEntitlementStateResponse = components['schemas']['CurrentEntitlementStateResponse'];
export type GetCurrentServiceStateRequest =
  operations['get_current_service_state_api_v1_access_delivery_channels_current_service_state_post']['requestBody']['content']['application/json'];
export type CurrentServiceStateResponse = components['schemas']['CurrentServiceStateResponse'];

export const DEFAULT_SERVICE_STATE_REQUEST: GetCurrentServiceStateRequest = {
  provider_name: 'remnawave',
  channel_type: 'shared_client',
  credential_type: 'desktop_client',
  credential_subject_key: 'official-web-dashboard',
};

export const entitlementsApi = {
  getCurrent: () =>
    apiClient.get<CurrentEntitlementStateResponse>('/entitlements/current'),
};

export const serviceAccessApi = {
  getCurrentServiceState: (data: GetCurrentServiceStateRequest = DEFAULT_SERVICE_STATE_REQUEST) =>
    apiClient.post<CurrentServiceStateResponse>('/access-delivery-channels/current/service-state', data),
};

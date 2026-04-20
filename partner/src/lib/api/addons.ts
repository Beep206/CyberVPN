import { apiClient } from './client';
import type { operations } from './generated/types';

type ListAddonCatalogOperation = operations['list_addon_catalog_api_v1_addons_catalog_get'];
type ListAdminAddonsOperation = operations['list_admin_addons_api_v1_addons_get'];

export type AddonsCatalogResponse =
  ListAddonCatalogOperation['responses'][200]['content']['application/json'];
export type AdminAddonsResponse =
  ListAdminAddonsOperation['responses'][200]['content']['application/json'];
export type AddonRecord = AddonsCatalogResponse[number];
export type ListAddonsCatalogParams = ListAddonCatalogOperation['parameters']['query'];
export type ListAdminAddonsParams = ListAdminAddonsOperation['parameters']['query'];
export type CreateAddonRequest =
  operations['create_addon_api_v1_addons_post']['requestBody']['content']['application/json'];
export type CreateAddonResponse =
  operations['create_addon_api_v1_addons_post']['responses'][201]['content']['application/json'];
export type UpdateAddonRequest =
  operations['update_addon_api_v1_addons__addon_id__put']['requestBody']['content']['application/json'];
export type UpdateAddonResponse =
  operations['update_addon_api_v1_addons__addon_id__put']['responses'][200]['content']['application/json'];

export const addonsApi = {
  listCatalog: (params?: ListAddonsCatalogParams) =>
    apiClient.get<AddonsCatalogResponse>('/addons/catalog', { params }),

  listAdmin: (params?: ListAdminAddonsParams) =>
    apiClient.get<AdminAddonsResponse>('/addons', { params }),

  create: (data: CreateAddonRequest) =>
    apiClient.post<CreateAddonResponse>('/addons', data),

  update: (addonId: string, data: UpdateAddonRequest) =>
    apiClient.put<UpdateAddonResponse>(`/addons/${addonId}`, data),
};

import { apiClient } from './client';
import type { operations } from './generated/types';

type ListAddonCatalogOperation = operations['list_addon_catalog_api_v1_addons_catalog_get'];

export type AddonsCatalogResponse =
  ListAddonCatalogOperation['responses'][200]['content']['application/json'];
export type AddonRecord = AddonsCatalogResponse[number];
export type ListAddonsCatalogParams = ListAddonCatalogOperation['parameters']['query'];

export const addonsApi = {
  listCatalog: (params?: ListAddonsCatalogParams) =>
    apiClient.get<AddonsCatalogResponse>('/addons/catalog', { params }),
};

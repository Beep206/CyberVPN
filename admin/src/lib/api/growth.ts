import { apiClient } from './client';
import type { operations } from './generated/types';

type AdminListPromosResponse =
  operations['admin_list_promos_api_v1_admin_promo_codes_get']['responses'][200]['content']['application/json'];
type AdminCreatePromoRequest =
  operations['admin_create_promo_api_v1_admin_promo_codes_post']['requestBody']['content']['application/json'];
type AdminCreatePromoResponse =
  operations['admin_create_promo_api_v1_admin_promo_codes_post']['responses'][201]['content']['application/json'];
type AdminGetPromoResponse =
  operations['admin_get_promo_api_v1_admin_promo_codes__promo_id__get']['responses'][200]['content']['application/json'];
type AdminUpdatePromoRequest =
  operations['admin_update_promo_api_v1_admin_promo_codes__promo_id__put']['requestBody']['content']['application/json'];
type AdminUpdatePromoResponse =
  operations['admin_update_promo_api_v1_admin_promo_codes__promo_id__put']['responses'][200]['content']['application/json'];
type AdminDeactivatePromoResponse =
  operations['admin_deactivate_promo_api_v1_admin_promo_codes__promo_id__delete']['responses'][200]['content']['application/json'];
type AdminCreateInviteCodesRequest =
  operations['admin_create_invites_api_v1_admin_invite_codes_post']['requestBody']['content']['application/json'];
type AdminCreateInviteCodesResponse =
  operations['admin_create_invites_api_v1_admin_invite_codes_post']['responses'][201]['content']['application/json'];
type AdminPromotePartnerRequest =
  operations['admin_promote_partner_api_v1_admin_partners_promote_post']['requestBody']['content']['application/json'];
type AdminPromotePartnerResponse =
  operations['admin_promote_partner_api_v1_admin_partners_promote_post']['responses'][200]['content']['application/json'];
type AdminReferralOverviewResponse =
  operations['get_referral_overview_api_v1_admin_referrals_overview_get']['responses'][200]['content']['application/json'];
type AdminReferralUserDetailResponse =
  operations['get_referral_user_detail_api_v1_admin_referrals_users__user_id__get']['responses'][200]['content']['application/json'];
type AdminPartnersListResponse =
  operations['list_partners_api_v1_admin_partners_get']['responses'][200]['content']['application/json'];
type AdminPartnersListParams =
  operations['list_partners_api_v1_admin_partners_get']['parameters']['query'];
type AdminPartnerDetailResponse =
  operations['get_partner_detail_api_v1_admin_partners__user_id__get']['responses'][200]['content']['application/json'];

/**
 * Growth API client
 * Covers admin-ready acquisition and promotion surfaces.
 */
export const growthApi = {
  listPromos: (params?: { offset?: number; limit?: number }) =>
    apiClient.get<AdminListPromosResponse>('/admin/promo-codes', { params }),

  createPromo: (data: AdminCreatePromoRequest) =>
    apiClient.post<AdminCreatePromoResponse>('/admin/promo-codes', data),

  getPromo: (promoId: string) =>
    apiClient.get<AdminGetPromoResponse>(`/admin/promo-codes/${promoId}`),

  updatePromo: (promoId: string, data: AdminUpdatePromoRequest) =>
    apiClient.put<AdminUpdatePromoResponse>(`/admin/promo-codes/${promoId}`, data),

  deactivatePromo: (promoId: string) =>
    apiClient.delete<AdminDeactivatePromoResponse>(`/admin/promo-codes/${promoId}`),

  createInviteCodes: (data: AdminCreateInviteCodesRequest) =>
    apiClient.post<AdminCreateInviteCodesResponse>('/admin/invite-codes', data),

  promotePartner: (data: AdminPromotePartnerRequest) =>
    apiClient.post<AdminPromotePartnerResponse>('/admin/partners/promote', data),

  getReferralOverview: () =>
    apiClient.get<AdminReferralOverviewResponse>('/admin/referrals/overview'),

  getReferralUserDetail: (userId: string) =>
    apiClient.get<AdminReferralUserDetailResponse>(`/admin/referrals/users/${userId}`),

  listPartners: (params?: AdminPartnersListParams) =>
    apiClient.get<AdminPartnersListResponse>('/admin/partners', { params }),

  getPartnerDetail: (userId: string) =>
    apiClient.get<AdminPartnerDetailResponse>(`/admin/partners/${userId}`),
};

export type {
  AdminCreateInviteCodesRequest,
  AdminCreateInviteCodesResponse,
  AdminPartnerDetailResponse,
  AdminPartnersListParams,
  AdminPartnersListResponse,
  AdminCreatePromoRequest,
  AdminCreatePromoResponse,
  AdminDeactivatePromoResponse,
  AdminGetPromoResponse,
  AdminListPromosResponse,
  AdminPromotePartnerRequest,
  AdminPromotePartnerResponse,
  AdminReferralOverviewResponse,
  AdminReferralUserDetailResponse,
  AdminUpdatePromoRequest,
  AdminUpdatePromoResponse,
};

import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type RedeemInviteRequest = operations['redeem_invite_api_v1_invites_redeem_post']['requestBody']['content']['application/json'];
type RedeemInviteResponse = operations['redeem_invite_api_v1_invites_redeem_post']['responses'][200]['content']['application/json'];
type MyInvitesResponse = operations['list_my_invites_api_v1_invites_my_get']['responses'][200]['content']['application/json'];

/**
 * Invites API client
 * Manages invite code redemption and user's invite codes
 */
export const invitesApi = {
  /**
   * Redeem an invite code
   * POST /api/v1/invites/redeem
   *
   * Redeems an invite code for the authenticated user.
   * Returns rewards or benefits associated with the code.
   *
   * @param data - Invite code to redeem
   * @throws 404 - Invite code not found or expired
   * @throws 400 - Code already redeemed or invalid
   */
  redeem: (data: RedeemInviteRequest) =>
    apiClient.post<RedeemInviteResponse>('/invites/redeem', data),

  /**
   * Get authenticated user's invite codes
   * GET /api/v1/invites/my
   *
   * Returns all invite codes created by or for the authenticated user.
   */
  getMyInvites: () =>
    apiClient.get<MyInvitesResponse>('/invites/my'),
};

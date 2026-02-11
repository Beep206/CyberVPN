import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type GetProfileResponse = operations['get_profile_api_v1_users_me_profile_get']['responses'][200]['content']['application/json'];
type UpdateProfileRequest = operations['update_profile_api_v1_users_me_profile_patch']['requestBody']['content']['application/json'];
type UpdateProfileResponse = operations['update_profile_api_v1_users_me_profile_patch']['responses'][200]['content']['application/json'];

/**
 * Profile API client
 * Manages authenticated user profile data
 */
export const profileApi = {
  /**
   * Get current authenticated user's profile
   * GET /api/v1/users/me/profile
   *
   * Returns profile with display name, avatar, language, timezone settings.
   * Note: Currently returns placeholder data from AdminUserModel.
   */
  getProfile: () =>
    apiClient.get<GetProfileResponse>('/users/me/profile'),

  /**
   * Update current authenticated user's profile
   * PATCH /api/v1/users/me/profile
   *
   * Partially updates profile fields. Only provided fields are updated.
   * Note: Currently a placeholder - changes are not persisted to database.
   *
   * @param data - Partial profile update (display_name, avatar_url, language, timezone)
   */
  updateProfile: (data: UpdateProfileRequest) =>
    apiClient.patch<UpdateProfileResponse>('/users/me/profile', data),
};

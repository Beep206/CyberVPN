import { apiClient } from './client';
import type { operations } from './generated/types';

// Extract types from OpenAPI operations
type TrialStatusResponse = operations['get_trial_status_api_v1_trial_status_get']['responses'][200]['content']['application/json'];
type TrialActivateResponse = operations['activate_trial_api_v1_trial_activate_post']['responses'][200]['content']['application/json'];

/**
 * Trial API client
 * Manages user trial period activation and status
 */
export const trialApi = {
  /**
   * Get trial status for authenticated user
   * GET /api/v1/trial/status
   *
   * Returns whether user is currently on trial, eligibility,
   * and trial period dates.
   */
  getStatus: () =>
    apiClient.get<TrialStatusResponse>('/trial/status'),

  /**
   * Activate trial period for authenticated user
   * POST /api/v1/trial/activate
   *
   * Activates a 7-day trial period. Returns activation confirmation
   * and trial end date.
   */
  activate: () =>
    apiClient.post<TrialActivateResponse>('/trial/activate', {}),
};

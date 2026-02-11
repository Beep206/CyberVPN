/**
 * CyberVPN API Client Index
 *
 * Centralized exports for all API client modules.
 * Each module follows the pattern established in auth.ts:
 * - Uses apiClient from client.ts for HTTP calls
 * - Imports types from generated/types.ts (OpenAPI schema)
 * - Provides typed request/response interfaces
 * - Includes JSDoc comments for all endpoints
 */

// Authentication
export { authApi } from './auth';

// User Management
export { profileApi } from './profile';
export { vpnApi } from './vpn';
export { trialApi } from './trial';
export { partnerApi } from './partner';
export { usageApi } from './usage';

// Financial
export { walletApi } from './wallet';
export { paymentsApi } from './payments';
export { codesApi } from './codes';
export { referralApi } from './referral';
export { promoApi } from './promo';
export { invitesApi } from './invites';

// Subscriptions
export { subscriptionsApi } from './subscriptions';
export { plansApi } from './plans';

// Infrastructure
export { serversApi } from './servers';
export { monitoringApi } from './monitoring';

// Security
export { twofaApi } from './twofa';
export { securityApi } from './security';

// Core Client & Types
export { apiClient, RateLimitError } from './client';
export type { AxiosError } from './client';

/**
 * Re-export commonly used auth types for convenience
 */
export type {
  User,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  TokenResponse,
  OAuthProvider,
} from './auth';

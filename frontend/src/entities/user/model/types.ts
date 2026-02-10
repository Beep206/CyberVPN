import type { components } from '@/lib/api/generated/types';

/** Backend enum from OpenAPI: "active" | "disabled" | "limited" | "expired" */
export type BackendUserStatus = components['schemas']['UserStatus'];

/**
 * Extended for admin UI — includes "banned" and "trial" which the backend
 * doesn't yet expose. Once the backend schema aligns, replace with BackendUserStatus.
 */
export type UserStatus = BackendUserStatus | 'banned' | 'trial';

/**
 * Frontend-only display model for the users data grid.
 * The backend UserResponse uses a different shape (uuid, username,
 * short_uuid, traffic_limit_bytes, etc.) and different field names,
 * so this type is intentionally kept hand-written as a presentation-layer model.
 */
export interface User {
    id: string;
    email: string;
    plan: 'basic' | 'pro' | 'ultra' | 'cyber';
    status: UserStatus;
    dataUsage: number; // GB used
    dataLimit: number; // GB limit
    expiresAt: string;
    lastActive: string;
}

export type UserStatus = 'active' | 'expired' | 'banned' | 'trial';

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

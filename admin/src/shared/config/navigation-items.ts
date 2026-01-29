import { Activity, Server, Users, CreditCard, BarChart3, Shield, Settings } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

export interface MenuItem {
    icon: LucideIcon;
    labelKey: string;
    href: string;
}

export const menuItems: MenuItem[] = [
    { icon: Activity, labelKey: 'dashboard', href: '/dashboard' },
    { icon: Server, labelKey: 'servers', href: '/servers' },
    { icon: Users, labelKey: 'users', href: '/users' },
    { icon: CreditCard, labelKey: 'billing', href: '/subscriptions' },
    { icon: BarChart3, labelKey: 'analytics', href: '/analytics' },
    { icon: Shield, labelKey: 'security', href: '/monitoring' },
    { icon: Settings, labelKey: 'settings', href: '/settings' },
];

'use client';

import { useIsMiniApp } from '@/stores/auth-store';

/**
 * Hides navigation elements in Telegram Mini App mode.
 * In Mini App context, Telegram provides its own back button and navigation.
 */
export function MiniAppNavGuard({ children }: { children: React.ReactNode }) {
    const isMiniApp = useIsMiniApp();

    if (isMiniApp) return null;

    return <>{children}</>;
}

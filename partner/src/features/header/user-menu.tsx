'use client';

import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { LayoutDashboard, LogOut } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Link, useRouter } from '@/i18n/navigation';
import { MagneticButton } from '@/shared/ui/magnetic-button';
import { useAuthStore } from '@/stores/auth-store';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

function formatRoleLabel(role?: string): string {
    return role ? role.replace(/_/g, ' ').toUpperCase() : 'PARTNER';
}

export function UserMenu() {
    const [isOpen, setIsOpen] = useState(false);
    const router = useRouter();
    const { user, logout } = useAuthStore();
    const navigationT = useTranslations('Navigation');
    const logoutT = useTranslations('Auth.logout');
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleLogout = async () => {
        await logout();
        setIsOpen(false);
        router.push('/login');
    };

    const initials = user?.email
        ? user.email.substring(0, 2).toUpperCase()
        : user?.login?.substring(0, 2).toUpperCase() || 'U';
    const primaryIdentity = user?.login || user?.email?.split('@')[0] || 'PARTNER';
    const roleLabel = formatRoleLabel(user?.role);

    return (
        <div className="relative z-50" ref={dropdownRef}>
            <MagneticButton strength={10}>
                <button
                    type="button"
                    onClick={() => setIsOpen((current) => !current)}
                    aria-label={navigationT('adminConsole')}
                    className={[
                        'group relative flex items-center gap-2 overflow-hidden rounded-full border p-1 pl-2 pr-1 transition-all duration-300',
                        isOpen
                            ? 'border-neon-cyan/50 bg-muted/40 ring-2 ring-neon-cyan/20'
                            : 'border-transparent bg-muted/20 hover:border-white/10 hover:bg-muted/40',
                    ].join(' ')}
                >
                    <span className="relative z-10 hidden max-w-[100px] truncate text-xs font-medium md:block">
                        {primaryIdentity}
                    </span>

                    <span className="absolute left-2 top-1/2 h-1.5 w-1.5 -translate-y-1/2 animate-pulse rounded-full bg-matrix-green shadow-[0_0_8px_theme(colors.matrix-green.DEFAULT)]" />

                    <Avatar className="h-8 w-8 border border-white/10 transition-colors group-hover:border-neon-cyan/50">
                        <AvatarFallback className="bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 text-xs font-bold text-foreground">
                            {initials}
                        </AvatarFallback>
                    </Avatar>
                </button>
            </MagneticButton>

            <AnimatePresence>
                {isOpen ? (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.96 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.96 }}
                        transition={{ duration: 0.18, ease: 'easeOut' }}
                        className="absolute right-0 top-full mt-3 z-50 w-72 overflow-hidden rounded-2xl border border-white/10 bg-terminal-surface/95 shadow-[0_20px_60px_-24px_rgba(0,0,0,0.8)] backdrop-blur-2xl"
                    >
                        <div className="relative overflow-hidden border-b border-grid-line/20 p-4">
                            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(0,255,255,0.12),transparent_40%),radial-gradient(circle_at_bottom_left,rgba(255,0,255,0.12),transparent_35%)]" />
                            <div className="relative z-10 flex items-center gap-3">
                                <Avatar className="h-11 w-11 border border-neon-cyan/30">
                                    <AvatarFallback className="bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 text-sm font-bold text-foreground">
                                        {initials}
                                    </AvatarFallback>
                                </Avatar>

                                <div className="min-w-0 flex-1">
                                    <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-neon-cyan/80">
                                        {navigationT('adminConsole')}
                                    </div>
                                    <div className="truncate text-sm font-medium text-foreground">
                                        {primaryIdentity}
                                    </div>
                                    <div className="mt-1">
                                        <span className="rounded-full border border-neon-cyan/25 bg-neon-cyan/10 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.16em] text-neon-cyan">
                                            {roleLabel}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="p-2">
                            <Link
                                href="/dashboard"
                                onClick={() => setIsOpen(false)}
                                className="group flex items-center gap-3 rounded-xl px-3 py-3 text-sm transition-colors hover:bg-white/5"
                            >
                                <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-neon-cyan/20 bg-neon-cyan/10 text-neon-cyan">
                                    <LayoutDashboard className="h-4 w-4" />
                                </div>

                                <div className="min-w-0 flex-1">
                                    <div className="font-medium text-foreground">
                                        {navigationT('dashboard')}
                                    </div>
                                    <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                                        {navigationT('secureSession')}
                                    </div>
                                </div>
                            </Link>
                        </div>

                        <div className="border-t border-grid-line/20 p-2">
                            <button
                                type="button"
                                onClick={handleLogout}
                                className="flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2.5 text-sm font-medium text-red-300 transition-colors hover:bg-red-500/10 hover:text-red-200"
                            >
                                <LogOut className="h-4 w-4" />
                                <span>{logoutT('button')}</span>
                            </button>
                        </div>
                    </motion.div>
                ) : null}
            </AnimatePresence>
        </div>
    );
}

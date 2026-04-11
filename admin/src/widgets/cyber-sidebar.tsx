'use client';

import { Shield } from 'lucide-react';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { Link, usePathname } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';
import {
    DASHBOARD_NAV_ITEMS,
    DASHBOARD_NAV_LABEL_FALLBACKS,
} from '@/widgets/dashboard-navigation';
import { useAuthStore } from '@/stores/auth-store';

export function CyberSidebar() {
    const pathname = usePathname();
    const t = useTranslations('Navigation');
    const user = useAuthStore((state) => state.user);
    const labelFor = (key: keyof typeof DASHBOARD_NAV_LABEL_FALLBACKS) => {
        try {
            return t(key);
        } catch {
            return DASHBOARD_NAV_LABEL_FALLBACKS[key];
        }
    };
    const operatorLabel = user?.login || user?.email?.split('@')[0] || 'ADMIN';
    const accessLabel = user?.role
        ? user.role.replace(/_/g, ' ').toUpperCase()
        : labelFor('secureSession');

    return (
        <aside
            aria-label={labelFor('sidebar')}
            className="fixed left-0 top-0 z-40 hidden h-dvh w-64 flex-col border-r border-grid-line/30 bg-terminal-surface/90 backdrop-blur-md md:flex"
        >
            <div className="flex h-16 items-center border-b border-grid-line/30 px-6">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan shadow-[0_0_18px_rgba(0,255,255,0.18)]">
                        <Shield className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                        <div className="font-display text-sm uppercase tracking-[0.26em] text-foreground">
                            OZOXY
                        </div>
                        <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan/80">
                            ADMIN
                        </div>
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto py-6 px-4">
                <nav aria-label={labelFor('mainNavigation')} className="grid gap-2">
                    {DASHBOARD_NAV_ITEMS.map((item) => {
                        const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
                        const Icon = item.icon;
                        const label = labelFor(item.labelKey);
                        const hint = labelFor(item.hintKey);

                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                aria-label={label}
                                aria-current={isActive ? 'page' : undefined}
                                className="group relative block overflow-hidden rounded-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-surface focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
                            >
                                {isActive && (
                                    <motion.div
                                        layoutId="sidebar-active"
                                        className="absolute inset-0 bg-neon-cyan/10 border-l-2 border-neon-cyan"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                    >
                                        <div className="absolute inset-0 bg-gradient-to-r from-neon-cyan/20 to-transparent" />
                                    </motion.div>
                                )}

                                <div className={cn(
                                    "relative flex items-start gap-3 px-4 py-3 text-sm font-mono transition-all duration-300",
                                    isActive ? "text-neon-cyan translate-x-1" : "text-muted-foreground group-hover:text-foreground group-hover:translate-x-1"
                                )}>
                                    <Icon className={cn(
                                        "mt-0.5 h-4 w-4 shrink-0 transition-transform duration-300",
                                        isActive ? "drop-shadow-[0_0_8px_cyan]" : "group-hover:scale-110 group-hover:drop-shadow-[0_0_5px_white]"
                                    )} />

                                    <span className="relative min-w-0 flex-1">
                                        <span className="relative block tracking-wide">
                                            <CypherText
                                                text={label}
                                                className="group-hover:text-neon-cyan transition-colors duration-300"
                                                speed={30}
                                            />
                                            <span aria-hidden="true" className="absolute left-0 top-0 -translate-x-[2px] opacity-0 text-neon-pink mix-blend-screen group-hover:opacity-100 group-hover:animate-pulse">
                                                {label}
                                            </span>
                                            <span aria-hidden="true" className="absolute left-0 top-0 translate-x-[2px] opacity-0 text-neon-cyan mix-blend-screen group-hover:opacity-100 group-hover:animate-pulse animation-delay-75">
                                                {label}
                                            </span>
                                        </span>
                                        <span className={cn(
                                            'mt-1 block text-[10px] uppercase tracking-[0.18em]',
                                            isActive ? 'text-neon-cyan/70' : 'text-muted-foreground/70 group-hover:text-foreground/70',
                                        )}>
                                            {hint}
                                        </span>
                                    </span>

                                    {/* Active Indicator Dot */}
                                    {isActive && (
                                        <motion.span
                                            aria-hidden="true"
                                            layoutId="active-dot"
                                            className="absolute right-3 h-1.5 w-1.5 rounded-full bg-neon-cyan shadow-[0_0_8px_#00ffff]"
                                        />
                                    )}
                                </div>
                            </Link>
                        );
                    })}
                </nav>
            </div>

            <div className="border-t border-grid-line/30 p-4">
                <div className="rounded-2xl border border-grid-line/20 bg-sidebar-accent/50 p-4">
                    <div className="mb-3 flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-neon-purple/40 bg-neon-purple/15 text-neon-purple">
                            AD
                        </div>
                        <div className="min-w-0">
                            <div className="font-mono text-[10px] uppercase tracking-[0.22em] text-neon-cyan/80">
                                {labelFor('adminConsole')}
                            </div>
                            <div className="truncate text-sm font-medium text-foreground">
                                {operatorLabel}
                            </div>
                        </div>
                    </div>
                    <div className="rounded-xl border border-grid-line/20 bg-terminal-bg/60 px-3 py-2 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                        <span className="text-matrix-green">{accessLabel}</span>
                        <span className="mx-2 text-grid-line/60">/</span>
                        <span>{labelFor('secureSession')}</span>
                    </div>
                </div>
            </div>
        </aside>
    );
}

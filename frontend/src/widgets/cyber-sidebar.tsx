'use client';

import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { Link, usePathname } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';
import { Server, Users, Activity, CreditCard, Settings, Shield, BarChart3 } from 'lucide-react';

const menuItems = [
    { icon: Activity, labelKey: 'dashboard', href: '/dashboard' },
    { icon: Server, labelKey: 'servers', href: '/servers' },
    { icon: Users, labelKey: 'users', href: '/users' },
    { icon: CreditCard, labelKey: 'billing', href: '/subscriptions' },
    { icon: BarChart3, labelKey: 'analytics', href: '/analytics' },
    { icon: Shield, labelKey: 'security', href: '/monitoring' },
    { icon: Settings, labelKey: 'settings', href: '/settings' },
];

export function CyberSidebar() {
    const pathname = usePathname();
    const t = useTranslations('Navigation');

    return (
        <aside
            aria-label={t('sidebar')}
            className="hidden h-screen w-64 flex-col border-r border-grid-line/30 bg-terminal-surface/90 backdrop-blur-md md:flex z-40 fixed left-0 top-0"
        >
            <div className="flex h-16 items-center border-b border-grid-line/30 px-6">
                <div className="flex items-center gap-2 font-display text-xl tracking-wider text-neon-cyan drop-shadow-glow">
                    <Shield className="h-6 w-6" />
                    <span>NEXUS</span>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto py-6 px-4">
                <nav aria-label={t('mainNavigation')} className="grid gap-2">
                    {menuItems.map((item) => {
                        const isActive = pathname?.includes(item.href);
                        const Icon = item.icon;
                        const label = t(item.labelKey);

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
                                    "relative flex items-center gap-3 px-4 py-3 text-sm font-mono transition-all duration-300",
                                    isActive ? "text-neon-cyan translate-x-1" : "text-muted-foreground group-hover:text-foreground group-hover:translate-x-1"
                                )}>
                                    <Icon className={cn(
                                        "h-4 w-4 transition-transform duration-300",
                                        isActive ? "drop-shadow-[0_0_8px_cyan]" : "group-hover:scale-110 group-hover:drop-shadow-[0_0_5px_white]"
                                    )} />

                                    <span className="relative tracking-wide">
                                        <CypherText
                                            text={label}
                                            className="group-hover:text-neon-cyan transition-colors duration-300"
                                            speed={30}
                                        />
                                        {/* Glitch Overlay Text (Visible on Hover) */}
                                        <span aria-hidden="true" className="absolute top-0 left-0 -translate-x-[2px] opacity-0 text-neon-pink mix-blend-screen group-hover:opacity-100 group-hover:animate-pulse">
                                            {label}
                                        </span>
                                        <span aria-hidden="true" className="absolute top-0 left-0 translate-x-[2px] opacity-0 text-neon-cyan mix-blend-screen group-hover:opacity-100 group-hover:animate-pulse animation-delay-75">
                                            {label}
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
                <div className="rounded-lg bg-sidebar-accent/50 p-3 border border-grid-line/20">
                    <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded bg-neon-purple/20 flex items-center justify-center text-neon-purple border border-neon-purple/50">
                            AD
                        </div>
                        <div className="text-xs font-mono">
                            <div className="text-foreground">ADMIN_01</div>
                            <div className="text-muted-foreground">ROOT ACCESS</div>
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
}

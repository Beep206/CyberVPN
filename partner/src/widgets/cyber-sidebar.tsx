'use client';

import { Shield } from 'lucide-react';
import { motion } from 'motion/react';
import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth-store';
import { PartnerWorkspaceSwitcher } from '@/features/partner-portal-state/components/partner-workspace-switcher';
import { usePartnerPortalBootstrapState } from '@/features/partner-portal-state/lib/use-partner-portal-bootstrap-state';
import {
    getPartnerNavGroups,
    type PartnerNavPresentationState,
} from '@/features/partner-shell/lib/partner-nav-presentation';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { DASHBOARD_NAV_LABEL_FALLBACKS } from '@/widgets/dashboard-navigation';

function badgeClassName(state: PartnerNavPresentationState) {
    if (state === 'task') {
        return 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink';
    }

    if (state === 'limited') {
        return 'border-neon-purple/45 bg-neon-purple/10 text-neon-purple';
    }

    return 'border-grid-line/25 bg-terminal-bg/70 text-muted-foreground';
}

export function CyberSidebar() {
    const pathname = usePathname();
    const t = useTranslations('Navigation');
    const user = useAuthStore((state) => state.user);
    const { state: portalState } = usePartnerPortalBootstrapState();
    const labelFor = (key: keyof typeof DASHBOARD_NAV_LABEL_FALLBACKS) => {
        try {
            return t(key);
        } catch {
            return DASHBOARD_NAV_LABEL_FALLBACKS[key];
        }
    };
    const operatorLabel = user?.login || user?.email?.split('@')[0] || 'PARTNER';
    const accessLabel = portalState.workspaceRole.replace(/_/g, ' ').toUpperCase();
    const navGroups = getPartnerNavGroups(portalState);

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
                            PARTNER
                        </div>
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-6">
                <nav aria-label={labelFor('mainNavigation')} className="space-y-5">
                    {navGroups.map((group) => (
                        <section key={group.id} aria-labelledby={`partner-sidebar-${group.id}`}>
                            <div className="mb-2 px-3">
                                <h2
                                    id={`partner-sidebar-${group.id}`}
                                    className="font-mono text-[10px] uppercase tracking-[0.24em] text-neon-cyan/70"
                                >
                                    {labelFor(group.labelKey)}
                                </h2>
                                <p className="mt-1 text-[10px] font-mono uppercase tracking-[0.14em] text-muted-foreground-low">
                                    {labelFor(group.hintKey)}
                                </p>
                            </div>

                            <div className="grid gap-1.5">
                                {group.items.map(({ item, presentation }) => {
                                    const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
                                    const Icon = item.icon;
                                    const label = labelFor(item.labelKey);
                                    const hint = labelFor(item.hintKey);
                                    const badgeLabel = presentation.badgeKey
                                        ? labelFor(presentation.badgeKey)
                                        : null;

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
                                                    className="absolute inset-0 border-l-2 border-neon-cyan bg-neon-cyan/10"
                                                    initial={{ opacity: 0 }}
                                                    animate={{ opacity: 1 }}
                                                    exit={{ opacity: 0 }}
                                                >
                                                    <div className="absolute inset-0 bg-gradient-to-r from-neon-cyan/20 to-transparent" />
                                                </motion.div>
                                            )}

                                            <div className={cn(
                                                'relative flex items-start gap-3 px-4 py-3 text-sm font-mono transition-all duration-300',
                                                isActive ? 'translate-x-1 text-neon-cyan' : 'text-muted-foreground group-hover:translate-x-1 group-hover:text-foreground',
                                            )}>
                                                <Icon className={cn(
                                                    'mt-0.5 h-4 w-4 shrink-0 transition-transform duration-300',
                                                    isActive ? 'drop-shadow-[0_0_8px_cyan]' : 'group-hover:scale-110 group-hover:drop-shadow-[0_0_5px_white]',
                                                )} />

                                                <span className="relative min-w-0 flex-1">
                                                    <span className="relative block tracking-wide">
                                                        <CypherText
                                                            text={label}
                                                            className="transition-colors duration-300 group-hover:text-neon-cyan"
                                                            speed={30}
                                                        />
                                                        <span aria-hidden="true" className="absolute left-0 top-0 -translate-x-[2px] text-neon-pink opacity-0 mix-blend-screen group-hover:animate-pulse group-hover:opacity-100">
                                                            {label}
                                                        </span>
                                                        <span aria-hidden="true" className="animation-delay-75 absolute left-0 top-0 translate-x-[2px] text-neon-cyan opacity-0 mix-blend-screen group-hover:animate-pulse group-hover:opacity-100">
                                                            {label}
                                                        </span>
                                                    </span>
                                                    <span className={cn(
                                                        'mt-1 block text-[10px] uppercase tracking-[0.18em]',
                                                        isActive ? 'text-neon-cyan' : 'text-muted-foreground-low group-hover:text-foreground',
                                                    )}>
                                                        {hint}
                                                    </span>
                                                    {badgeLabel ? (
                                                        <span className={cn(
                                                            'mt-2 inline-flex rounded-full border px-2 py-0.5 text-[9px] uppercase tracking-[0.16em]',
                                                            badgeClassName(presentation.state),
                                                        )}>
                                                            {badgeLabel}
                                                        </span>
                                                    ) : null}
                                                </span>

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
                            </div>
                        </section>
                    ))}
                </nav>
            </div>

            <div className="border-t border-grid-line/30 p-4">
                <div className="space-y-4">
                    <PartnerWorkspaceSwitcher />

                    <div className="rounded-2xl border border-grid-line/20 bg-sidebar-accent/50 p-4">
                        <div className="mb-3 flex items-center gap-3">
                            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-neon-purple/50 bg-neon-purple/15 text-neon-purple">
                                PT
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
            </div>
        </aside>
    );
}

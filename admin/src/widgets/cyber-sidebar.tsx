'use client';

import { useState } from 'react';
import { ChevronDown, Shield } from 'lucide-react';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { Link, usePathname } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { motion } from 'motion/react';
import {
    getAdminActiveNavItem,
    isAdminNavGroupActive,
    resolveAdminNavigationGroups,
} from '@/features/admin-shell/config/admin-navigation';
import {
    formatAdminQueueBadge,
    useAdminActionQueues,
} from '@/features/admin-shell/hooks/use-admin-action-queues';
import type {
    AdminNavGroupId,
    ResolvedAdminNavItem,
} from '@/features/admin-shell/config/admin-navigation';
import {
    DASHBOARD_NAV_LABEL_FALLBACKS,
} from '@/widgets/dashboard-navigation';
import { useAuthStore } from '@/stores/auth-store';

const DEFAULT_EXPANDED_GROUP_IDS: readonly AdminNavGroupId[] = ['operations'];

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
    const navigationGroups = resolveAdminNavigationGroups(user?.role);
    const activeItem = getAdminActiveNavItem(pathname, navigationGroups);
    const activeItemId = activeItem?.id ?? null;
    const { badges: queueBadges } = useAdminActionQueues(user?.role);
    const [expandedGroupIds, setExpandedGroupIds] = useState<
        AdminNavGroupId[]
    >(() => [...DEFAULT_EXPANDED_GROUP_IDS]);

    const toggleGroup = (groupId: AdminNavGroupId) => {
        setExpandedGroupIds((currentGroupIds) =>
            currentGroupIds.includes(groupId)
                ? currentGroupIds.filter((currentGroupId) => currentGroupId !== groupId)
                : [...currentGroupIds, groupId],
        );
    };

    const renderNavItem = (item: ResolvedAdminNavItem) => {
        const isActive = item.id === activeItemId;
        const isDisabled = item.accessState === 'disabled';
        const Icon = item.icon;
        const label = labelFor(item.labelKey);
        const hint = labelFor(item.hintKey);
        const unavailableLabel = labelFor('unavailableForRole');
        const badgeCount = queueBadges[item.id];
        const badgeLabel = badgeCount ? formatAdminQueueBadge(badgeCount) : null;
        const content = (
            <>
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

                <div
                    className={cn(
                        'relative flex items-start gap-3 px-3 py-2.5 text-sm font-mono transition-all duration-300',
                        isActive
                            ? 'translate-x-1 text-neon-cyan'
                            : 'text-muted-foreground group-hover:translate-x-1 group-hover:text-foreground',
                        isDisabled
                            ? 'cursor-not-allowed opacity-50 group-hover:translate-x-0 group-hover:text-muted-foreground'
                            : '',
                    )}
                >
                    <Icon
                        className={cn(
                            'mt-0.5 h-4 w-4 shrink-0 transition-transform duration-300',
                            isActive
                                ? 'drop-shadow-[0_0_8px_cyan]'
                                : 'group-hover:scale-110 group-hover:drop-shadow-[0_0_5px_white]',
                            isDisabled ? 'group-hover:scale-100 group-hover:drop-shadow-none' : '',
                        )}
                    />

                    <span className="relative min-w-0 flex-1">
                        <span className="relative block tracking-wide">
                            <CypherText
                                text={label}
                                className="transition-colors duration-300 group-hover:text-neon-cyan"
                                speed={30}
                            />
                            {!isDisabled ? (
                                <>
                                    <span
                                        aria-hidden="true"
                                        className="absolute left-0 top-0 -translate-x-[2px] text-neon-pink opacity-0 mix-blend-screen group-hover:animate-pulse group-hover:opacity-100"
                                    >
                                        {label}
                                    </span>
                                    <span
                                        aria-hidden="true"
                                        className="animation-delay-75 absolute left-0 top-0 translate-x-[2px] text-neon-cyan opacity-0 mix-blend-screen group-hover:animate-pulse group-hover:opacity-100"
                                    >
                                        {label}
                                    </span>
                                </>
                            ) : null}
                        </span>
                        <span
                            className={cn(
                                'mt-1 block text-[10px] uppercase tracking-[0.18em]',
                                isActive
                                    ? 'text-neon-cyan/70'
                                    : 'text-muted-foreground/70 group-hover:text-foreground/70',
                                isDisabled ? 'group-hover:text-muted-foreground/70' : '',
                            )}
                        >
                            {hint}
                        </span>
                    </span>

                    {badgeLabel ? (
                        <span
                            aria-label={`${label}: ${badgeLabel}`}
                            className={cn(
                                'mt-0.5 inline-flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full border px-1.5 text-[10px] font-mono font-semibold leading-none',
                                isActive
                                    ? 'border-neon-cyan/50 bg-neon-cyan/20 text-neon-cyan'
                                    : 'border-amber-300/40 bg-amber-300/15 text-amber-200',
                            )}
                        >
                            {badgeLabel}
                        </span>
                    ) : null}

                    {isActive && (
                        <motion.span
                            aria-hidden="true"
                            layoutId="active-dot"
                            className="absolute right-3 h-1.5 w-1.5 rounded-full bg-neon-cyan shadow-[0_0_8px_#00ffff]"
                        />
                    )}
                </div>
            </>
        );

        if (isDisabled) {
            return (
                <span
                    key={item.id}
                    role="link"
                    aria-label={label}
                    aria-current={isActive ? 'page' : undefined}
                    aria-disabled="true"
                    title={unavailableLabel}
                    className="group relative block overflow-hidden rounded-sm"
                >
                    {content}
                </span>
            );
        }

        return (
            <Link
                key={item.id}
                href={item.href}
                aria-label={label}
                aria-current={isActive ? 'page' : undefined}
                className="group relative block overflow-hidden rounded-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-surface focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
            >
                {content}
            </Link>
        );
    };

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
                <nav aria-label={labelFor('mainNavigation')} className="grid gap-3">
                    {navigationGroups.map((group) => {
                        const isActiveGroup = isAdminNavGroupActive(pathname, group);
                        const isExpanded =
                            isActiveGroup || expandedGroupIds.includes(group.id);
                        const groupLabel = labelFor(group.labelKey);
                        const groupHint = labelFor(group.hintKey);
                        const contentId = `desktop-nav-group-${group.id}`;
                        const groupBadgeCount = group.items.reduce(
                            (sum, item) => sum + (queueBadges[item.id] ?? 0),
                            0,
                        );
                        const groupBadgeLabel = groupBadgeCount
                            ? formatAdminQueueBadge(groupBadgeCount)
                            : null;

                        return (
                            <section key={group.id} className="grid gap-1">
                                <button
                                    type="button"
                                    aria-expanded={isExpanded}
                                    aria-controls={contentId}
                                    onClick={() => toggleGroup(group.id)}
                                    className={cn(
                                        'flex w-full items-center justify-between rounded-sm border border-transparent px-3 py-2 text-left font-mono text-[10px] uppercase tracking-[0.18em] transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan',
                                        isActiveGroup
                                            ? 'border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan'
                                            : 'text-muted-foreground hover:border-grid-line/30 hover:bg-sidebar-accent/40 hover:text-foreground',
                                    )}
                                >
                                    <span className="min-w-0">
                                        <span className="block truncate">{groupLabel}</span>
                                        <span className="mt-0.5 block truncate text-[9px] normal-case tracking-[0.08em] opacity-70">
                                            {groupHint}
                                        </span>
                                    </span>
                                    <span className="ml-2 flex shrink-0 items-center gap-2">
                                        {groupBadgeLabel ? (
                                            <span
                                                aria-label={`${groupLabel}: ${groupBadgeLabel}`}
                                                className="inline-flex h-5 min-w-5 items-center justify-center rounded-full border border-amber-300/40 bg-amber-300/15 px-1.5 text-[10px] font-semibold leading-none text-amber-200"
                                            >
                                                {groupBadgeLabel}
                                            </span>
                                        ) : null}
                                        <ChevronDown
                                            aria-hidden="true"
                                            className={cn(
                                                'h-3.5 w-3.5 transition-transform duration-200',
                                                isExpanded ? 'rotate-180' : '',
                                            )}
                                        />
                                    </span>
                                </button>

                                {isExpanded ? (
                                    <div id={contentId} className="grid gap-1 pl-2">
                                        {group.items.map((item) => renderNavItem(item))}
                                    </div>
                                ) : null}
                            </section>
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

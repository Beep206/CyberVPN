'use client';

import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronDown, Menu, Shield, X } from 'lucide-react';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { Link, usePathname } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { lockDocumentScroll } from '@/shared/lib/scroll-lock';
import { useAuthStore } from '@/stores/auth-store';
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

const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';
const DEFAULT_EXPANDED_GROUP_IDS: readonly AdminNavGroupId[] = ['operations'];

export function MobileSidebar() {
    const [isOpen, setIsOpen] = useState(false);
    const pathname = usePathname();
    const t = useTranslations('Navigation');
    const user = useAuthStore((state) => state.user);
    const sidebarRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);
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
    const portalContainer =
        typeof document === 'undefined' ? null : document.body;

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
            <div
                className={cn(
                    'relative flex min-h-12 items-start gap-3 px-3 py-2.5 text-sm font-mono transition-all duration-300',
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
                    <CypherText
                        text={label}
                        className="block transition-colors duration-300 group-hover:text-neon-cyan"
                        speed={30}
                    />
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
            </div>
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
                    className="group relative block overflow-hidden rounded-md"
                >
                    {isActive ? (
                        <div className="absolute inset-0 border-l-2 border-neon-cyan bg-neon-cyan/10" />
                    ) : null}
                    {content}
                </span>
            );
        }

        return (
            <Link
                key={item.id}
                href={item.href}
                onClick={() => setIsOpen(false)}
                aria-label={label}
                aria-current={isActive ? 'page' : undefined}
                className="group relative block overflow-hidden rounded-md focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-surface focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
            >
                {isActive ? (
                    <div className="absolute inset-0 border-l-2 border-neon-cyan bg-neon-cyan/10" />
                ) : null}
                {content}
            </Link>
        );
    };

    // Focus trap and keyboard handling for mobile sidebar
    useEffect(() => {
        if (!isOpen) return;

        // Focus the close button when sidebar opens
        const panel = sidebarRef.current;
        if (panel) {
            const closeBtn = panel.querySelector<HTMLElement>('[data-close-btn]');
            closeBtn?.focus();
        }

        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                setIsOpen(false);
                return;
            }

            if (e.key === 'Tab' && panel) {
                const focusable = panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
                if (focusable.length === 0) return;

                const first = focusable[0];
                const last = focusable[focusable.length - 1];

                if (e.shiftKey && document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                } else if (!e.shiftKey && document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [isOpen]);

    // Return focus to trigger button when sidebar closes
    useEffect(() => {
        if (!isOpen) {
            triggerRef.current?.focus();
        }
    }, [isOpen]);

    useEffect(() => {
        if (!isOpen) {
            return;
        }

        return lockDocumentScroll();
    }, [isOpen]);

    return (
        <div className="md:hidden">
            <Button
                ref={triggerRef}
                variant="ghost"
                size="icon"
                magnetic={false}
                onClick={() => setIsOpen(true)}
                aria-label={labelFor('openMenu')}
                aria-expanded={isOpen}
                aria-haspopup="dialog"
                aria-controls="mobile-sidebar-panel"
                className="h-10 w-10 rounded-xl border border-grid-line/30 bg-terminal-surface/60 text-neon-cyan hover:bg-neon-cyan/10 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
            >
                <Menu className="h-5 w-5" />
            </Button>

            {portalContainer
                ? createPortal(
                      <AnimatePresence>
                          {isOpen && (
                              <>
                                  <motion.div
                                      initial={{ opacity: 0 }}
                                      animate={{ opacity: 1 }}
                                      exit={{ opacity: 0 }}
                                      onClick={() => setIsOpen(false)}
                                      className="fixed inset-0 z-[70] bg-black/60 backdrop-blur-sm"
                                      aria-hidden="true"
                                  />
                                  <motion.aside
                                      ref={sidebarRef}
                                      id="mobile-sidebar-panel"
                                      role="dialog"
                                      aria-modal="true"
                                      aria-label={labelFor('sidebar')}
                                      initial={{ x: '-100%' }}
                                      animate={{ x: 0 }}
                                      exit={{ x: '-100%' }}
                                      transition={{ type: 'spring', damping: 20, stiffness: 300 }}
                                      className="fixed inset-y-0 left-0 z-[80] flex h-dvh w-[min(20rem,calc(100vw-var(--mobile-page-gutter)*2))] max-w-full flex-col border-r border-grid-line/30 bg-terminal-surface/95 backdrop-blur-xl"
                                  >
                            <div className="flex h-16 items-center justify-between border-b border-grid-line/30 px-6">
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
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    magnetic={false}
                                    data-close-btn
                                    onClick={() => setIsOpen(false)}
                                    aria-label={labelFor('closeMenu')}
                                    className="text-muted-foreground hover:text-neon-pink focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-pink focus-visible:shadow-[0_0_12px_var(--color-neon-pink)]"
                                >
                                    <X className="h-5 w-5" />
                                </Button>
                            </div>

                            <div className="flex-1 overflow-y-auto py-6 px-4">
                                <nav aria-label={labelFor('mainNavigation')} className="grid gap-3">
                                    {navigationGroups.map((group) => {
                                        const isActiveGroup = isAdminNavGroupActive(pathname, group);
                                        const isExpanded =
                                            isActiveGroup || expandedGroupIds.includes(group.id);
                                        const groupLabel = labelFor(group.labelKey);
                                        const groupHint = labelFor(group.hintKey);
                                        const contentId = `mobile-nav-group-${group.id}`;
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
                                                        'flex min-h-12 w-full items-center justify-between rounded-md border border-transparent px-3 py-2 text-left font-mono text-[10px] uppercase tracking-[0.18em] transition-colors focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan',
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
                                </motion.aside>
                            </>
                        )}
                    </AnimatePresence>,
                    portalContainer,
                )
                : null}
        </div>
    );
}

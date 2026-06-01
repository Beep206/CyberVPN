'use client';

import { useEffect, useRef, useState } from 'react';
import { ChevronDown, Menu, Shield, X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Link, usePathname } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/auth-store';
import { PartnerWorkspaceSwitcher } from '@/features/partner-portal-state/components/partner-workspace-switcher';
import { usePartnerPortalBootstrapState } from '@/features/partner-portal-state/lib/use-partner-portal-bootstrap-state';
import {
    doesPartnerNavGroupNeedAttention,
    getPartnerNavGroups,
    type PartnerNavPresentationState,
} from '@/features/partner-shell/lib/partner-nav-presentation';
import type { PartnerNavGroupId } from '@/features/partner-shell/config/nav-groups';
import { lockDocumentScroll } from '@/shared/lib/scroll-lock';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { DASHBOARD_NAV_LABEL_FALLBACKS } from '@/widgets/dashboard-navigation';

const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function badgeClassName(state: PartnerNavPresentationState) {
    if (state === 'task') {
        return 'border-neon-pink/35 bg-neon-pink/10 text-neon-pink';
    }

    if (state === 'limited') {
        return 'border-neon-purple/45 bg-neon-purple/10 text-neon-purple';
    }

    return 'border-grid-line/25 bg-terminal-bg/70 text-muted-foreground';
}

export function MobileSidebar() {
    const [isOpen, setIsOpen] = useState(false);
    const [openGroupIds, setOpenGroupIds] = useState<PartnerNavGroupId[]>([]);
    const pathname = usePathname();
    const t = useTranslations('Navigation');
    const user = useAuthStore((state) => state.user);
    const { state: portalState } = usePartnerPortalBootstrapState();
    const sidebarRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);
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
    const isActiveHref = (href: string) => pathname === href || pathname?.startsWith(`${href}/`);
    const getDefaultOpenGroupIds = () => {
        const preferredGroupIds = navGroups
            .filter((group) => (
                group.items.some(({ item }) => isActiveHref(item.href))
                || doesPartnerNavGroupNeedAttention(group)
            ))
            .map((group) => group.id);

        return preferredGroupIds.length > 0
            ? preferredGroupIds
            : navGroups.slice(0, 1).map((group) => group.id);
    };
    const openMenu = () => {
        setOpenGroupIds(getDefaultOpenGroupIds());
        setIsOpen(true);
    };
    const closeMenu = () => setIsOpen(false);
    const toggleGroup = (groupId: PartnerNavGroupId) => {
        setOpenGroupIds((current) => (
            current.includes(groupId)
                ? current.filter((id) => id !== groupId)
                : [...current, groupId]
        ));
    };

    // Focus trap and keyboard handling for mobile sidebar
    useEffect(() => {
        if (!isOpen) return;

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
                onClick={openMenu}
                aria-label={labelFor('openMenu')}
                aria-expanded={isOpen}
                aria-haspopup="dialog"
                aria-controls="mobile-sidebar-panel"
                className="h-10 w-10 rounded-xl border border-grid-line/30 bg-terminal-surface/60 text-neon-cyan hover:bg-neon-cyan/10 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
            >
                <Menu className="h-5 w-5" />
            </Button>

            <AnimatePresence>
                {isOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={closeMenu}
                            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
                            aria-hidden="true"
                        />
                        <motion.div
                            ref={sidebarRef}
                            id="mobile-sidebar-panel"
                            role="dialog"
                            aria-modal="true"
                            aria-label={labelFor('sidebar')}
                            initial={{ x: '-100%' }}
                            animate={{ x: 0 }}
                            exit={{ x: '-100%' }}
                            transition={{ type: 'spring', damping: 20, stiffness: 300 }}
                            className="fixed inset-y-0 left-0 z-50 flex w-[min(20rem,calc(100vw-var(--mobile-page-gutter)*2))] max-w-full flex-col border-r border-grid-line/30 bg-terminal-surface/95 backdrop-blur-xl"
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
                                            PARTNER
                                        </div>
                                    </div>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    magnetic={false}
                                    data-close-btn
                                    onClick={closeMenu}
                                    aria-label={labelFor('closeMenu')}
                                    className="text-muted-foreground hover:text-neon-pink focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-pink focus-visible:shadow-[0_0_12px_var(--color-neon-pink)]"
                                >
                                    <X className="h-5 w-5" />
                                </Button>
                            </div>

                            <div className="flex-1 overflow-y-auto px-4 py-6">
                                <nav aria-label={labelFor('mainNavigation')} className="space-y-3">
                                    {navGroups.map((group) => {
                                        const isExpanded = openGroupIds.includes(group.id);
                                        const groupLabel = labelFor(group.labelKey);
                                        const groupHint = labelFor(group.hintKey);
                                        const groupPanelId = `mobile-sidebar-group-${group.id}`;

                                        return (
                                            <section key={group.id}>
                                                <button
                                                    type="button"
                                                    aria-expanded={isExpanded}
                                                    aria-controls={groupPanelId}
                                                    onClick={() => toggleGroup(group.id)}
                                                    className="flex w-full items-start justify-between gap-3 rounded-xl border border-grid-line/20 bg-terminal-bg/45 px-3 py-3 text-left focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
                                                >
                                                    <span className="min-w-0">
                                                        <span className="block font-mono text-[11px] uppercase tracking-[0.2em] text-neon-cyan/80">
                                                            {groupLabel}
                                                        </span>
                                                        <span className="mt-1 block text-[10px] font-mono uppercase tracking-[0.13em] text-muted-foreground-low">
                                                            {groupHint}
                                                        </span>
                                                    </span>
                                                    <span className="flex shrink-0 items-center gap-2">
                                                        {doesPartnerNavGroupNeedAttention(group) ? (
                                                            <span className="rounded-full border border-neon-pink/35 bg-neon-pink/10 px-2 py-0.5 text-[9px] font-mono uppercase tracking-[0.16em] text-neon-pink">
                                                                {labelFor('badgeTask')}
                                                            </span>
                                                        ) : null}
                                                        <ChevronDown
                                                            className={cn(
                                                                'mt-0.5 h-4 w-4 text-muted-foreground transition-transform',
                                                                isExpanded ? 'rotate-180' : '',
                                                            )}
                                                        />
                                                    </span>
                                                </button>

                                                <AnimatePresence initial={false}>
                                                    {isExpanded && (
                                                        <motion.div
                                                            id={groupPanelId}
                                                            initial={{ height: 0, opacity: 0 }}
                                                            animate={{ height: 'auto', opacity: 1 }}
                                                            exit={{ height: 0, opacity: 0 }}
                                                            className="overflow-hidden"
                                                        >
                                                            <div className="grid gap-1.5 pt-2">
                                                                {group.items.map(({ item, presentation }) => {
                                                                    const isActive = isActiveHref(item.href);
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
                                                                            onClick={closeMenu}
                                                                            aria-label={label}
                                                                            aria-current={isActive ? 'page' : undefined}
                                                                            className="group relative block overflow-hidden rounded-md focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-surface focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
                                                                        >
                                                                            {isActive && (
                                                                                <div className="absolute inset-0 border-l-2 border-neon-cyan bg-neon-cyan/10" />
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
                                                                                    <CypherText
                                                                                        text={label}
                                                                                        className="block transition-colors duration-300 group-hover:text-neon-cyan"
                                                                                        speed={30}
                                                                                    />
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
                                                                            </div>
                                                                        </Link>
                                                                    );
                                                                })}
                                                            </div>
                                                        </motion.div>
                                                    )}
                                                </AnimatePresence>
                                            </section>
                                        );
                                    })}
                                </nav>
                            </div>

                            <div className="border-t border-grid-line/30 p-4">
                                <div className="space-y-4">
                                    <PartnerWorkspaceSwitcher compact />

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
                        </motion.div>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}

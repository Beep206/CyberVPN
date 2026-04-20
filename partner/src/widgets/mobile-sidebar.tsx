'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Menu, Shield, X } from 'lucide-react';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { Link, usePathname } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { lockDocumentScroll } from '@/shared/lib/scroll-lock';
import { useAuthStore } from '@/stores/auth-store';
import {
    DASHBOARD_NAV_ITEMS,
    DASHBOARD_NAV_LABEL_FALLBACKS,
} from '@/widgets/dashboard-navigation';
import type { PartnerSectionSlug } from '@/features/partner-shell/config/section-registry';
import { usePartnerPortalBootstrapState } from '@/features/partner-portal-state/lib/use-partner-portal-bootstrap-state';
import { PartnerWorkspaceSwitcher } from '@/features/partner-portal-state/components/partner-workspace-switcher';
import { canPartnerRouteAccess } from '@/features/partner-portal-state/lib/portal-access';

const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function MobileSidebar() {
    const [isOpen, setIsOpen] = useState(false);
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
    const visibleItems = DASHBOARD_NAV_ITEMS.filter((item) => (
        item.href === '/dashboard'
            ? true
            : canPartnerRouteAccess(
                item.href.slice(1) as PartnerSectionSlug,
                portalState,
            )
    ));

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

            <AnimatePresence>
                {isOpen && (
                    <>
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setIsOpen(false)}
                            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
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
                                    onClick={() => setIsOpen(false)}
                                    aria-label={labelFor('closeMenu')}
                                    className="text-muted-foreground hover:text-neon-pink focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-pink focus-visible:shadow-[0_0_12px_var(--color-neon-pink)]"
                                >
                                    <X className="h-5 w-5" />
                                </Button>
                            </div>

                            <div className="flex-1 overflow-y-auto py-6 px-4">
                                <nav aria-label={labelFor('mainNavigation')} className="grid gap-2">
                                    {visibleItems.map((item) => {
                                        const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
                                        const Icon = item.icon;
                                        const label = labelFor(item.labelKey);
                                        const hint = labelFor(item.hintKey);

                                        return (
                                            <Link
                                                key={item.href}
                                                href={item.href}
                                                onClick={() => setIsOpen(false)}
                                                aria-label={label}
                                                aria-current={isActive ? 'page' : undefined}
                                                className="group relative block overflow-hidden rounded-md focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-surface focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
                                            >
                                                {isActive && (
                                                    <div className="absolute inset-0 bg-neon-cyan/10 border-l-2 border-neon-cyan" />
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
                                                        <CypherText
                                                            text={label}
                                                            className="block group-hover:text-neon-cyan transition-colors duration-300"
                                                            speed={30}
                                                        />
                                                        <span className={cn(
                                                            'mt-1 block text-[10px] uppercase tracking-[0.18em]',
                                                            isActive ? 'text-neon-cyan/70' : 'text-muted-foreground/70 group-hover:text-foreground/70',
                                                        )}>
                                                            {hint}
                                                        </span>
                                                    </span>
                                                </div>
                                            </Link>
                                        );
                                    })}
                                </nav>
                            </div>

                            <div className="border-t border-grid-line/30 p-4">
                                <div className="space-y-4">
                                    <PartnerWorkspaceSwitcher compact />

                                    <div className="rounded-2xl border border-grid-line/20 bg-sidebar-accent/50 p-4">
                                    <div className="mb-3 flex items-center gap-3">
                                        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-neon-purple/40 bg-neon-purple/15 text-neon-purple">
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
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}

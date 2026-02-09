'use client';

import { useState, useEffect, useRef } from 'react';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { Link, usePathname } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'motion/react';
import { Server, Users, Activity, CreditCard, Settings, Shield, BarChart3, Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';

const FOCUSABLE_SELECTOR = 'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

const menuItems = [
    { icon: Activity, labelKey: 'dashboard', href: '/dashboard' },
    { icon: Server, labelKey: 'servers', href: '/servers' },
    { icon: Users, labelKey: 'users', href: '/users' },
    { icon: CreditCard, labelKey: 'billing', href: '/subscriptions' },
    { icon: BarChart3, labelKey: 'analytics', href: '/analytics' },
    { icon: Shield, labelKey: 'security', href: '/monitoring' },
    { icon: Settings, labelKey: 'settings', href: '/settings' },
];

export function MobileSidebar() {
    const [isOpen, setIsOpen] = useState(false);
    const pathname = usePathname();
    const t = useTranslations('Navigation');
    const sidebarRef = useRef<HTMLDivElement>(null);
    const triggerRef = useRef<HTMLButtonElement>(null);

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

    return (
        <div className="md:hidden">
            <Button
                ref={triggerRef}
                variant="ghost"
                size="icon"
                magnetic={false}
                onClick={() => setIsOpen(true)}
                aria-label={t('openMenu')}
                aria-expanded={isOpen}
                aria-haspopup="dialog"
                aria-controls="mobile-sidebar-panel"
                className="fixed top-3.5 left-4 z-50 h-9 w-9 rounded-lg text-neon-cyan hover:bg-neon-cyan/10 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
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
                            aria-label={t('sidebar')}
                            initial={{ x: '-100%' }}
                            animate={{ x: 0 }}
                            exit={{ x: '-100%' }}
                            transition={{ type: 'spring', damping: 20, stiffness: 300 }}
                            className="fixed left-0 top-0 bottom-0 z-50 w-64 flex-col border-r border-grid-line/30 bg-terminal-surface/95 backdrop-blur-xl"
                        >
                            <div className="flex h-16 items-center justify-between border-b border-grid-line/30 px-6">
                                <div className="flex items-center gap-2 font-display text-xl tracking-wider text-neon-cyan drop-shadow-glow">
                                    <Shield className="h-6 w-6" />
                                    <span>NEXUS</span>
                                </div>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    magnetic={false}
                                    data-close-btn
                                    onClick={() => setIsOpen(false)}
                                    aria-label={t('closeMenu')}
                                    className="text-muted-foreground hover:text-neon-pink focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-pink focus-visible:shadow-[0_0_12px_var(--color-neon-pink)]"
                                >
                                    <X className="h-5 w-5" />
                                </Button>
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
                                                onClick={() => setIsOpen(false)}
                                                aria-label={label}
                                                aria-current={isActive ? 'page' : undefined}
                                                className="group relative block overflow-hidden rounded-md focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-terminal-surface focus-visible:shadow-[0_0_12px_var(--color-neon-cyan)]"
                                            >
                                                {isActive && (
                                                    <div className="absolute inset-0 bg-neon-cyan/10 border-l-2 border-neon-cyan" />
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
                                                    </span>
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
                        </motion.aside>
                    </>
                )}
            </AnimatePresence>
        </div>
    );
}

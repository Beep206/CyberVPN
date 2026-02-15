'use client';

import { useState, useRef, useEffect } from 'react';
import { QrCode, Smartphone, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslations } from 'next-intl';
import { MagneticButton } from '@/shared/ui/magnetic-button';
import { cn } from '@/lib/utils';
import QRCode from 'react-qr-code';
import { CypherText } from '@/shared/ui/atoms/cypher-text';

type Tab = 'ios' | 'android';

export function QRCodeDropdown() {
    const [isOpen, setIsOpen] = useState(false);
    const [activeTab, setActiveTab] = useState<Tab>('ios');
    const [isHovered, setIsHovered] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const t = useTranslations('Header.QRCode');

    // Close on click outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // TODO: Replace with actual app store links
    const appLinks = {
        ios: 'https://apps.apple.com/app/cybervpn',
        android: 'https://play.google.com/store/apps/details?id=com.cybervpn'
    };

    return (
        <div className="relative z-50" ref={dropdownRef}>
            <MagneticButton strength={10}>
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    onMouseEnter={() => setIsHovered(true)}
                    onMouseLeave={() => setIsHovered(false)}
                    className={cn(
                        "flex items-center gap-2 px-3 py-1.5 rounded-lg border transition-all duration-300",
                        isOpen
                            ? "bg-neon-cyan/10 border-neon-cyan text-neon-cyan"
                            : "bg-muted/30 border-border/50 dark:border-white/10 text-muted-foreground hover:text-foreground hover:border-foreground/20"
                    )}
                >
                    <QrCode className="w-4 h-4" />
                    <span className="text-sm font-medium hidden sm:inline">
                        <CypherText text="Get App" trigger={isHovered} />
                    </span>
                </button>
            </MagneticButton>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95, filter: 'blur(10px)' }}
                        animate={{ opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
                        exit={{ opacity: 0, y: 10, scale: 0.95, filter: 'blur(10px)' }}
                        transition={{ duration: 0.2, ease: "circOut" }}
                        className="absolute right-0 top-full mt-3 z-50 w-72 bg-background/95 dark:bg-terminal-surface/80 border border-border/50 dark:border-white/10 rounded-2xl shadow-xl dark:shadow-[0_20px_50px_-12px_rgba(0,0,0,0.7)] backdrop-blur-3xl overflow-hidden ring-1 ring-black/5 dark:ring-white/5"
                    >
                        {/* Background Effects */}
                        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-5 dark:opacity-20 pointer-events-none" />
                        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-primary/5 pointer-events-none" />

                        {/* Tabs */}
                        <div className="flex border-b border-border/50 dark:border-white/10">
                            <button
                                onClick={() => setActiveTab('ios')}
                                className={cn(
                                    "flex-1 py-3 text-sm font-medium transition-colors relative group",
                                    activeTab === 'ios' ? "text-foreground font-semibold bg-foreground/10 dark:text-neon-cyan dark:bg-neon-cyan/5" : "text-muted-foreground hover:text-foreground hover:bg-foreground/5 dark:hover:bg-white/5"
                                )}
                            >
                                <CypherText text="iOS" trigger={activeTab === 'ios'} />
                                {activeTab === 'ios' && (
                                    <motion.div
                                        layoutId="activeTab"
                                        className="absolute bottom-0 left-0 right-0 h-0.5 bg-foreground dark:bg-neon-cyan shadow-[0_0_10px_theme(colors.gray.500)] dark:shadow-[0_0_10px_rgba(0,255,255,0.5)]"
                                    />
                                )}
                            </button>
                            <button
                                onClick={() => setActiveTab('android')}
                                className={cn(
                                    "flex-1 py-3 text-sm font-medium transition-colors relative group",
                                    activeTab === 'android' ? "text-emerald-600 font-semibold bg-emerald-600/10 dark:text-matrix-green dark:bg-matrix-green/5" : "text-muted-foreground hover:text-foreground hover:bg-foreground/5 dark:hover:bg-white/5"
                                )}
                            >
                                <CypherText text="Android" trigger={activeTab === 'android'} />
                                {activeTab === 'android' && (
                                    <motion.div
                                        layoutId="activeTab"
                                        className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600 dark:bg-matrix-green shadow-[0_0_10px_theme(colors.emerald.500)] dark:shadow-[0_0_10px_rgba(0,255,0,0.5)]"
                                    />
                                )}
                            </button>
                        </div>

                        {/* Content */}
                        <div className="p-6 flex flex-col items-center gap-4">
                            <motion.div
                                initial={{ scale: 0.9, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ type: "spring", stiffness: 200, damping: 20 }}
                                className={cn(
                                    "p-3 rounded-xl bg-white relative group active:scale-95 transition-transform duration-200",
                                    activeTab === 'ios'
                                        ? "shadow-lg shadow-primary/20 dark:shadow-[0_0_30px_rgba(0,255,255,0.15)] ring-1 ring-black/5"
                                        : "shadow-lg shadow-green-500/20 dark:shadow-[0_0_30px_rgba(0,255,0,0.15)] ring-1 ring-black/5"
                                )}>
                                <QRCode
                                    value={appLinks[activeTab]}
                                    size={160}
                                    level="M"
                                />
                                {/* Scan Line Animation */}
                                <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-xl">
                                    <div className={cn(
                                        "absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-black/20 to-transparent dark:via-white/50 animate-[scan_2s_ease-in-out_infinite]",
                                        activeTab === 'ios' ? "shadow-[0_0_10px_rgba(0,255,255,0.5)]" : "shadow-[0_0_10px_rgba(0,255,0,0.5)]"
                                    )} />
                                </div>
                            </motion.div>

                            <div className="text-center space-y-1">
                                <h4 className="text-sm font-medium text-foreground">
                                    <CypherText text="Scan to Download" delay={200} trigger={true} />
                                </h4>
                                <p className="text-xs text-muted-foreground text-center max-w-[200px] mx-auto">
                                    Open your camera to install on <span className={activeTab === 'ios' ? "text-primary dark:text-neon-cyan" : "text-green-600 dark:text-matrix-green"}>{activeTab === 'ios' ? 'iOS' : 'Android'}</span>
                                </p>
                            </div>

                            <a
                                href={appLinks[activeTab]}
                                target="_blank"
                                rel="noreferrer"
                                className={cn(
                                    "w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all group/btn relative overflow-hidden",
                                    activeTab === 'ios'
                                        ? "bg-gradient-to-br from-gray-900 to-black text-white hover:from-black hover:to-gray-800 shadow-lg shadow-black/25 dark:bg-neon-cyan/10 dark:text-neon-cyan dark:hover:bg-neon-cyan/20 dark:border dark:border-neon-cyan/50 dark:shadow-[0_0_20px_rgba(0,255,255,0.2)]"
                                        : "bg-emerald-600 text-white hover:bg-emerald-700 shadow-lg shadow-emerald-600/20 dark:bg-matrix-green/10 dark:text-matrix-green dark:hover:bg-matrix-green/20 dark:border dark:border-matrix-green/50 dark:shadow-[0_0_20px_rgba(0,255,0,0.2)]"
                                )}
                            >
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover/btn:translate-x-full transition-transform duration-1000 ease-in-out" />
                                <Smartphone className="w-4 h-4" />
                                <span>Download for {activeTab === 'ios' ? 'iPhone' : 'Android'}</span>
                                <ExternalLink className="w-3 h-3 ml-1 opacity-50 group-hover/btn:translate-x-0.5 group-hover/btn:-translate-y-0.5 transition-transform" />
                            </a>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

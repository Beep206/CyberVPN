'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'framer-motion';
import { Hexagon, Lock, Unlock, ServerCrash, Skull, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { type TermsSectionId } from './terms-dashboard';

interface Props {
    activeSection: TermsSectionId;
    setActiveSection: (id: TermsSectionId) => void;
    isAccepted: boolean;
}

const SECTION_KEYS: TermsSectionId[] = ['acceptance', 'prohibited', 'service', 'liability', 'termination'];

export function ComplianceScanner({ activeSection, setActiveSection, isAccepted }: Props) {
    const t = useTranslations('Terms');

    // Helper to determine if a section has been passed (scrolled past = scanned)
    const getSectionStatus = (section: TermsSectionId) => {
        if (isAccepted) return 'verified';
        const currentIndex = SECTION_KEYS.indexOf(activeSection);
        const sectionIndex = SECTION_KEYS.indexOf(section);
        if (sectionIndex < currentIndex) return 'scanned';
        if (sectionIndex === currentIndex) return 'scanning';
        return 'pending';
    };

    const getIcon = (section: TermsSectionId, status: string) => {
        if (status === 'verified') return <CheckCircle2 className="w-5 h-5 text-matrix-green" />;
        
        switch (section) {
            case 'acceptance': return status === 'pending' ? <Lock className="w-5 h-5" /> : <Unlock className="w-5 h-5" />;
            case 'prohibited': return <ServerCrash className="w-5 h-5" />;
            case 'termination': return <Skull className="w-5 h-5" />;
            default: return <Hexagon className="w-5 h-5" />;
        }
    };

    return (
        <div className="w-full h-full p-6 flex flex-col pt-12">
            <div className="mb-8">
                <h2 className="text-sm font-cyber text-muted-foreground-low tracking-widest mb-2 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-warning animate-pulse" />
                    SYSTEM COMPLIANCE
                </h2>
                <div className="h-px w-full bg-gradient-to-r from-warning/50 to-transparent" />
            </div>

            <div className="flex-1 flex flex-col gap-6">
                {SECTION_KEYS.map((section, index) => {
                    const status = getSectionStatus(section);
                    const isActive = section === activeSection;

                    return (
                        <button
                            key={section}
                            onClick={() => {
                                const el = document.getElementById(section);
                                if (el) el.scrollIntoView({ behavior: 'smooth' });
                            }}
                            className={cn(
                                "group flex flex-col text-left transition-all duration-300 relative pl-6",
                                status === 'verified' ? "opacity-100" :
                                isActive ? "opacity-100 scale-105" : "opacity-40 hover:opacity-100"
                            )}
                        >
                            {/* Animated line behind the nodes */}
                            {index !== SECTION_KEYS.length - 1 && (
                                <div className="absolute left-[9px] top-6 bottom-[-24px] w-px bg-grid-line/30">
                                    {status === 'scanned' || status === 'verified' ? (
                                        <motion.div 
                                            className="w-full bg-warning h-full origin-top"
                                            initial={{ scaleY: 0 }}
                                            animate={{ scaleY: 1 }}
                                            transition={{ duration: 0.5 }}
                                        />
                                    ) : null}
                                </div>
                            )}

                            <div className="flex items-center gap-4">
                                <div className={cn(
                                    "relative z-10 flex items-center justify-center w-6 h-6 rounded-full border bg-black transition-colors duration-500",
                                    status === 'verified' ? "text-matrix-green border-matrix-green shadow-[0_0_10px_rgba(0,255,136,0.3)]" :
                                    status === 'scanned' ? "text-warning border-warning" :
                                    isActive ? "text-neon-cyan border-neon-cyan animate-pulse" :
                                    "text-muted-foreground border-muted-foreground"
                                )}>
                                    {getIcon(section, status)}
                                </div>

                                <div className="flex flex-col">
                                    <span className={cn(
                                        "font-mono text-xs mb-1 transition-colors",
                                        status === 'verified' ? "text-matrix-green" :
                                        isActive ? "text-neon-cyan" : "text-muted-foreground"
                                    )}>
                                        {status === 'verified' ? t('status.acknowledged') : isActive ? 'SCANNING...' : t('status.unverified')}
                                    </span>
                                    <span className={cn(
                                        "font-display font-medium tracking-wide transition-colors",
                                        status === 'verified' ? "text-white" :
                                        isActive ? "text-white" : "text-white/50"
                                    )}>
                                        {t(`sections.${section}.title`)}
                                    </span>
                                </div>
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Global Status Indicator */}
            <div className="mt-8 pt-6 border-t border-grid-line/30 flex items-center justify-between">
                <span className="font-mono text-xs text-muted-foreground">SCAN PROGRESS</span>
                <span className={cn(
                    "font-display text-sm",
                    isAccepted ? "text-matrix-green" : "text-warning"
                )}>
                    {isAccepted ? "100% COMPLETE" : "ONGOING"}
                </span>
            </div>
        </div>
    );
}

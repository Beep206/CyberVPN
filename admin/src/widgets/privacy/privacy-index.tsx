'use client';

import { useTranslations } from 'next-intl';
import { PrivacySectionId } from './privacy-dashboard';
import { motion } from 'motion/react';
import { Lock, Unlock, ShieldAlert, FileKey } from 'lucide-react';

const SECTIONS: PrivacySectionId[] = [
    'introduction',
    'dataCollection',
    'noLogs',
    'encryption',
    'thirdParties'
];

export function PrivacyIndex({ 
    activeSection, 
    setActiveSection 
}: { 
    activeSection: PrivacySectionId;
    setActiveSection: (id: PrivacySectionId) => void;
}) {
    const t = useTranslations('Privacy');
    
    // Find index of active section to determine which are "decrypted" (above/at) vs "encrypted" (below)
    const activeIndex = SECTIONS.indexOf(activeSection);

    return (
        <div className="h-full w-full flex flex-col p-6 overflow-y-auto no-scrollbar font-mono">
            
            <div className="mb-8 flex flex-col gap-2">
                <div className="flex items-center gap-2 text-neon-cyan mb-1">
                    <ShieldAlert className="w-5 h-5" />
                    <span className="text-sm tracking-widest font-bold">CYBERVPN // ROOT</span>
                </div>
                <h1 className="text-2xl font-black text-white uppercase tracking-wider">
                    {t('title')}
                </h1>
                <p className="text-xs text-matrix-green/80 uppercase">
                    {t('description')}
                </p>
                
                <div className="w-full h-px bg-gradient-to-r from-neon-cyan/50 to-transparent mt-4" />
            </div>

            <nav className="flex flex-col gap-1 w-full relative">
                
                {/* Vertical Timeline Line */}
                <div className="absolute left-3.5 top-2 bottom-2 w-px bg-grid-line/50 z-0" />

                {SECTIONS.map((sectionId, index) => {
                    const isActive = sectionId === activeSection;
                    const isDecrypted = index <= activeIndex;
                    
                    return (
                        <button
                            key={sectionId}
                            onClick={() => {
                                setActiveSection(sectionId);
                                const el = document.getElementById(`section-${sectionId}`);
                                if (el) {
                                    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                }
                            }}
                            className={`relative z-10 w-full text-left py-4 px-2 group transition-all duration-300 flex items-start gap-4 ${
                                isActive 
                                    ? 'bg-neon-cyan/10 border-l-2 border-neon-cyan' 
                                    : 'hover:bg-grid-line/10 border-l-2 border-transparent'
                            }`}
                        >
                            {/* Icon Indicator */}
                            <div className={`mt-0.5 min-w-7 h-7 flex flex-col items-center justify-center rounded-sm border ${
                                isActive
                                    ? 'bg-neon-cyan/20 border-neon-cyan text-neon-cyan'
                                    : isDecrypted
                                        ? 'bg-matrix-green/10 border-matrix-green/50 text-matrix-green/80'
                                        : 'bg-black border-grid-line text-grid-line/50'
                            }`}>
                                {isActive ? (
                                    <FileKey className="w-3.5 h-3.5 animate-pulse" />
                                ) : isDecrypted ? (
                                    <Unlock className="w-3 h-3" />
                                ) : (
                                    <Lock className="w-3 h-3" />
                                )}
                            </div>

                            {/* Text Content */}
                            <div className="flex flex-col gap-1 w-full overflow-hidden">
                                <span className={`text-[10px] uppercase font-bold tracking-widest ${
                                    isActive ? 'text-neon-cyan' : isDecrypted ? 'text-matrix-green/70' : 'text-grid-line'
                                }`}>
                                    {isActive ? t('status.decrypting') : isDecrypted ? t('status.decrypted') : t('status.encrypted')}
                                </span>
                                
                                <span className={`text-sm md:text-xs truncate transition-colors ${
                                    isActive ? 'text-white' : isDecrypted ? 'text-terminal-text' : 'text-terminal-text/40'
                                }`}>
                                    {t(`sections.${sectionId}.title`)}
                                </span>
                            </div>

                            {/* Active Scanline Effect */}
                            {isActive && (
                                <motion.div 
                                    className="absolute inset-0 bg-gradient-to-r from-neon-cyan/0 via-neon-cyan/5 to-neon-cyan/0"
                                    animate={{ x: ['-100%', '100%'] }}
                                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                                />
                            )}
                        </button>
                    );
                })}
            </nav>

        </div>
    );
}

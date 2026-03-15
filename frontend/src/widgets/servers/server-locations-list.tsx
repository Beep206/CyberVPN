'use client';

import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from '@/lib/utils';
import { Server, Zap, Shield, Globe2, ChevronRight } from 'lucide-react';

interface ServerLocationsListProps {
    activeNodeId: string | null;
    setActiveNodeId: (id: string | null) => void;
}

const REGION_MAP: Record<string, string[]> = {
    namerica: ['1'], // NY
    europe: ['2', '5'], // LDN, DE
    asia: ['3', '4', '7'], // JP, SG, AU
    latam: ['6'] // BR
};

export function ServerLocationsList({ activeNodeId, setActiveNodeId }: ServerLocationsListProps) {
    const t = useTranslations('Network');

    return (
        <div className="w-full flex flex-col gap-6">
            {Object.entries(REGION_MAP).map(([regionKey, serverIds], rIdx) => (
                <div key={regionKey} className="flex flex-col gap-2">
                    <h3 className="font-display text-sm font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-2 mb-2">
                        <Globe2 className="w-4 h-4 text-neon-cyan/50" />
                        {t(`regions.${regionKey}`)}
                    </h3>
                    
                    <div className="flex flex-col gap-2">
                        {serverIds.map((id, sIdx) => {
                            const isActive = activeNodeId === id;
                            
                            return (
                                <motion.button
                                    key={id}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ duration: 0.4, delay: rIdx * 0.1 + sIdx * 0.05 }}
                                    onMouseEnter={() => setActiveNodeId(id)}
                                    className={cn(
                                        "relative w-full text-left p-4 rounded-lg border transition-all duration-300 group overflow-hidden flex items-center justify-between",
                                        isActive 
                                            ? "bg-neon-cyan/10 border-neon-cyan shadow-[0_0_20px_rgba(0,255,255,0.1)]" 
                                            : "bg-terminal-bg/80 backdrop-blur-md border-grid-line/30 hover:border-neon-cyan/50 hover:bg-terminal-bg"
                                    )}
                                >
                                    <div className={cn(
                                        "absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full transition-transform duration-700",
                                        isActive ? "animate-scan" : "group-hover:translate-x-[200%]"
                                    )} />

                                    <div className="relative z-10 flex items-center gap-3">
                                        <div className={cn(
                                            "w-2 h-2 rounded-full transition-all duration-300",
                                            isActive ? "bg-neon-cyan shadow-[0_0_8px_rgba(0,255,255,0.8)]" : "bg-matrix-green/50 group-hover:bg-matrix-green"
                                        )} />
                                        <span className={cn(
                                            "font-mono text-sm transition-colors duration-300",
                                            isActive ? "text-white font-bold" : "text-muted-foreground group-hover:text-white"
                                        )}>
                                            {t(`servers.${id}`)}
                                        </span>
                                    </div>
                                    
                                    <ChevronRight className={cn(
                                        "w-4 h-4 transition-all duration-300 relative z-10",
                                        isActive ? "text-neon-cyan translate-x-1 opacity-100" : "text-muted-foreground opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 group-hover:text-neon-cyan/50"
                                    )} />
                                    
                                    {isActive && (
                                        <motion.div 
                                            layoutId="activeServerGlow"
                                            className="absolute inset-0 rounded-lg border border-neon-cyan pointer-events-none"
                                            initial={false}
                                            transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                        />
                                    )}
                                </motion.button>
                            );
                        })}
                    </div>
                </div>
            ))}
        </div>
    );
}

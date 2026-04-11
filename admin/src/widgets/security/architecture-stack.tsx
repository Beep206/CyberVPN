'use client';

import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'framer-motion';
import { Server, Network, ShieldClose, ShieldCheck, Terminal, ChevronRight, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { type SecurityLayerId } from './security-dashboard';

interface Props {
    activeLayer: SecurityLayerId;
    setActiveLayer: (id: SecurityLayerId) => void;
}

const LAYERS: { id: SecurityLayerId; icon: LucideIcon }[] = [
    { id: 'bareMetal', icon: Server },
    { id: 'network', icon: Network },
    { id: 'crypto', icon: ShieldClose },
    { id: 'client', icon: Terminal },
];

export function ArchitectureStack({ activeLayer, setActiveLayer }: Props) {
    const t = useTranslations('Security.stack');

    return (
        <div className="w-full h-full p-8 flex flex-col pt-16">
            <div className="mb-12">
                <h2 className="text-sm font-cyber text-muted-foreground-low tracking-widest flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-neon-cyan" />
                    {t('title')}
                </h2>
                <div className="mt-4 h-px w-full bg-gradient-to-r from-neon-cyan/50 to-transparent" />
            </div>

            <div className="flex-1 flex flex-col justify-center gap-4">
                {LAYERS.map(({ id, icon: Icon }) => {
                    const isActive = activeLayer === id;

                    return (
                        <button
                            key={id}
                            onClick={() => setActiveLayer(id)}
                            className={cn(
                                "group relative flex flex-col text-left transition-all duration-500 rounded-lg border p-4 overflow-hidden",
                                isActive 
                                    ? "bg-neon-cyan/10 border-neon-cyan shadow-[0_0_20px_rgba(0,255,255,0.1)]" 
                                    : "bg-black/40 border-grid-line/30 hover:border-grid-line"
                            )}
                        >
                            {/* Animated Background Scanline for Active State */}
                            {isActive && (
                                <motion.div 
                                    layoutId="activeLayerBg"
                                    className="absolute inset-0 bg-neon-cyan/5 -z-10"
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                />
                            )}

                            <div className="flex items-center gap-4 relative z-10 w-full">
                                <div className={cn(
                                    "flex items-center justify-center w-10 h-10 rounded-md border bg-black transition-colors duration-500",
                                    isActive ? "text-neon-cyan border-neon-cyan" : "text-muted-foreground border-grid-line/50"
                                )}>
                                    <Icon className="w-5 h-5" />
                                </div>

                                <div className="flex flex-col flex-1">
                                    <span className={cn(
                                        "font-display font-medium tracking-wide transition-colors text-sm",
                                        isActive ? "text-white" : "text-white/60 group-hover:text-white/80"
                                    )}>
                                        {t(`${id}.title`)}
                                    </span>
                                </div>
                                
                                <ChevronRight className={cn(
                                    "w-4 h-4 transition-transform duration-300",
                                    isActive ? "text-neon-cyan translate-x-1" : "text-muted-foreground opacity-0 group-hover:opacity-100"
                                )} />
                            </div>

                            <AnimatePresence>
                                {isActive && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: 'auto', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        transition={{ duration: 0.3 }}
                                        className="overflow-hidden relative z-10"
                                    >
                                        <p className="font-mono text-xs text-muted-foreground mt-4 leading-relaxed pr-8 border-t border-neon-cyan/20 pt-4">
                                            {t(`${id}.description`)}
                                        </p>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

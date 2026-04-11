'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { cn } from '@/lib/utils';
import { FeatureId } from './features-dashboard';
import { Shield, Zap, EyeOff, Activity, LucideIcon } from 'lucide-react';

interface FeatureModulesProps {
    activeFeature: FeatureId;
    setActiveFeature: (id: FeatureId) => void;
}

const FEATURE_ICONS: Record<FeatureId, LucideIcon> = {
    quantum: Zap,
    multihop: Activity,
    obfuscation: EyeOff,
    killswitch: Shield,
};

export function FeatureModules({ activeFeature, setActiveFeature }: FeatureModulesProps) {
    const t = useTranslations('Features');

    const features: FeatureId[] = ['quantum', 'multihop', 'obfuscation', 'killswitch'];

    return (
        <div className="flex flex-col gap-4 w-full">
            {features.map((id, index) => {
                const isActive = activeFeature === id;
                const Icon = FEATURE_ICONS[id];

                return (
                    <motion.button
                        key={id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.5, delay: index * 0.1 }}
                        onClick={() => setActiveFeature(id)}
                        className={cn(
                            "relative w-full text-left p-6 rounded-xl border transition-all duration-300 group overflow-hidden",
                            isActive 
                                ? "bg-neon-cyan/10 border-neon-cyan shadow-[0_0_30px_rgba(0,255,255,0.15)]" 
                                : "bg-terminal-bg/50 border-grid-line/50 hover:border-neon-cyan/50 hover:bg-terminal-bg"
                        )}
                    >
                        {/* Interactive scanline sweep on active or hover */}
                        <div className={cn(
                            "absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full transition-transform duration-700",
                            isActive ? "animate-scan" : "group-hover:translate-x-[200%]"
                        )} />

                        <div className="relative z-10 flex items-start gap-4">
                            <div className={cn(
                                "flex-shrink-0 w-12 h-12 rounded-lg flex items-center justify-center border transition-colors duration-300",
                                isActive
                                    ? "bg-neon-cyan/20 border-neon-cyan text-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.4)]"
                                    : "bg-black/50 border-grid-line/50 text-muted-foreground group-hover:text-white group-hover:border-neon-cyan/30"
                            )}>
                                <Icon className="w-6 h-6" />
                            </div>

                            <div className="flex flex-col gap-1">
                                <div className="flex items-center gap-2">
                                    <span className="font-mono text-xs uppercase tracking-wider text-matrix-green">
                                        MODULE_{index + 1}
                                    </span>
                                    {isActive && (
                                        <span className="relative flex h-2 w-2">
                                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neon-cyan opacity-75"></span>
                                            <span className="relative inline-flex rounded-full h-2 w-2 bg-neon-cyan"></span>
                                        </span>
                                    )}
                                </div>
                                
                                <h3 className={cn(
                                    "font-display text-xl md:text-2xl font-bold tracking-tight transition-colors duration-300",
                                    isActive ? "text-neon-cyan" : "text-white group-hover:text-neon-cyan/80"
                                )}>
                                    {t(`features.${id}.title`)}
                                </h3>
                                
                                <p className="font-mono text-sm text-muted-foreground mt-2 line-clamp-2">
                                    {t(`features.${id}.description`)}
                                </p>
                            </div>
                        </div>

                        {/* Active state inner glow border */}
                        {isActive && (
                            <motion.div 
                                layoutId="activeFeatureGlow"
                                className="absolute inset-0 rounded-xl border border-neon-cyan pointer-events-none"
                                initial={false}
                                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                            />
                        )}
                    </motion.button>
                );
            })}
        </div>
    );
}

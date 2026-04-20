'use client';

import { motion } from 'motion/react';
import { useTranslations } from 'next-intl';
import { Check, Zap, Shield, Globe } from 'lucide-react';
import { TierLevel } from './pricing-dashboard';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

interface TierCardsProps {
    hoveredTier: TierLevel;
    onHover: (tier: TierLevel) => void;
}

const tierConfig = {
    basic: { icon: Globe, color: '#00ffff', border: 'border-neon-cyan/30', bgHover: 'hover:bg-neon-cyan/5' },
    pro: { icon: Zap, color: '#00ff88', border: 'border-matrix-green/50', bgHover: 'hover:bg-matrix-green/10' },
    elite: { icon: Shield, color: '#ff00ff', border: 'border-neon-purple/50', bgHover: 'hover:bg-neon-purple/10' }
};

export function TierCards({ hoveredTier, onHover }: TierCardsProps) {
    const t = useTranslations('Pricing.tiers');
    const tiers: ('basic' | 'pro' | 'elite')[] = ['basic', 'pro', 'elite'];

    return (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto px-4">
            {tiers.map((tierKey, index) => {
                const config = tierConfig[tierKey];
                const Icon = config.icon;
                const isHovered = hoveredTier === tierKey;
                const name = t(`${tierKey}.name`);
                const price = t(`${tierKey}.price`);
                const period = t(`${tierKey}.period`);
                const description = t(`${tierKey}.description`);
                const buttonText = t(`${tierKey}.button`);
                const badge = tierKey === 'pro' ? t('pro.badge') : null;

                // For testing array retrieval in next-intl
                // Features will be mocked or mapped sequentially depending on JSON setup.
                // Assuming features are passed as a single string separated by newlines or we use raw array
                const features = [
                    t(`${tierKey}.features.0`),
                    t(`${tierKey}.features.1`),
                    t(`${tierKey}.features.2`),
                    t(`${tierKey}.features.3`),
                    ...(tierKey !== 'basic' ? [t(`${tierKey}.features.4`)] : [])
                ];

                return (
                    <motion.div
                        key={tierKey}
                        initial={{ opacity: 0, y: 50 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.15, type: 'spring', damping: 20 }}
                        onMouseEnter={() => onHover(tierKey)}
                        onMouseLeave={() => onHover('none')}
                        className={cn(
                            "relative flex flex-col p-8 rounded-2xl border bg-black/40 backdrop-blur-xl transition-all duration-500 overflow-hidden cursor-crosshair group",
                            config.border,
                            config.bgHover,
                            isHovered ? "scale-105 shadow-2xl -translate-y-4" : "scale-100",
                            tierKey === 'pro' && !isHovered ? "shadow-[0_0_30px_-10px_rgba(0,255,136,0.3)]" : ""
                        )}
                        style={{
                            boxShadow: isHovered ? `0 20px 50px -15px ${config.color}40` : '',
                            borderColor: isHovered ? config.color : ''
                        }}
                    >
                        {/* Hover Overlay Gradient */}
                        {isHovered && (
                            <div 
                                className="absolute inset-0 opacity-20 pointer-events-none transition-opacity duration-1000 animate-pulse"
                                style={{ background: `radial-gradient(circle at top right, ${config.color}, transparent 70%)` }}
                            />
                        )}

                        {badge && (
                            <div className="absolute top-0 right-8 transform -translate-y-1/2">
                                <span className={cn(
                                    "px-4 py-1 rounded-full text-[10px] font-bold tracking-widest uppercase font-mono shadow-lg",
                                    "bg-matrix-green text-black border border-matrix-green"
                                )}>
                                    {badge}
                                </span>
                            </div>
                        )}

                        <div className="relative z-10 flex-1 flex flex-col">
                            <div className="flex items-center gap-4 mb-6">
                                <div 
                                    className="p-3 rounded-lg bg-black/50 border transition-colors duration-300"
                                    style={{ borderColor: isHovered ? config.color : `${config.color}40` }}
                                >
                                    <Icon className="w-6 h-6" style={{ color: config.color }} />
                                </div>
                                <h3 className="text-2xl font-display font-bold tracking-widest text-white uppercase group-hover:animate-glitch">
                                    {name}
                                </h3>
                            </div>

                            <div className="mb-6">
                                <div className="flex items-baseline gap-2">
                                    <span className="text-4xl lg:text-5xl font-mono font-black tracking-tighter text-white">
                                        {price}
                                    </span>
                                    <span className="text-sm font-mono text-muted-foreground uppercase tracking-widest">
                                        {period}
                                    </span>
                                </div>
                                <p className="mt-4 text-sm font-mono text-muted-foreground min-h-[40px]">
                                    {description}
                                </p>
                            </div>

                            <div className="flex-1">
                                <ul className="space-y-4 mb-8">
                                    {features.map((feature, i) => feature && (
                                        <motion.li 
                                            key={i} 
                                            className="flex items-start gap-3 text-sm font-mono text-white/80"
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: index * 0.1 + i * 0.05 }}
                                        >
                                            <Check className="w-5 h-5 shrink-0" style={{ color: config.color }} />
                                            <span>{feature}</span>
                                        </motion.li>
                                    ))}
                                </ul>
                            </div>

                            <Button 
                                className={cn(
                                    "w-full h-14 font-display font-bold tracking-widest uppercase transition-all duration-300 relative overflow-hidden group/btn border",
                                    "bg-black hover:bg-white hover:text-black"
                                )}
                                style={{
                                    borderColor: config.color,
                                    color: isHovered ? config.color : 'white'
                                }}
                            >
                                <div 
                                    className="absolute inset-0 opacity-10 transition-opacity group-hover/btn:opacity-100" 
                                    style={{ backgroundColor: config.color }} 
                                />
                                <span className="relative z-10 mix-blend-difference text-white">{buttonText}</span>
                            </Button>
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
}

'use client';

import { motion } from 'motion/react';
import { useTranslations } from 'next-intl';
import { Monitor, Apple, TerminalSquare, Smartphone, Laptop } from 'lucide-react';
import { OSPlatform } from './download-dashboard';
import { cn } from '@/lib/utils';

interface OSSelectorProps {
    selectedOS: OSPlatform;
    onSelect: (os: OSPlatform) => void;
}

const platforms: { id: OSPlatform; icon: any; color: string; labelKey: string }[] = [
    { id: 'windows', icon: Monitor, color: '#00ffff', labelKey: 'windows' }, // Cyber-cyan
    { id: 'macos', icon: Apple, color: '#ffffff', labelKey: 'macos' }, // White/Silver
    { id: 'linux', icon: TerminalSquare, color: '#ffb800', labelKey: 'linux' }, // Warning orange/yellow
    { id: 'ios', icon: Smartphone, color: '#a0a0a0', labelKey: 'ios' }, // Grey
    { id: 'android', icon: Laptop, color: '#00ff88', labelKey: 'android' }, // Matrix green
];

export function OSSelector({ selectedOS, onSelect }: OSSelectorProps) {
    const t = useTranslations('Download.platforms');

    return (
        <div className="flex flex-col gap-3">
            {platforms.map((platform, i) => {
                const Icon = platform.icon;
                const isSelected = selectedOS === platform.id;
                
                return (
                    <motion.button
                        key={platform.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        onClick={() => onSelect(platform.id)}
                        className={cn(
                            "relative flex items-center gap-4 p-4 rounded-xl border transition-all duration-300 overflow-hidden text-left outline-none group",
                            isSelected 
                                ? "bg-black/80 border-white/40 shadow-lg scale-[1.02]" 
                                : "bg-black/40 border-white/10 hover:border-white/30 hover:bg-black/60"
                        )}
                        style={{
                            boxShadow: isSelected ? `0 0 20px -5px ${platform.color}` : 'none'
                        }}
                    >
                        {/* Hover & Active Glare */}
                        {isSelected && (
                            <div 
                                className="absolute inset-0 opacity-20 bg-gradient-to-r pointer-events-none"
                                style={{ backgroundImage: `linear-gradient(to right, ${platform.color}, transparent)` }}
                            />
                        )}

                        <div 
                            className={cn(
                                "flex items-center justify-center w-10 h-10 rounded-lg border bg-black/50 transition-colors",
                                isSelected ? "border-transparent" : "border-white/10 group-hover:border-white/20"
                            )}
                            style={{ 
                                backgroundColor: isSelected ? `${platform.color}15` : '',
                                borderColor: isSelected ? platform.color : ''
                            }}
                        >
                            <Icon 
                                className="w-5 h-5 transition-transform group-hover:scale-110" 
                                style={{ color: isSelected ? platform.color : '#666' }} 
                            />
                        </div>

                        <div className="flex-1">
                            <span className={cn(
                                "font-mono text-sm tracking-widest uppercase transition-colors",
                                isSelected ? "text-white font-bold" : "text-muted-foreground group-hover:text-white/80"
                            )}>
                                {t(platform.labelKey)}
                            </span>
                        </div>
                        
                        {/* Status Dot */}
                        <div className={cn(
                            "w-2 h-2 rounded-full transition-all duration-500",
                            isSelected ? "opacity-100 animate-pulse" : "opacity-0"
                        )}
                        style={{ backgroundColor: platform.color }}
                        />
                    </motion.button>
                );
            })}
        </div>
    );
}

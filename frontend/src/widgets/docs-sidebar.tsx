'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { TerminalSquare, Shield, Activity, Zap } from 'lucide-react';
import Link from 'next/link';

interface DocsSidebarProps {
    activeSection: string;
}

export function DocsSidebar({ activeSection }: DocsSidebarProps) {
    const t = useTranslations('Docs');

    const sections = [
        {
            categoryKey: 'sidebar_category_basics',
            items: [
                { id: 'getting_started', titleKey: 'section_getting_started', icon: TerminalSquare },
                { id: 'routing', titleKey: 'section_routing', icon: Zap }
            ]
        },
        {
            categoryKey: 'sidebar_category_advanced',
            items: [
                { id: 'security', titleKey: 'section_security', icon: Shield },
                { id: 'api', titleKey: 'section_api', icon: Activity }
            ]
        }
    ];

    return (
        <nav className="w-full pr-4 border-r border-terminal-border/50 h-[calc(100vh-120px)] overflow-y-auto no-scrollbar pb-10">
            <h2 className="text-sm font-cyber text-neon-cyan tracking-widest mb-8 uppercase flex items-center gap-2">
                <div className="w-2 h-2 bg-neon-cyan/80 rotate-45" />
                SYSTEM_INDEX
            </h2>

            <div className="space-y-8">
                {sections.map((group, gIdx) => (
                    <div key={gIdx} className="space-y-3">
                        <h3 className="text-xs font-mono text-muted-foreground/50 tracking-wider uppercase pl-4 border-l border-terminal-border/30">
                            {t(group.categoryKey as any)}
                        </h3>
                        <ul className="space-y-1">
                            {group.items.map((item) => {
                                const isActive = activeSection === item.id;
                                const Icon = item.icon;
                                
                                return (
                                    <li key={item.id}>
                                        <Link 
                                            href={`#${item.id}`}
                                            className={`w-full flex items-center gap-3 px-4 py-2 text-sm font-mono transition-all duration-300 relative group
                                                ${isActive ? 'text-neon-cyan' : 'text-muted-foreground hover:text-foreground'}
                                            `}
                                        >
                                            {/* Active Indicator Glow */}
                                            {isActive && (
                                                <motion.div 
                                                    layoutId="sidebarActiveIndiciator"
                                                    className="absolute left-0 top-0 bottom-0 w-[2px] bg-neon-cyan shadow-[0_0_10px_rgba(0,255,255,1)]"
                                                    initial={{ opacity: 0 }}
                                                    animate={{ opacity: 1 }}
                                                    transition={{ duration: 0.3 }}
                                                />
                                            )}
                                            
                                            {/* Hover Left Bar */}
                                            {!isActive && (
                                                <div className="absolute left-0 top-1/4 bottom-1/4 w-[1px] bg-terminal-border opacity-0 group-hover:opacity-100 transition-opacity" />
                                            )}

                                            <Icon className={`w-4 h-4 ${isActive ? 'opacity-100' : 'opacity-40 group-hover:opacity-80'}`} />
                                            <span className="truncate">{t(item.titleKey as any)}</span>
                                        </Link>
                                    </li>
                                );
                            })}
                        </ul>
                    </div>
                ))}
            </div>
            
            {/* Ambient Background decoration */}
            <div className="absolute bottom-0 left-0 w-full h-32 bg-gradient-to-t from-background to-transparent pointer-events-none" />
        </nav>
    );
}

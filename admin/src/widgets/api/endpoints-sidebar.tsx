'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { cn } from '@/lib/utils';
import { ActiveEndpoint, EndpointCategory, EndpointId } from './api-dashboard';
import { ChevronRight, Key, Server, Hash } from 'lucide-react';
import { useMemo } from 'react';

interface EndpointsSidebarProps {
    activeEndpoint: ActiveEndpoint;
    setActiveEndpoint: (e: ActiveEndpoint) => void;
}

export function EndpointsSidebar({ activeEndpoint, setActiveEndpoint }: EndpointsSidebarProps) {
    const t = useTranslations('Api');

    // Define the structure of our sidebar based on the translations
    const structure = useMemo(() => [
        {
            categoryId: 'auth' as EndpointCategory,
            icon: <Key className="w-4 h-4" />,
            endpoints: [
                { id: 'generateToken' as EndpointId, method: 'POST', path: '/auth/token' }
            ]
        },
        {
            categoryId: 'servers' as EndpointCategory,
            icon: <Server className="w-4 h-4" />,
            endpoints: [
                { id: 'listServers' as EndpointId, method: 'GET', path: '/servers' },
                { id: 'connect' as EndpointId, method: 'POST', path: '/servers/connect' }
            ]
        }
    ], []);

    const getMethodColor = (method: string) => {
        switch (method) {
            case 'GET': return 'text-matrix-green border-matrix-green/30 bg-matrix-green/10';
            case 'POST': return 'text-neon-cyan border-neon-cyan/30 bg-neon-cyan/10';
            case 'DELETE': return 'text-red-500 border-red-500/30 bg-red-500/10';
            case 'PUT': return 'text-neon-purple border-neon-purple/30 bg-neon-purple/10';
            default: return 'text-muted-foreground border-grid-line/30 bg-terminal-bg';
        }
    };

    return (
        <div className="flex flex-col gap-8 w-full">
            {structure.map((category, cIdx) => (
                <div key={category.categoryId} className="flex flex-col gap-3">
                    <h3 className="font-display text-sm font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-2 mb-2">
                        {category.icon}
                        {t(`endpoints.${category.categoryId}.category`)}
                    </h3>
                    
                    <div className="flex flex-col gap-2">
                        {category.endpoints.map((endpoint, eIdx) => {
                            const isActive = activeEndpoint.category === category.categoryId && activeEndpoint.id === endpoint.id;
                            
                            return (
                                <motion.button
                                    key={endpoint.id}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ duration: 0.3, delay: cIdx * 0.1 + eIdx * 0.05 }}
                                    onClick={() => setActiveEndpoint({ category: category.categoryId, id: endpoint.id })}
                                    className={cn(
                                        "relative w-full text-left p-3 rounded-md border transition-all duration-300 group overflow-hidden flex flex-col gap-2",
                                        isActive 
                                            ? "bg-neon-cyan/10 border-neon-cyan shadow-[0_0_15px_rgba(0,255,255,0.1)]" 
                                            : "bg-terminal-bg/50 border-grid-line/30 hover:border-neon-cyan/50 hover:bg-terminal-bg"
                                    )}
                                >
                                    {isActive && (
                                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent animate-scan -translate-x-full" />
                                    )}

                                    <div className="relative z-10 flex items-center justify-between w-full">
                                        <div className="flex items-center gap-3">
                                            <span className={cn(
                                                "font-mono text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border",
                                                getMethodColor(endpoint.method)
                                            )}>
                                                {endpoint.method}
                                            </span>
                                            <span className={cn(
                                                "font-display text-sm font-bold transition-colors duration-300",
                                                isActive ? "text-white" : "text-muted-foreground group-hover:text-white"
                                            )}>
                                                {t(`endpoints.${category.categoryId}.items.${endpoint.id}.title`)}
                                            </span>
                                        </div>
                                        <ChevronRight className={cn(
                                            "w-4 h-4 transition-all duration-300",
                                            isActive ? "text-neon-cyan translate-x-1 opacity-100" : "text-muted-foreground opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 group-hover:text-neon-cyan/50"
                                        )} />
                                    </div>
                                    
                                    <div className="relative z-10 font-mono text-xs text-muted-foreground/70 flex items-center gap-1.5 overflow-hidden text-ellipsis whitespace-nowrap">
                                        <Hash className="w-3 h-3 opacity-50 shrink-0" />
                                        {endpoint.path}
                                    </div>

                                    {isActive && (
                                        <motion.div 
                                            layoutId="activeApiEndpointGlow"
                                            className="absolute inset-0 rounded-md border border-neon-cyan pointer-events-none"
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

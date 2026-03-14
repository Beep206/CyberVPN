'use client';

import * as React from 'react';
import { motion } from 'motion/react';

export interface StatusBadgeLiveProps {
    protocol?: string;
    status?: string;
    latency?: string;
    nodeName?: string;
    className?: string;
}

export function StatusBadgeLive({ 
    protocol = "VLESS-Reality", 
    status = "ONLINE", 
    latency, 
    nodeName, 
    className = '' 
}: StatusBadgeLiveProps) {
    return (
        <div className={`inline-flex items-center gap-3 px-3 py-1.5 border border-grid-line/40 rounded-sm bg-terminal-bg/50 backdrop-blur font-mono text-xs uppercase tracking-wider ${className}`}>
            {nodeName && (
                <span className="text-muted-foreground">{nodeName}:</span>
            )}
            
            <div className="flex items-center gap-2 text-neon-cyan">
                <span className="font-semibold">{protocol}</span>
            </div>

            <div className="flex items-center gap-1.5">
                <span className="text-[color:var(--color-server-online)] font-bold">
                    ({status})
                </span>
                <motion.div
                    className="w-2 h-2 rounded-full bg-[color:var(--color-server-online)] shadow-[0_0_8px_var(--color-server-online)]"
                    animate={{ opacity: [1, 0.4, 1], scale: [1, 0.8, 1] }}
                    transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                />
            </div>

            {latency && (
                <div className="pl-2 border-l border-grid-line/50 text-muted-foreground">
                    {latency}
                </div>
            )}
        </div>
    );
}

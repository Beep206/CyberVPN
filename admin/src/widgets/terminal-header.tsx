'use client';

import { Bell, Search, Wifi } from 'lucide-react';
import { useEffect, useState } from 'react';
import { CypherText } from '@/shared/ui/atoms/cypher-text';

export function TerminalHeader() {
    const [time, setTime] = useState<string>('');

    // Hydration fix for time
    useEffect(() => {
        const updateTime = () => setTime(new Date().toISOString().split('T')[1].split('.')[0] + ' UTC');
        updateTime();
        const timer = setInterval(updateTime, 1000);
        return () => clearInterval(timer);
    }, []);

    return (
        <header className="sticky top-0 z-30 flex h-16 w-full items-center gap-4 bg-terminal-surface/80 backdrop-blur-xl border-b border-grid-line/30 px-6 transition-all">
            <div className="flex flex-1 items-center gap-4">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-grid-line/30 bg-black/20 text-muted-foreground hover:text-foreground">
                    <Search className="h-4 w-4" />
                </div>

                {/* Cypher Text Status */}
                <div className="hidden md:flex items-center text-xs font-cyber text-muted-foreground/50">
                    <span className="mr-1">SYSTEM:</span>
                    <CypherText text="INTEGRITY CHECK PASSED" className="text-neon-cyan" />
                    <span className="mx-2">|</span>
                    <span className="mr-1">ENCRYPTION:</span>
                    <CypherText text="ACTIVE - AES-256" className="text-neon-purple" />
                </div>
            </div>

            <div className="flex items-center gap-4">
                {/* Network Pulse */}
                <div className="flex items-center gap-2 text-xs font-mono text-matrix-green bg-matrix-green/10 px-3 py-1 rounded-full border border-matrix-green/30">
                    <Wifi className="h-3 w-3 animate-pulse" />
                    <span>NET_UPLINK</span>
                </div>

                <div className="font-cyber text-sm text-neon-cyan/80 min-w-[100px] text-right">
                    {time || "--:--:--"}
                </div>

                <button className="relative rounded-full p-2 text-muted-foreground hover:bg-white/5 hover:text-foreground">
                    <Bell className="h-5 w-5" />
                    <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-neon-pink shadow-[0_0_8px_#ff0055]" />
                </button>
            </div>
        </header>
    );
}

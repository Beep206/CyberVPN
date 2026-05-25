'use client';

import { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTranslations } from 'next-intl';
import { Terminal, Download as DownloadIcon } from 'lucide-react';
import { OSPlatform } from './download-dashboard';
import { Button } from '@/components/ui/button';
import { CypherText } from '@/shared/ui/atoms/cypher-text';

interface TerminalVerifierProps {
    selectedOS: OSPlatform;
}

export function TerminalVerifier({ selectedOS }: TerminalVerifierProps) {
    const t = useTranslations('Download.terminal');
    const [logs, setLogs] = useState<string[]>([]);
    const [isReady, setIsReady] = useState(false);
    const scrollRef = useRef<HTMLDivElement>(null);

    // Simulated terminal output sequence
    useEffect(() => {
        const timeoutIds: Array<ReturnType<typeof setTimeout>> = [];

        if (selectedOS === 'none') {
            const resetId = setTimeout(() => {
                setLogs(['[SYS] AWAITING PLATFORM SELECTION...']);
                setIsReady(false);
            }, 0);

            return () => clearTimeout(resetId);
        }

        const initId = setTimeout(() => {
            setIsReady(false);
            setLogs([t('init')]);
        }, 0);
        timeoutIds.push(initId);

        const sequence = [
            { text: `${t('verify')} ${selectedOS.toUpperCase()}`, delay: 800 },
            { text: '[OK] HANDSHAKE VERIFIED.', delay: 1500 },
            { text: t('compiling'), delay: 2500 },
            { text: '[OK] SIGNATURE INTACT.', delay: 3500 },
            { text: t('ready'), delay: 4500 }
        ];

        sequence.forEach((step) => {
            const id = setTimeout(() => {
                setLogs((prev) => [...prev, step.text]);
                if (step.text === t('ready')) {
                    setIsReady(true);
                }
            }, step.delay);
            timeoutIds.push(id);
        });

        return () => timeoutIds.forEach(clearTimeout);
    }, [selectedOS, t]);

    // Auto-scroll to bottom of logs
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <div className="relative flex min-h-[250px] flex-1 flex-col overflow-hidden rounded-xl border border-border/60 bg-card/85 shadow-2xl backdrop-blur-xl dark:border-white/10 dark:bg-black/60">
            {/* Terminal Header */}
            <div className="flex items-center gap-2 border-b border-border/60 bg-muted/40 p-3 dark:border-white/5 dark:bg-white/[0.02]">
                <Terminal className="w-4 h-4 text-neon-cyan" />
                <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground dark:text-white/50">Compiler.exe</span>
            </div>

            {/* Terminal Output */}
            <div ref={scrollRef} className="flex-1 p-4 font-mono text-xs overflow-y-auto space-y-2 relative custom-scrollbar">
                {logs.map((log, i) => (
                    <motion.div 
                        key={`${selectedOS}-${i}`}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                    >
                        <span className="text-neon-cyan/50 mr-2">{'>'}</span>
                        <span className={log.includes('[OK]') || log.includes('READY') ? 'text-matrix-green' : 'text-foreground/80 dark:text-white/80'}>
                            {log}
                        </span>
                    </motion.div>
                ))}
            </div>

            {/* Action Bar (Revealed when ready) */}
            <div className="flex min-h-[80px] items-center justify-center border-t border-border/60 bg-muted/40 p-4 dark:border-white/5 dark:bg-black/40">
                <AnimatePresence mode="wait">
                    {isReady ? (
                        <motion.div
                            key="ready"
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="w-full"
                        >
                            <Button className="w-full relative group overflow-hidden bg-white text-black hover:bg-neon-cyan hover:text-black transition-all duration-300 h-12 font-display font-bold tracking-widest uppercase">
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent -translate-x-full group-hover:animate-shimmer" />
                                <DownloadIcon className="w-4 h-4 mr-2" />
                                {t('button')}
                            </Button>
                            <div className="mt-2 text-center font-mono text-[10px] uppercase tracking-wider text-muted-foreground dark:text-white/30">
                                {t('version')} <CypherText text="v2.4.1" className="text-neon-cyan" />
                            </div>
                        </motion.div>
                    ) : (
                        <motion.div
                            key="waiting"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex animate-pulse items-center gap-2 font-mono text-xs uppercase tracking-widest text-muted-foreground dark:text-white/20"
                        >
                            <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/30 dark:bg-white/20" />
                            Awaiting Signal
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

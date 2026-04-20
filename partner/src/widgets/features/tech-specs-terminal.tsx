'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { FeatureId } from './features-dashboard';
import { Terminal } from 'lucide-react';

interface TechSpecsTerminalProps {
    activeFeature: FeatureId;
}

function FeatureSpecsSequence({ activeFeature }: TechSpecsTerminalProps) {
    const t = useTranslations('Features');
    const [specLines, setSpecLines] = useState<string[]>([]);

    useEffect(() => {
        const rawSpecs = [
            t(`features.${activeFeature}.specs.0`),
            t(`features.${activeFeature}.specs.1`),
            t(`features.${activeFeature}.specs.2`)
        ];

        let currentLine = 0;
        let timeoutId: number | null = null;

        const typeLines = () => {
            setSpecLines((prev) => [...prev, rawSpecs[currentLine]]);
            currentLine += 1;

            if (currentLine < rawSpecs.length) {
                timeoutId = window.setTimeout(typeLines, 400 + Math.random() * 300);
            }
        };

        timeoutId = window.setTimeout(typeLines, 300);

        return () => {
            if (timeoutId !== null) {
                window.clearTimeout(timeoutId);
            }
        };
    }, [activeFeature, t]);

    return (
        <div className="flex flex-col gap-1 pl-4 border-l border-matrix-green/30 ml-2">
            {specLines.map((line, idx) => (
                <motion.div
                    key={idx}
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="text-white/90 flex items-start gap-2"
                >
                    <span className="text-neon-cyan/50 mt-0.5">{'>'}</span>
                    {line}
                </motion.div>
            ))}

            {specLines.length < 3 && (
                <motion.div
                    animate={{ opacity: [1, 0, 1] }}
                    transition={{ repeat: Infinity, duration: 0.8 }}
                    className="w-2 h-4 bg-neon-cyan mt-1 ml-6"
                />
            )}
        </div>
    );
}

export function TechSpecsTerminal({ activeFeature }: TechSpecsTerminalProps) {
    return (
        <div className="w-full mt-6 flex flex-col items-end">
            <div className="w-full max-w-lg bg-[#050505] border border-grid-line/50 rounded-lg overflow-hidden relative shadow-[0_10px_40px_rgba(0,255,255,0.05)]">
                
                {/* Terminal Header */}
                <div className="h-8 bg-[#111] border-b border-grid-line/50 flex items-center px-4 gap-2">
                    <div className="flex gap-1.5">
                        <div className="w-2.5 h-2.5 rounded-full bg-red-500/80" />
                        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80" />
                        <div className="w-2.5 h-2.5 rounded-full bg-green-500/80" />
                    </div>
                    <div className="mx-auto flex items-center gap-2 text-muted-foreground-low text-[10px] font-mono uppercase tracking-widest">
                        <Terminal className="w-3 h-3" />
                        sys_specs.exe
                    </div>
                </div>

                {/* Terminal Body */}
                <div className="p-5 font-mono text-sm relative min-h-[160px]">
                    <div
                        className="absolute inset-0 opacity-20 pointer-events-none mix-blend-overlay"
                        style={{ backgroundImage: "url('/scanlines.svg')" }}
                    />
                    
                    <AnimatePresence mode="wait">
                        <motion.div
                            key={activeFeature}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="flex flex-col gap-3"
                        >
                            <div className="text-muted-foreground flex items-center gap-2">
                                <span className="text-neon-cyan">root@cybervpn:~$</span>
                                <span>inspect module --target {activeFeature}</span>
                            </div>

                            <div className="text-matrix-green">
                                Analyzing payload constraints... [OK]
                            </div>

                            <FeatureSpecsSequence key={activeFeature} activeFeature={activeFeature} />
                        </motion.div>
                    </AnimatePresence>
                </div>
                
                {/* Glow bar at bottom */}
                <div className="absolute bottom-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-matrix-green/50 to-transparent" />
            </div>
        </div>
    );
}

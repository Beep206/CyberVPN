'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { TerminalSquare, Cpu, Lock, Fingerprint, RefreshCcw } from 'lucide-react';
import { ScrambleText } from '@/shared/ui/scramble-text';

const QA_COUNT = 4;

// Helper icons map
const ICONS = [Cpu, Lock, Fingerprint, TerminalSquare];

export function HelpFaq() {
    const t = useTranslations('HelpCenter');
    const [activeIndex, setActiveIndex] = useState<number>(0);
    const [isDecrypting, setIsDecrypting] = useState(false);
    const [typedAnswer, setTypedAnswer] = useState('');

    const currentAnswer = t(`faq_${activeIndex + 1}_a` as any);

    // Terminal Decoder typewriter effect logic
    useEffect(() => {
        setIsDecrypting(true);
        setTypedAnswer('');
        
        // Initial "scramble/decrypting" phase
        const decryptTimout = setTimeout(() => {
            setIsDecrypting(false);
            
            // Typewriter phase
            let i = 0;
            const typeInterval = setInterval(() => {
                if (i <= currentAnswer.length) {
                    setTypedAnswer(currentAnswer.slice(0, i));
                    i += 2; // Type 2 chars at a time for speed (WOW effect)
                } else {
                    clearInterval(typeInterval);
                }
            }, 10);

            return () => clearInterval(typeInterval);
        }, 800);

        return () => clearTimeout(decryptTimout);
    }, [activeIndex, currentAnswer]);

    return (
        <section id="faq" className="relative w-full max-w-6xl mx-auto mb-32 scroll-mt-32">
            <div className="flex items-center gap-4 mb-12">
                <div className="h-px bg-terminal-border flex-1" />
                <h2 className="text-2xl font-display font-bold text-foreground tracking-widest uppercase">
                    {t('faq_title')} <span className="text-neon-cyan opacity-80 text-sm ml-2 font-mono">[DECRYPTION_MATRIX]</span>
                </h2>
                <div className="h-px bg-terminal-border flex-1" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 relative">
                
                {/* Background ambient glow for the whole section */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full max-w-lg bg-neon-cyan/5 blur-[120px] pointer-events-none rounded-full" />

                {/* LEFT PANEL: The Node List (Questions) */}
                <div className="lg:col-span-5 flex flex-col gap-4 relative z-10">
                    <p className="font-mono text-muted-foreground/50 text-xs mb-2 pl-2">SELECT_NODE_FOR_DECRYPTION</p>
                    
                    {Array.from({ length: QA_COUNT }).map((_, idx) => {
                        const isActive = activeIndex === idx;
                        const question = t(`faq_${idx + 1}_q` as any);
                        const Icon = ICONS[idx % ICONS.length];

                        return (
                            <motion.button
                                key={idx}
                                initial={{ opacity: 0, x: -20 }}
                                whileInView={{ opacity: 1, x: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.4, delay: idx * 0.1 }}
                                onClick={() => setActiveIndex(idx)}
                                className={`group relative w-full flex items-center gap-4 p-4 rounded-xl border transition-all duration-300 overflow-hidden text-left focus:outline-none ${isActive ? 'bg-terminal-card border-neon-cyan shadow-[0_0_20px_rgba(0,255,255,0.15)]' : 'bg-terminal-bg/50 border-terminal-border/50 hover:bg-terminal-card/80 hover:border-terminal-border'}`}
                            >
                                {/* Active background gradient */}
                                {isActive && (
                                    <motion.div 
                                        layoutId="activeFaqBg" 
                                        className="absolute inset-0 bg-gradient-to-r from-neon-cyan/10 to-transparent z-0" 
                                        initial={false}
                                        transition={{ type: "spring", stiffness: 300, damping: 30 }}
                                    />
                                )}
                                
                                {/* Icon Container */}
                                <div className={`relative z-10 w-12 h-12 rounded-lg flex items-center justify-center shrink-0 border transition-colors ${isActive ? 'bg-neon-cyan/10 border-neon-cyan text-neon-cyan' : 'bg-terminal-bg border-terminal-border/50 text-muted-foreground group-hover:text-foreground group-hover:border-terminal-border'}`}>
                                    <Icon className="w-5 h-5" />
                                </div>
                                
                                <span className={`relative z-10 font-display text-sm md:text-base tracking-wide transition-colors ${isActive ? 'text-foreground font-bold' : 'text-muted-foreground group-hover:text-foreground/90'}`}>
                                    {question}
                                </span>

                                {/* Tech accents */}
                                {isActive && (
                                    <div className="absolute right-0 top-0 h-full w-1 bg-neon-cyan blur-[1px] shadow-[0_0_10px_rgba(0,255,255,1)]" />
                                )}
                            </motion.button>
                        );
                    })}
                </div>

                {/* RIGHT PANEL: The Primary Databank Terminal (Answers) */}
                <div className="lg:col-span-7 relative z-10">
                    <p className="font-mono text-neon-cyan/50 text-xs mb-2 pl-2">SECURE_DATABANK_FEED</p>
                    
                    <div className="w-full h-full min-h-[300px] bg-terminal-card/80 backdrop-blur-md rounded-xl border border-neon-cyan/30 shadow-[0_0_30px_rgba(0,255,255,0.05)] overflow-hidden relative group">
                        
                        {/* Terminal Header */}
                        <div className="w-full h-10 border-b border-terminal-border bg-terminal-bg/50 flex items-center justify-between px-4">
                            <div className="flex gap-2">
                                <div className="w-3 h-3 rounded-full bg-red-500/50" />
                                <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                                <div className="w-3 h-3 rounded-full bg-green-500/50 bg-neon-cyan/50 shadow-[0_0_8px_rgba(0,255,255,0.8)]" />
                            </div>
                            <div className="font-mono text-xs text-muted-foreground/60 flex items-center gap-2">
                                <Lock className="w-3 h-3" /> E2E_ENCRYPTED_STREAM
                            </div>
                        </div>

                        {/* Terminal Body */}
                        <div className="p-8 relative">
                            {/* Persistent Scanline moving down */}
                            <div className="absolute inset-0 scanline opacity-30 pointer-events-none" />

                            <AnimatePresence mode="wait">
                                <motion.div
                                    key={activeIndex}
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    transition={{ duration: 0.2 }}
                                    className="font-mono text-base md:text-lg text-foreground/90 leading-relaxed"
                                >
                                    {isDecrypting ? (
                                        <div className="flex flex-col items-center justify-center h-48 text-neon-cyan space-y-4">
                                            <motion.div 
                                                animate={{ rotate: 360 }} 
                                                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                                            >
                                                <RefreshCcw className="w-8 h-8" />
                                            </motion.div>
                                            <div className="text-xl font-display font-bold tracking-widest">
                                                <ScrambleText text="DECRYPTING..." />
                                            </div>
                                            <div className="w-48 h-1 bg-terminal-border rounded overflow-hidden">
                                                <motion.div 
                                                    className="h-full bg-neon-cyan" 
                                                    initial={{ width: "0%" }} 
                                                    animate={{ width: "100%" }} 
                                                    transition={{ duration: 0.8 }} 
                                                />
                                            </div>
                                        </div>
                                    ) : (
                                        <div className="relative">
                                            <h3 className="text-xl font-display font-bold text-neon-cyan mb-6 tracking-wide drop-shadow-[0_0_8px_rgba(0,255,255,0.5)]">
                                                &gt; {t(`faq_${activeIndex + 1}_q` as any)}
                                            </h3>
                                            
                                            {/* decorative line */}
                                            <div className="absolute left-0 top-14 bottom-0 w-px bg-gradient-to-b from-neon-cyan/50 to-transparent" />
                                            
                                            <div className="pl-6">
                                                {typedAnswer}
                                                <motion.span 
                                                    animate={{ opacity: [1, 0] }}
                                                    transition={{ repeat: Infinity, duration: 0.8 }}
                                                    className="inline-block w-2.5 h-5 bg-neon-cyan ml-1 align-sub"
                                                />
                                            </div>
                                        </div>
                                    )}
                                </motion.div>
                            </AnimatePresence>
                        </div>
                        
                        {/* Background structural lines */}
                        <div className="absolute bottom-0 right-0 w-32 h-32 border-b border-r border-neon-cyan/20 rounded-br-xl m-4 pointer-events-none" />
                        <div className="absolute top-10 right-4 font-cyber text-[10px] text-muted-foreground/30 rotate-90 origin-right pointer-events-none">
                            DATA_ID_7493_A
                        </div>
                    </div>
                </div>

            </div>
        </section>
    );
}

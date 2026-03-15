'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion } from 'framer-motion';
import { TerminalSquare, Fingerprint } from 'lucide-react';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { cn } from '@/lib/utils';

export function SignatureTerminal({
    isAccepted,
    onAccept
}: {
    isAccepted: boolean;
    onAccept: () => void;
}) {
    const t = useTranslations('Terms.terminal');
    const [isHovered, setIsHovered] = useState(false);

    return (
        <div className="w-full py-32 px-6 flex flex-col items-center justify-center relative z-20">
            
            {/* The Terminal Container */}
            <motion.div 
                initial={{ opacity: 0, y: 50 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: "all" }}
                className={cn(
                    "w-full max-w-2xl border bg-black/80 backdrop-blur-md rounded-xl overflow-hidden transition-all duration-700",
                    isAccepted ? "border-matrix-green shadow-[0_0_40px_rgba(0,255,136,0.2)]" : "border-neon-cyan/30 shadow-[0_0_20px_rgba(0,255,255,0.05)]"
                )}
            >
                {/* Terminal Header */}
                <div className="flex items-center gap-2 px-4 py-3 border-b border-grid-line/30 bg-terminal-bg/50">
                    <TerminalSquare className={cn("w-4 h-4", isAccepted ? "text-matrix-green" : "text-neon-cyan")} />
                    <span className="font-mono text-xs text-muted-foreground">root@cybervpn:~/directives#</span>
                </div>

                {/* Terminal Body */}
                <div className="p-8 md:p-12 flex flex-col items-center justify-center min-h-[250px] relative overflow-hidden">
                    
                    {/* Background scanline effect */}
                    <div className="absolute inset-0 bg-[url('/scanlines.png')] opacity-20 pointer-events-none mix-blend-overlay" />

                    {!isAccepted ? (
                        <>
                            <p className="font-mono text-warning text-sm mb-8 animate-pulse text-center">
                                {t('prompt')}
                            </p>

                            <button
                                onClick={onAccept}
                                onMouseEnter={() => setIsHovered(true)}
                                onMouseLeave={() => setIsHovered(false)}
                                className="group relative px-8 py-4 bg-neon-cyan/10 border border-neon-cyan text-neon-cyan font-cyber tracking-widest text-lg hover:bg-neon-cyan hover:text-black transition-all duration-300 overflow-hidden"
                            >
                                {/* Glitch background hover effect */}
                                <div className="absolute inset-0 bg-white/20 -translate-x-full group-hover:animate-[glitch_0.3s_linear_infinite] mix-blend-overlay" />
                                
                                <span className="relative z-10 flex items-center justify-center gap-3">
                                    <Fingerprint className="w-5 h-5 group-hover:scale-110 transition-transform" />
                                    <CypherText 
                                        text={t('command')} 
                                        loop={isHovered} 
                                        loopDelay={500} 
                                        className={isHovered ? "text-black" : "text-neon-cyan"} 
                                    />
                                </span>
                            </button>
                        </>
                    ) : (
                        <motion.div 
                            initial={{ scale: 0.8, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            className="flex flex-col items-center gap-4"
                        >
                            <div className="w-16 h-16 rounded-full bg-matrix-green/20 border border-matrix-green flex items-center justify-center shadow-[0_0_30px_rgba(0,255,136,0.4)]">
                                <motion.div
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
                                    className="absolute inset-0 border-t-2 border-matrix-green rounded-full"
                                />
                                <Fingerprint className="w-8 h-8 text-matrix-green" />
                            </div>
                            <p className="font-mono text-matrix-green text-center text-sm md:text-base animate-pulse">
                                {t('verified')}
                            </p>
                        </motion.div>
                    )}

                </div>
            </motion.div>
        </div>
    );
}

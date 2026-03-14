'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { Terminal, Copy, Check } from 'lucide-react';
import { useState } from 'react';

export function QuickStart() {
    const t = useTranslations('Landing.quick_start');
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText('@CyberVPN_Bot');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <section className="relative py-24 bg-terminal-bg border-t border-grid-line/20 overflow-hidden">
            {/* Glows */}
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-neon-cyan/5 dark:bg-neon-cyan/10 rounded-full blur-[120px] pointer-events-none" />

            <div className="container mx-auto px-4 relative z-10 max-w-4xl text-center flex flex-col items-center">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                >
                    <h2 className="text-4xl md:text-5xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-cyan to-matrix-green mb-12">
                        {t('title')}
                    </h2>
                </motion.div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full mt-8">
                    {/* Step 1 */}
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 }}
                        className="flex flex-col items-center gap-4 group"
                    >
                        <div className="w-16 h-16 rounded-2xl bg-terminal-surface/80 border border-neon-cyan/30 flex items-center justify-center text-neon-cyan font-bold text-xl relative">
                            1
                            <div className="absolute inset-0 rounded-2xl border border-neon-cyan/50 scale-110 opacity-0 group-hover:opacity-100 group-hover:scale-125 transition-all duration-500" />
                        </div>
                        <p className="text-muted-foreground font-mono text-center flex flex-col items-center gap-2">
                            {t('step1')}
                            <button 
                                onClick={handleCopy}
                                className="inline-flex items-center gap-2 px-3 py-1 bg-neon-cyan/10 text-neon-cyan rounded hover:bg-neon-cyan/20 transition-colors"
                            >
                                @CyberVPN_Bot
                                {copied ? <Check size={14} /> : <Copy size={14} />}
                            </button>
                        </p>
                    </motion.div>

                    {/* Step 2 */}
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.2 }}
                        className="flex flex-col items-center gap-4 group"
                    >
                        <div className="w-16 h-16 rounded-2xl bg-terminal-surface/80 border border-neon-purple/30 flex items-center justify-center text-neon-purple font-bold text-xl relative">
                            2
                            <div className="absolute inset-0 rounded-2xl border border-neon-purple/50 scale-110 opacity-0 group-hover:opacity-100 group-hover:scale-125 transition-all duration-500" />
                        </div>
                        <p className="text-muted-foreground font-mono text-center">
                            {t('step2')}
                        </p>
                    </motion.div>

                    {/* Step 3 */}
                    <motion.div 
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.3 }}
                        className="flex flex-col items-center gap-4 group"
                    >
                        <div className="w-16 h-16 rounded-2xl bg-terminal-surface/80 border border-matrix-green/30 flex items-center justify-center text-matrix-green font-bold text-xl relative">
                            3
                            <div className="absolute inset-0 rounded-2xl border border-matrix-green/50 scale-110 opacity-0 group-hover:opacity-100 group-hover:scale-125 transition-all duration-500" />
                        </div>
                        <p className="text-muted-foreground font-mono text-center">
                            {t('step3')}
                        </p>
                    </motion.div>
                </div>
                
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.5 }}
                    className="mt-16 w-full max-w-2xl bg-black/40 border border-grid-line/30 rounded-lg p-4 flex items-center justify-between text-left"
                >
                    <div className="flex items-center gap-4">
                        <Terminal className="text-neon-cyan" size={24} />
                        <div>
                            <div className="text-xs text-muted-foreground font-mono mb-1">EXECUTE COMMAND</div>
                            <div className="text-matrix-green font-mono text-sm md:text-base">
                                <span className="opacity-50 select-none mr-2">~</span>
                                ./connect.sh --protocol=vless-reality --invisible
                            </div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </section>
    );
}

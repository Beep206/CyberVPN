'use client';

import { useTranslations } from 'next-intl';
import { motion, type Variants } from 'motion/react';
import { Terminal, Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { TiltCard } from '@/shared/ui/tilt-card';
import dynamic from 'next/dynamic';

const FastTrackScene3D = dynamic(() => import('@/3d/scenes/FastTrackScene3D'), { ssr: false });

export function QuickStart() {
    const t = useTranslations('Landing.quick_start');
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText('@CyberVPN_Bot');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const containerVariants: Variants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: { staggerChildren: 0.2 }
        }
    };

    const stepVariants: Variants = {
        hidden: { opacity: 0, y: 30 },
        visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 80 } }
    };

    return (
        <section className="relative py-32 bg-terminal-bg border-t border-grid-line/20 overflow-hidden">
            {/* Dark Matrix Grid Background & FastTrackScene3D */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <FastTrackScene3D />
                <div className="absolute inset-0 bg-grid-white/[0.015] bg-[size:50px_50px]" />
                <div className="absolute inset-0 scanline opacity-30" />
            </div>

            <div className="container mx-auto px-4 relative z-10 max-w-5xl flex flex-col items-center">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="text-center mb-16"
                >
                    <div className="inline-block mb-6 px-4 py-1.5 rounded-full border border-matrix-green/30 bg-matrix-green/10 text-matrix-green text-sm font-mono tracking-widest uppercase">
                        Fast Track
                    </div>
                    <h2 className="text-4xl md:text-6xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-cyan via-matrix-green to-neon-cyan mb-6">
                        {t('title')}
                    </h2>
                </motion.div>

                <motion.div 
                    variants={containerVariants}
                    initial="hidden"
                    whileInView="visible"
                    viewport={{ once: true, margin: '-50px' }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full"
                >
                    {/* Step 1 */}
                    <motion.div variants={stepVariants} className="h-full">
                        <TiltCard className="flex flex-col items-center gap-6 p-8 h-full rounded-2xl group w-full text-center hover:border-neon-cyan/50 transition-colors">
                            <div className="w-20 h-20 rounded-2xl bg-terminal-bg border border-neon-cyan/40 flex items-center justify-center text-neon-cyan font-display font-bold text-3xl shadow-[0_0_15px_rgba(0,255,255,0.2)] group-hover:shadow-[0_0_25px_rgba(0,255,255,0.5)] transition-shadow">
                                1
                            </div>
                            <div className="flex flex-col items-center gap-3 w-full">
                                <p className="text-foreground font-mono text-lg">{t('step1')}</p>
                                <button 
                                    onClick={handleCopy}
                                    className="w-full relative overflow-hidden inline-flex items-center justify-center gap-2 px-4 py-3 bg-neon-cyan/10 border border-neon-cyan/20 text-neon-cyan rounded-lg hover:bg-neon-cyan/20 transition-all font-mono font-semibold"
                                >
                                    @CyberVPN_Bot
                                    {copied ? <Check size={16} /> : <Copy size={16} />}
                                    <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
                                </button>
                            </div>
                        </TiltCard>
                    </motion.div>

                    {/* Step 2 */}
                    <motion.div variants={stepVariants} className="h-full">
                        <TiltCard className="flex flex-col items-center gap-6 p-8 h-full rounded-2xl group w-full text-center hover:border-neon-purple/50 transition-colors">
                            <div className="w-20 h-20 rounded-2xl bg-terminal-bg border border-neon-purple/40 flex items-center justify-center text-neon-purple font-display font-bold text-3xl shadow-[0_0_15px_rgba(157,0,255,0.2)] group-hover:shadow-[0_0_25px_rgba(157,0,255,0.5)] transition-shadow">
                                2
                            </div>
                            <div className="flex flex-col items-center gap-3 w-full justify-center flex-1">
                                <p className="text-foreground font-mono text-lg">{t('step2')}</p>
                            </div>
                        </TiltCard>
                    </motion.div>

                    {/* Step 3 */}
                    <motion.div variants={stepVariants} className="h-full">
                        <TiltCard className="flex flex-col items-center gap-6 p-8 h-full rounded-2xl group w-full text-center hover:border-matrix-green/50 transition-colors">
                            <div className="w-20 h-20 rounded-2xl bg-terminal-bg border border-matrix-green/40 flex items-center justify-center text-matrix-green font-display font-bold text-3xl shadow-[0_0_15px_rgba(0,255,136,0.2)] group-hover:shadow-[0_0_25px_rgba(0,255,136,0.5)] transition-shadow">
                                3
                            </div>
                            <div className="flex flex-col items-center gap-3 w-full justify-center flex-1">
                                <p className="text-foreground font-mono text-lg">{t('step3')}</p>
                            </div>
                        </TiltCard>
                    </motion.div>
                </motion.div>
                
                {/* Terminal Window Detail */}
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-50px' }}
                    transition={{ delay: 0.6 }}
                    className="mt-20 w-full max-w-3xl overflow-hidden rounded-xl border border-grid-line/50 bg-terminal-bg/80 backdrop-blur-xl shadow-2xl relative"
                >
                    {/* Terminal Header */}
                    <div className="flex items-center px-4 py-3 border-b border-grid-line/50 bg-black/40">
                        <div className="flex gap-2">
                            <div className="w-3 h-3 rounded-full bg-red-500/80" />
                            <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                            <div className="w-3 h-3 rounded-full bg-green-500/80" />
                        </div>
                        <div className="mx-auto font-mono text-xs text-muted-foreground uppercase flex items-center gap-2">
                            <Terminal size={12} />
                            Deploy Connection
                        </div>
                    </div>
                    {/* Terminal Body */}
                    <div className="p-6 font-mono text-sm md:text-base leading-relaxed relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-b from-matrix-green/5 to-transparent pointer-events-none" />
                        <div className="text-muted-foreground mb-2"># Auto-provisioning VPN tunnel...</div>
                        <div className="flex items-center text-matrix-green mb-1">
                            <span className="opacity-50 select-none mr-3">sys@admin:~$</span>
                            <span className="typing-animation break-all">curl -sL https://get.cybervpn.com | bash -s -- --protocol=vless-reality</span>
                        </div>
                        <div className="text-neon-cyan mt-4 animate-pulse">
                            {'>'} Tunnel Established. DPI bypassed. Securing transport...
                        </div>
                    </div>
                </motion.div>
            </div>
        </section>
    );
}

'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { Rocket, ShieldCheck } from 'lucide-react';
import { GlobalNetworkWrapper } from './3d-background/global-network-wrapper';
import { ScrambleText } from '@/shared/ui/scramble-text';

export function LandingHero() {
    const t = useTranslations('Landing.hero');

    return (
        <section className="relative min-h-[90vh] flex flex-col items-center justify-center overflow-hidden bg-terminal-bg">
            {/* Background Grid & Scanlines */}
            <div className="absolute inset-0 z-0">
                {/* 3D Global Network Background */}
                <GlobalNetworkWrapper />
                {/* Overlay to ensure text readability */}
                <div className="absolute inset-0 bg-terminal-bg/80 via-terminal-bg/60 to-transparent bg-gradient-to-b" />
            </div>
            {/* Fallback Grid if 3D fails or for texture */}
            <div className="absolute inset-0 z-0 bg-grid-white/[0.02] bg-[size:50px_50px] pointer-events-none" />
            <div className="absolute inset-0 z-0 scanline opacity-20 pointer-events-none" />

            {/* Glow effects */}
            <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-neon-cyan/20 rounded-full blur-[100px] animate-pulse pointer-events-none" />
            <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-neon-purple/20 rounded-full blur-[100px] animate-pulse delay-1000 pointer-events-none" />

            <div className="container relative z-10 flex flex-col items-center text-center px-4">

                {/* Status Badge */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="mb-6 inline-flex items-center gap-2 px-3 py-1 rounded-full border border-matrix-green/30 bg-matrix-green/10 text-matrix-green text-xs font-mono backdrop-blur-md"
                >
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-matrix-green opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-matrix-green"></span>
                    </span>
                    {t('status')}
                </motion.div>

                {/* Main Heading */}
                <motion.h1
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="text-5xl md:text-8xl font-display font-bold tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white to-white/50 mb-6 drop-shadow-lg py-4 leading-normal"
                >
                    <ScrambleText text={t('title')} /> <br />
                    <span className="text-neon-cyan neon-text">{t('titleHighlight')}</span>
                </motion.h1>

                {/* Subtitle */}
                <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                    className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-10 font-mono"
                >
                    {t('subtitle')}
                </motion.p>

                {/* CTA Buttons */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.4 }}
                    className="flex flex-col sm:flex-row gap-4 w-full justify-center"
                >
                    <Button size="lg" className="bg-neon-cyan hover:bg-neon-cyan/80 text-black font-bold tracking-wide shadow-neon-cyan hover:shadow-neon-cyan/50 transition-all h-12 px-8 text-base group" data-hoverable>
                        <Rocket className="mr-2 h-5 w-5 group-hover:-translate-y-1 transition-transform" />
                        {t('ctaPrimary')}
                    </Button>
                    <Button variant="outline" size="lg" className="border-neon-purple text-neon-purple hover:bg-neon-purple/10 font-bold tracking-wide h-12 px-8 text-base backdrop-blur-sm" data-hoverable>
                        <ShieldCheck className="mr-2 h-5 w-5" />
                        {t('ctaSecondary')}
                    </Button>
                </motion.div>
            </div>

            {/* Decorative Footer Element */}
            <div className="absolute bottom-0 w-full h-24 bg-gradient-to-t from-terminal-bg to-transparent z-10 pointer-events-none" />
        </section>
    );
}

'use client';

import { useTranslations } from 'next-intl';
import { motion, useMotionTemplate, useMotionValue } from 'motion/react';
import { Zap, Shield, EyeOff, Globe, Server, Lock } from 'lucide-react';
import { ScrambleText } from '@/shared/ui/scramble-text';

const icons = {
    speed: Zap,
    security: Shield,
    anonymity: EyeOff,
    global: Globe,
    unlimited: Server,
    encryption: Lock
};

import { TiltCard } from '@/shared/ui/tilt-card';

export function LandingFeatures() {
    const t = useTranslations('Landing.features');

    const features = [
        { id: 'speed', icon: icons.speed, color: 'text-neon-cyan', bg: 'bg-neon-cyan/5', colSpan: 'md:col-span-2' },
        { id: 'security', icon: icons.security, color: 'text-neon-purple', bg: 'bg-neon-purple/5', colSpan: 'md:col-span-1' },
        { id: 'anonymity', icon: icons.anonymity, color: 'text-matrix-green', bg: 'bg-matrix-green/5', colSpan: 'md:col-span-1' },
        { id: 'global', icon: icons.global, color: 'text-blue-400', bg: 'bg-blue-400/5', colSpan: 'md:col-span-2' },
    ];

    return (
        <section className="relative py-32 bg-terminal-bg">
            <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:30px_30px] z-0" />

            <div className="container px-4 mx-auto relative z-10">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="text-center mb-20"
                >
                    <h2 className="text-4xl md:text-6xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-cyan to-neon-purple mb-6">
                        {t('title')}
                    </h2>
                    <p className="text-muted-foreground font-mono text-lg max-w-2xl mx-auto">
                        Next-generation feature set designed for the modern cyber-citizen.
                    </p>
                </motion.div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[300px]">
                    {features.map((feature, index) => (
                        <motion.div
                            key={feature.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true }}
                            transition={{ delay: index * 0.1 }}
                            className={`${feature.colSpan}`}
                        >
                            <TiltCard className={`h-full rounded-2xl p-8 flex flex-col justify-between hover:border-neon-cyan/50 transition-colors duration-500`}>
                                <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${feature.bg} ${feature.color} mb-6 border border-foreground/5`}>
                                    <feature.icon className="w-7 h-7" />
                                </div>

                                <div>
                                    <h3 className="text-2xl font-bold font-display mb-3 text-foreground">
                                        <ScrambleText text={t(`${feature.id}.title`)} triggerOnHover />
                                    </h3>
                                    <p className="text-muted-foreground font-mono leading-relaxed">
                                        {t(`${feature.id}.desc`)}
                                    </p>
                                </div>

                                {/* Decorative tech elements */}
                                <div className="absolute top-4 right-4 text-[10px] font-mono text-foreground/20">
                                    SYS.0{index + 1}
                                </div>
                                <div className="absolute bottom-4 right-4 w-12 h-0.5 bg-gradient-to-r from-transparent to-foreground/20" />
                            </TiltCard>
                        </motion.div>
                    ))}
                </div>

                {/* Stat Card / Connect CTA - Placed outside the rigid grid for flexible height */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.4 }}
                    className="w-full mt-6"
                >
                    <TiltCard className="h-auto min-h-[300px] rounded-2xl p-0 overflow-hidden relative group border-neon-cyan/30 bg-gradient-to-br from-terminal-surface/50 to-neon-purple/5">
                        {/* Ambient Glow */}
                        <div className="absolute -right-20 -top-20 w-96 h-96 bg-neon-purple/20 rounded-full blur-[100px] pointer-events-none group-hover:bg-neon-purple/30 transition-all duration-700" />

                        <div className="relative z-10 h-full grid grid-cols-1 md:grid-cols-2 gap-8 p-10 items-center">
                            {/* Left Content */}
                            <div className="flex flex-col items-start space-y-6">
                                <div>
                                    <h3 className="text-3xl md:text-4xl font-bold font-display text-foreground mb-3 leading-tight">
                                        Ready to secure <br />
                                        <span className="text-neon-cyan">your connection?</span>
                                    </h3>
                                    <p className="text-muted-foreground font-mono text-lg max-w-md">
                                        Join thousands of users on the most secure highly-encrypted network available today.
                                    </p>
                                </div>

                                <button className="px-8 py-4 bg-foreground text-background font-bold font-mono rounded hover:bg-neon-cyan hover:text-black transition-all duration-300 shadow-lg shadow-neon-cyan/20 group-hover:shadow-neon-cyan/40" data-hoverable>
                                    <span className="mr-2">INITIALIZE UPLINK_</span>
                                </button>
                            </div>

                            {/* Right Visuals - Holographic Map Composition */}
                            <div className="hidden md:flex items-center justify-center relative h-full min-h-[200px]">
                                <div className="relative w-full h-full flex items-center justify-center">
                                    {/* Spinning rings */}
                                    <div className="absolute w-64 h-64 border border-neon-cyan/20 rounded-full animate-[spin_10s_linear_infinite]" />
                                    <div className="absolute w-48 h-48 border border-neon-purple/20 rounded-full animate-[spin_15s_linear_infinite_reverse]" />
                                    <div className="absolute w-32 h-32 border-2 border-neon-cyan/10 rounded-full animate-pulse" />

                                    {/* Center Icon */}
                                    <Globe className="w-24 h-24 text-neon-cyan opacity-80 drop-shadow-[0_0_15px_rgba(0,255,255,0.5)]" />

                                    {/* Floating nodes */}
                                    <div className="absolute top-10 right-20 w-3 h-3 bg-neon-purple rounded-full animate-ping" />
                                    <div className="absolute bottom-10 left-20 w-2 h-2 bg-neon-cyan rounded-full animate-ping delay-700" />
                                </div>
                            </div>
                        </div>

                        {/* Grid overlay */}
                        <div className="absolute inset-0 z-0 opacity-10 bg-[url('/grid-pattern.svg')] pointer-events-none" />
                    </TiltCard>
                </motion.div>
            </div>
        </section>
    );
}

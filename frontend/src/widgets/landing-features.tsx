'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { Shield, Zap, EyeOff, Globe, Infinity, Layers } from 'lucide-react';
import dynamic from 'next/dynamic';
import { FeatureCard3D } from '@/shared/ui/feature-card-3d';
import { ScrambleText } from '@/shared/ui/scramble-text';

// Dynamically import 3D scene to avoid SSR issues
const FeaturesScene3D = dynamic(
    () => import('@/3d/scenes/FeaturesScene3D').then((mod) => mod.FeaturesScene3D),
    { ssr: false }
);

// Feature configuration with icons and styling
const featureConfig = [
    {
        id: 'shield',
        icon: Shield,
        color: 'text-neon-cyan',
        bgColor: 'bg-neon-cyan/15 dark:bg-neon-cyan/10',
        colSpan: 'md:col-span-2'
    },
    {
        id: 'speed',
        icon: Zap,
        color: 'text-yellow-400',
        bgColor: 'bg-yellow-400/15 dark:bg-yellow-400/10',
        colSpan: 'md:col-span-1'
    },
    {
        id: 'privacy',
        icon: EyeOff,
        color: 'text-neon-purple',
        bgColor: 'bg-neon-purple/15 dark:bg-neon-purple/10',
        colSpan: 'md:col-span-1'
    },
    {
        id: 'global',
        icon: Globe,
        color: 'text-blue-400',
        bgColor: 'bg-blue-400/15 dark:bg-blue-400/10',
        colSpan: 'md:col-span-1'
    },
    {
        id: 'unlimited',
        icon: Infinity,
        color: 'text-matrix-green',
        bgColor: 'bg-matrix-green/15 dark:bg-matrix-green/10',
        colSpan: 'md:col-span-1'
    },
    {
        id: 'protocols',
        icon: Layers,
        color: 'text-neon-pink',
        bgColor: 'bg-neon-pink/15 dark:bg-neon-pink/10',
        colSpan: 'md:col-span-2'
    }
];

// Stats data
const stats = [
    { value: '100+', label: 'locations' },
    { value: '10', label: 'Gbit/s' },
    { value: '99.9%', label: 'uptime' },
    { value: '0', label: 'logs' }
];

export function LandingFeatures() {
    const t = useTranslations('Landing.features');

    // Container animation variants
    const containerVariants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: {
                staggerChildren: 0.1,
                delayChildren: 0.2
            }
        }
    };

    return (
        <section className="relative py-32 bg-terminal-bg overflow-hidden">
            {/* 3D Background Scene */}
            <FeaturesScene3D />

            {/* Grid overlay */}
            <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:30px_30px] z-[1]" />

            {/* Gradient overlays for readability */}
            <div className="absolute inset-0 bg-gradient-to-b from-terminal-bg via-transparent to-terminal-bg z-[2]" />
            <div className="absolute inset-0 bg-terminal-bg/60 z-[2]" />

            <div className="container px-4 mx-auto relative z-10">
                {/* Section Header */}
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                    className="text-center mb-20"
                >
                    {/* Tag */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        whileInView={{ opacity: 1, scale: 1 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 }}
                        className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-neon-cyan/30 bg-neon-cyan/10 text-neon-cyan text-xs font-mono mb-6 backdrop-blur-sm"
                    >
                        <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-pulse" />
                        FEATURE MATRIX
                    </motion.div>

                    {/* Title */}
                    <h2 className="text-4xl md:text-6xl lg:text-7xl font-display font-bold mb-6">
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-neon-cyan via-neon-purple to-neon-pink">
                            {t('sectionTitle')}
                        </span>
                    </h2>

                    {/* Subtitle */}
                    <p className="text-muted-foreground font-mono text-lg md:text-xl max-w-2xl mx-auto">
                        {t('sectionSubtitle')}
                    </p>
                </motion.div>

                {/* Features Grid - Bento Layout */}
                <motion.div
                    variants={containerVariants}
                    initial="hidden"
                    whileInView="visible"
                    viewport={{ once: true, margin: '-100px' }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[280px] mb-16"
                >
                    {featureConfig.map((feature, index) => (
                        <FeatureCard3D
                            key={feature.id}
                            icon={feature.icon}
                            title={t(`${feature.id}.title`)}
                            description={t(`${feature.id}.desc`)}
                            color={feature.color}
                            bgColor={feature.bgColor}
                            index={index}
                            colSpan={feature.colSpan}
                        />
                    ))}
                </motion.div>

                {/* Stats Banner */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.5 }}
                    className="relative rounded-2xl border border-grid-line/40 bg-terminal-surface/60 dark:bg-black/40 backdrop-blur-xl p-8 overflow-hidden"
                >
                    {/* Glow accents */}
                    <div className="absolute -left-20 -top-20 w-40 h-40 bg-neon-cyan/20 rounded-full blur-[80px] pointer-events-none" />
                    <div className="absolute -right-20 -bottom-20 w-40 h-40 bg-neon-purple/20 rounded-full blur-[80px] pointer-events-none" />

                    <div className="relative z-10 grid grid-cols-2 md:grid-cols-4 gap-8">
                        {stats.map((stat, index) => (
                            <motion.div
                                key={stat.label}
                                initial={{ opacity: 0, y: 10 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ delay: 0.6 + index * 0.1 }}
                                className="text-center"
                            >
                                <div className="text-3xl md:text-5xl font-display font-bold text-neon-cyan mb-2">
                                    <ScrambleText text={stat.value} />
                                </div>
                                <div className="text-muted-foreground font-mono text-sm uppercase tracking-wider">
                                    {stat.label}
                                </div>
                            </motion.div>
                        ))}
                    </div>

                    {/* Decorative scan line */}
                    <motion.div
                        className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-neon-cyan to-transparent"
                        initial={{ top: '0%' }}
                        animate={{ top: '100%' }}
                        transition={{
                            duration: 3,
                            repeat: Infinity,
                            ease: 'linear'
                        }}
                    />
                </motion.div>
            </div>
        </section>
    );
}

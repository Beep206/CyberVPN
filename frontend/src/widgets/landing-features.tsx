'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { Zap, Shield, EyeOff } from 'lucide-react';

const icons = {
    speed: Zap,
    security: Shield,
    anonymity: EyeOff
};

export function LandingFeatures() {
    const t = useTranslations('Landing.features');

    const features = [
        { id: 'speed', icon: icons.speed, color: 'text-neon-cyan', shadow: 'shadow-neon-cyan/20' },
        { id: 'security', icon: icons.security, color: 'text-neon-purple', shadow: 'shadow-neon-purple/20' },
        { id: 'anonymity', icon: icons.anonymity, color: 'text-matrix-green', shadow: 'shadow-server-online/20' }
    ];

    return (
        <section className="relative py-24 bg-terminal-surface/30">
            <div className="container px-4 mx-auto">
                <motion.h2
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="text-3xl md:text-5xl font-display font-bold text-center mb-16 text-white"
                >
                    {t('title')}
                </motion.h2>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {features.map((feature, index) => (
                        <motion.div
                            key={feature.id}
                            initial={{ opacity: 0, y: 30 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: index * 0.2 }}
                            className={`group relative p-8 rounded-xl bg-terminal-surface border border-grid-line/20 hover:border-grid-line/50 transition-all hover:-translate-y-2 ${feature.shadow} hover:shadow-xl`}
                        >
                            <div className={`mb-6 p-4 rounded-lg inline-block bg-terminal-bg border border-grid-line/30 ${feature.color}`}>
                                <feature.icon className="w-10 h-10" />
                            </div>

                            <h3 className="text-xl font-bold font-display mb-3 text-foreground group-hover:text-white transition-colors">
                                {t(`${feature.id}.title`)}
                            </h3>

                            <p className="text-muted-foreground font-mono text-sm leading-relaxed">
                                {t(`${feature.id}.desc`)}
                            </p>

                            {/* Corner Accents */}
                            <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-white/20 group-hover:border-neon-cyan transition-colors" />
                            <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-white/20 group-hover:border-neon-cyan transition-colors" />
                        </motion.div>
                    ))}
                </div>
            </div>
        </section>
    );
}

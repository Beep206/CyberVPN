'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { ShieldAlert, Server, CreditCard, LockKeyhole } from 'lucide-react';
import { TiltCard } from '@/shared/ui/tilt-card';

export function HelpCategories() {
    const t = useTranslations('HelpCenter');

    const categories = [
        {
            icon: ShieldAlert,
            titleKey: 'category_getting_started',
            descKey: 'category_getting_started_desc',
            color: 'text-matrix-green',
            glow: 'shadow-matrix-green'
        },
        {
            icon: Server,
            titleKey: 'category_troubleshooting',
            descKey: 'category_troubleshooting_desc',
            color: 'text-neon-cyan',
            glow: 'shadow-neon-cyan'
        },
        {
            icon: CreditCard,
            titleKey: 'category_billing',
            descKey: 'category_billing_desc',
            color: 'text-neon-pink',
            glow: 'shadow-neon-pink'
        },
        {
            icon: LockKeyhole,
            titleKey: 'category_security',
            descKey: 'category_security_desc',
            color: 'text-neon-purple',
            glow: 'shadow-neon-purple'
        }
    ];

    return (
        <section className="relative w-full">
            <div className="flex items-center gap-4 mb-10">
                <div className="h-px bg-terminal-border flex-1" />
                <h2 className="text-2xl font-display font-bold text-foreground tracking-widest uppercase">
                    {t('categories_title')}
                </h2>
                <div className="h-px bg-terminal-border flex-1" />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {categories.map((cat, idx) => {
                    const Icon = cat.icon;
                    return (
                        <motion.div
                            key={idx}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-100px" }}
                            transition={{ duration: 0.5, delay: idx * 0.1 }}
                        >
                            <TiltCard className="h-full cursor-pointer hover:border-terminal-border/80 transition-colors group">
                                <div className="p-6 flex flex-col items-center text-center h-full">
                                    <div className={`p-4 rounded-full bg-terminal-bg border border-terminal-border group-hover:bg-terminal-bg/50 transition-colors mb-6 relative`}>
                                        <div className={`absolute inset-0 blur-md opacity-0 group-hover:opacity-30 transition-opacity bg-current ${cat.color} rounded-full`} />
                                        <Icon className={`w-8 h-8 ${cat.color} relative z-10`} />
                                    </div>
                                    <h3 className="text-xl font-bold font-display mb-3 group-hover:text-neon-cyan transition-colors">
                                        {t(cat.titleKey as any)}
                                    </h3>
                                    <p className="text-sm text-muted-foreground font-mono flex-grow">
                                        {t(cat.descKey as any)}
                                    </p>
                                    
                                    <div className="mt-6 w-full h-1 bg-terminal-bg rounded overflow-hidden">
                                        <div className="h-full bg-gradient-to-r from-transparent via-current to-transparent opacity-0 group-hover:opacity-50 group-hover:animate-pulse transition-opacity w-full" style={{ color: "var(--color-neon-cyan)" }} />
                                    </div>
                                </div>
                            </TiltCard>
                        </motion.div>
                    );
                })}
            </div>
        </section>
    );
}

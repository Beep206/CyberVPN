'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { Database, Laptop, ShieldAlert, WifiHigh } from 'lucide-react';

const SECONDARY_ICONS = [Database, Laptop, ShieldAlert, WifiHigh];

export function SecondaryGrid() {
    const t = useTranslations('Features');

    // Assume we know there are 4 secondary items in the JSON
    const items = [0, 1, 2, 3];

    return (
        <div className="w-full">
            <h2 className="font-display text-2xl font-bold mb-6 text-white flex items-center gap-2">
                <span className="w-2 h-6 bg-matrix-green block" />
                {t('secondary.title')}
            </h2>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {items.map((idx) => {
                    const Icon = SECONDARY_ICONS[idx];
                    
                    return (
                        <motion.div
                            key={idx}
                            initial={{ opacity: 0, y: 10 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true, margin: "-50px" }}
                            transition={{ duration: 0.5, delay: idx * 0.1 }}
                            className="bg-[#080808] border border-grid-line/40 rounded-lg p-5 group hover:border-matrix-green/50 transition-colors"
                        >
                            <div className="flex items-center gap-3 mb-2">
                                <div className="p-2 bg-matrix-green/10 rounded-md text-matrix-green group-hover:bg-matrix-green group-hover:text-black transition-colors">
                                    <Icon className="w-4 h-4" />
                                </div>
                                <h4 className="font-bold text-white font-display text-sm">
                                    {t(`secondary.items.${idx}.title`)}
                                </h4>
                            </div>
                            <p className="text-muted-foreground-low text-xs font-mono leading-relaxed pl-11">
                                {t(`secondary.items.${idx}.desc`)}
                            </p>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}

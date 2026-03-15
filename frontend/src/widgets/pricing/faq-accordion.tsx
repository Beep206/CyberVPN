'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTranslations } from 'next-intl';
import { Plus, Minus, Database } from 'lucide-react';
import { cn } from '@/lib/utils';

export function FAQAccordion() {
    const t = useTranslations('Pricing.faq');
    const [openIndex, setOpenIndex] = useState<number | null>(0);

    const faqs = [
        { q: t('q1'), a: t('a1') },
        { q: t('q2'), a: t('a2') },
        { q: t('q3'), a: t('a3') }
    ];

    return (
        <div className="w-full flex flex-col gap-6">
            <h3 className="text-2xl font-display font-bold tracking-widest text-white uppercase mb-4 flex items-center justify-center gap-4 text-center">
                <Database className="w-6 h-6 text-matrix-green" />
                {t('title')}
            </h3>

            <div className="space-y-4">
                {faqs.map((faq, index) => {
                    const isOpen = openIndex === index;

                    return (
                        <motion.div
                            key={index}
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ delay: index * 0.1 }}
                            className={cn(
                                "border backdrop-blur-xl rounded-xl overflow-hidden transition-colors duration-300",
                                isOpen ? "bg-black/80 border-matrix-green/50 shadow-[0_0_20px_-5px_rgba(0,255,136,0.2)]" : "bg-black/40 border-white/10 hover:border-white/30"
                            )}
                        >
                            <button
                                onClick={() => setOpenIndex(isOpen ? null : index)}
                                className="w-full flex items-center justify-between p-6 text-left"
                            >
                                <span className={cn(
                                    "font-mono text-sm md:text-base tracking-widest uppercase transition-colors",
                                    isOpen ? "text-matrix-green font-bold" : "text-white/80"
                                )}>
                                    {faq.q}
                                </span>
                                <div className={cn(
                                    "flex-shrink-0 ml-4 p-2 rounded-lg border transition-all duration-300",
                                    isOpen ? "bg-matrix-green/10 border-matrix-green text-matrix-green" : "border-white/10 text-white/50"
                                )}>
                                    {isOpen ? <Minus className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
                                </div>
                            </button>

                            <AnimatePresence>
                                {isOpen && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: 'auto', opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        className="overflow-hidden"
                                    >
                                        <div className="p-6 pt-0 font-mono text-sm text-muted-foreground leading-relaxed border-t border-white/5 mt-2">
                                            <span className="text-neon-cyan/50 mr-2">{'>'}</span>{faq.a}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}

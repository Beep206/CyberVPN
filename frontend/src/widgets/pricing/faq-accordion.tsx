'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { useTranslations } from 'next-intl';
import { Database, Minus, Plus } from 'lucide-react';
import { cn } from '@/lib/utils';

export function FAQAccordion() {
  const t = useTranslations('Pricing.faq');
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  const faqs = t.raw('items') as Array<{ q: string; a: string }>;

  return (
    <div className="flex w-full flex-col gap-6">
      <h3 className="mb-4 flex items-center justify-center gap-4 text-center font-display text-2xl font-bold uppercase tracking-widest text-white">
        <Database className="h-6 w-6 text-matrix-green" />
        {t('title')}
      </h3>

      <div className="space-y-4">
        {faqs.map((faq, index) => {
          const isOpen = openIndex === index;

          return (
            <motion.div
              key={faq.q}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.08 }}
              className={cn(
                'overflow-hidden rounded-[1.5rem] border backdrop-blur-xl transition-colors duration-300',
                isOpen
                  ? 'border-matrix-green/45 bg-black/80 shadow-[0_0_24px_-10px_rgba(0,255,136,0.28)]'
                  : 'border-white/10 bg-black/40 hover:border-white/30',
              )}
            >
              <button
                type="button"
                onClick={() => setOpenIndex(isOpen ? null : index)}
                className="flex w-full items-center justify-between p-6 text-left"
              >
                <span
                  className={cn(
                    'font-mono text-sm uppercase tracking-[0.18em] transition-colors md:text-base',
                    isOpen ? 'font-bold text-matrix-green' : 'text-white/80',
                  )}
                >
                  {faq.q}
                </span>
                <div
                  className={cn(
                    'ml-4 shrink-0 rounded-xl border p-2 transition-all duration-300',
                    isOpen
                      ? 'border-matrix-green bg-matrix-green/10 text-matrix-green'
                      : 'border-white/10 text-white/50',
                  )}
                >
                  {isOpen ? <Minus className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
                </div>
              </button>

              <AnimatePresence>
                {isOpen ? (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-2 border-t border-white/5 p-6 pt-0 font-mono text-sm leading-relaxed text-muted-foreground">
                      <span className="mr-2 text-neon-cyan/50">{'>'}</span>
                      {faq.a}
                    </div>
                  </motion.div>
                ) : null}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}

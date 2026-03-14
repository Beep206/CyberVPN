'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { Button } from '@/components/ui/button';
import { Send, TerminalSquare } from 'lucide-react';
import { ScrambleText } from '@/shared/ui/scramble-text';

export function HelpContact() {
    const t = useTranslations('HelpCenter');

    return (
        <section className="relative w-full overflow-hidden border border-neon-purple/30 bg-terminal-card/40 backdrop-blur-sm p-8 md:p-12 mb-20 rounded-xl group hover:border-neon-purple/60 transition-colors">
            {/* Background elements */}
            <div className="absolute inset-0 bg-grid-white/[0.01] bg-[size:30px_30px] pointer-events-none" />
            <div className="absolute right-0 top-0 w-64 h-64 bg-neon-purple/5 blur-[120px] rounded-full pointer-events-none group-hover:bg-neon-purple/10 transition-colors" />

            <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-10">
                <div className="flex-1 text-center md:text-left">
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.5 }}
                    >
                        <h2 className="text-3xl font-display font-bold text-foreground tracking-widest mb-4">
                            <ScrambleText text={t('contact_title')} />
                        </h2>
                        <p className="text-muted-foreground font-mono max-w-xl">
                            {t('contact_desc')}
                        </p>
                    </motion.div>
                </div>

                <div className="flex flex-col sm:flex-row gap-4 w-full md:w-auto">
                    <Button 
                        size="lg" 
                        className="bg-neon-pink/10 hover:bg-neon-pink/20 text-neon-pink border border-neon-pink/50 font-bold tracking-wide transition-all h-14 px-8 group relative overflow-hidden flex-1 sm:flex-none"
                    >
                        <span className="absolute inset-0 bg-neon-pink/10 group-hover:translate-x-full transition-transform duration-500 ease-out" style={{ transformOrigin: 'left' }} />
                        <TerminalSquare className="mr-3 h-5 w-5 relative z-10" />
                        <span className="relative z-10">{t('contact_button_ticket')}</span>
                    </Button>
                    
                    <Button 
                        size="lg" 
                        className="bg-matrix-green hover:bg-matrix-green/80 text-black font-bold tracking-wide shadow-[0_0_15px_rgba(0,255,136,0.3)] hover:shadow-[0_0_25px_rgba(0,255,136,0.5)] transition-all h-14 px-8 group flex-1 sm:flex-none"
                    >
                        <Send className="mr-3 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                        {t('contact_button_telegram')}
                    </Button>
                </div>
            </div>

            {/* Corner decorations */}
            <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-neon-purple/50" />
            <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-neon-purple/50" />
            <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-neon-purple/50" />
            <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-neon-purple/50" />
        </section>
    );
}

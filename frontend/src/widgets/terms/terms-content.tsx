'use client';

import { useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { motion, useInView } from 'framer-motion';
import { type TermsSectionId } from './terms-dashboard';
import { ShieldAlert } from 'lucide-react';

const SECTION_KEYS: TermsSectionId[] = ['acceptance', 'prohibited', 'service', 'liability', 'termination'];

// Custom component for the glitch reveal text effect
function GlitchText({ text, delay = 0 }: { text: string; delay?: number }) {
    const ref = useRef(null);
    const isInView = useInView(ref, { once: true, margin: "-10%" });

    return (
        <span ref={ref} className="relative inline-block overflow-hidden">
            <motion.span
                initial={{ opacity: 0, y: 20, filter: 'blur(10px)', skewX: 40 }}
                animate={isInView ? { 
                    opacity: 1, 
                    y: 0, 
                    filter: 'blur(0px)', 
                    skewX: 0 
                } : {}}
                transition={{ duration: 0.6, delay, type: "spring", bounce: 0.4 }}
                className="inline-block"
            >
                {text}
            </motion.span>
        </span>
    );
}

// Visual widget for prohibited items
function ViolationWidget({ rules }: { rules: Record<string, string> }) {
    return (
        <div className="my-8 rounded-lg border border-red-500/30 bg-red-950/20 p-6 relative overflow-hidden">
            {/* Warning stripe overlay */}
            <div className="absolute inset-0 bg-[url('/warning-stripes.svg')] opacity-5 mix-blend-overlay pointer-events-none" />
            
            <div className="flex items-center gap-3 mb-6 relative z-10">
                <ShieldAlert className="w-8 h-8 text-red-500 animate-pulse" />
                <h3 className="text-xl font-display font-bold text-red-400">RESTRICTED PROTOCOLS</h3>
            </div>

            <ul className="space-y-4 relative z-10">
                {Object.entries(rules).map(([key, desc], idx) => (
                    <motion.li 
                        key={key}
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="flex items-start gap-4"
                    >
                        <div className="mt-1 flex items-center justify-center w-5 h-5 rounded bg-red-500/10 border border-red-500/50">
                            <span className="text-[10px] text-red-400 font-mono">X</span>
                        </div>
                        <span className="font-mono text-sm text-red-200">{desc}</span>
                    </motion.li>
                ))}
            </ul>
        </div>
    );
}

export function TermsContent({ 
    setActiveSection,
    isAccepted 
}: { 
    setActiveSection: (id: TermsSectionId) => void;
    isAccepted: boolean;
}) {
    const t = useTranslations('Terms');
    const containerRef = useRef<HTMLDivElement>(null);

    // Scroll spy logic
    useEffect(() => {
        const handleScroll = () => {
            if (!containerRef.current) return;
            
            const sections = SECTION_KEYS.map(id => document.getElementById(id));
            const scrollPos = containerRef.current.parentElement!.scrollTop + window.innerHeight / 3;

            // Find the last section that we have scrolled past
            for (let i = sections.length - 1; i >= 0; i--) {
                const section = sections[i];
                if (section && section.offsetTop <= scrollPos) {
                    setActiveSection(SECTION_KEYS[i]);
                    break;
                }
            }
        };

        const parent = containerRef.current?.parentElement;
        if (parent) {
            parent.addEventListener('scroll', handleScroll);
            return () => parent.removeEventListener('scroll', handleScroll);
        }
    }, [setActiveSection]);

    // Raw object extraction for the prohibited rules map
    const rulesObj = t.raw('sections.prohibited.rules') as Record<string, string>;

    return (
        <div ref={containerRef} className="max-w-3xl mx-auto px-6 lg:px-12 py-32 space-y-32">
            
            {/* Header intro */}
            <div className="mb-24">
                <h1 className="font-display text-4xl md:text-6xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-white/50 mb-6">
                    {t('title')}
                </h1>
                <p className="font-mono text-warning text-sm tracking-widest border-l-2 border-warning pl-4">
                    {t('description')}
                </p>
            </div>

            {/* Sections Mapping */}
            {SECTION_KEYS.map((id, index) => (
                <section key={id} id={id} className="relative scroll-mt-32">
                    
                    {/* Section Numbering bg */}
                    <div className="absolute -left-8 -top-12 text-[120px] font-display font-black text-white/[0.02] select-none pointer-events-none z-0">
                        0{index + 1}
                    </div>

                    <div className="relative z-10">
                        <h2 className="text-2xl font-display font-bold text-neon-cyan mb-8 border-b border-grid-line/30 pb-4 inline-block">
                            {t(`sections.${id}.title`)}
                        </h2>

                        <div className="font-mono text-muted-foreground leading-relaxed text-sm md:text-base">
                            <GlitchText text={t(`sections.${id}.content`)} />
                        </div>

                        {/* Inject specific widgets for certain sections */}
                        {id === 'prohibited' && rulesObj && (
                            <ViolationWidget rules={rulesObj} />
                        )}
                    </div>
                </section>
            ))}

            {/* Spacer for bottom scrolling padding */}
            <div className="h-64" />
        </div>
    );
}

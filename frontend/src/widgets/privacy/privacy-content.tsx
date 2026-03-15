'use client';

import { useTranslations } from 'next-intl';
import { PrivacySectionId } from './privacy-dashboard';
import { motion, useInView } from 'motion/react';
import { useRef, useEffect, useState } from 'react';
import { DataRadar } from './data-radar';

const SECTIONS: PrivacySectionId[] = [
    'introduction',
    'dataCollection',
    'noLogs',
    'encryption',
    'thirdParties'
];

export function PrivacyContent({ setActiveSection }: { setActiveSection: (id: PrivacySectionId) => void }) {
    return (
        <div className="relative w-full min-h-full py-24 md:py-32 px-6 md:px-12 max-w-4xl mx-auto flex flex-col gap-32">
            
            {/* Ambient Top Glow */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[80%] h-32 bg-neon-cyan/5 blur-[100px] pointer-events-none" />

            {SECTIONS.map((sectionId, i) => (
                <PrivacySection 
                    key={sectionId} 
                    sectionId={sectionId} 
                    index={i} 
                    onInView={() => setActiveSection(sectionId)} 
                />
            ))}
            
            {/* Extra padding to allow the last item to scroll to top */}
            <div className="h-[50vh]" />
        </div>
    );
}

function PrivacySection({ 
    sectionId, 
    index, 
    onInView 
}: { 
    sectionId: PrivacySectionId; 
    index: number; 
    onInView: () => void;
}) {
    const t = useTranslations('Privacy');
    const ref = useRef<HTMLDivElement>(null);
    const isInView = useInView(ref, { margin: "-20% 0px -60% 0px" });
    const isVisible = useInView(ref, { once: true, margin: "0px 0px -100px 0px" });

    useEffect(() => {
        if (isInView) {
            onInView();
        }
    }, [isInView, onInView]);

    return (
        <div 
            id={`section-${sectionId}`} 
            ref={ref}
            className="w-full flex flex-col gap-6 relative"
        >
            {/* Section Index Badge */}
            <motion.div 
                initial={{ opacity: 0, x: -20 }}
                animate={isVisible ? { opacity: 1, x: 0 } : { opacity: 0, x: -20 }}
                transition={{ duration: 0.5, delay: 0.1 }}
                className="flex items-center gap-4"
            >
                <div className="text-xs px-2 py-1 bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 rounded-sm font-bold tracking-widest uppercase">
                    SEC_{String(index + 1).padStart(2, '0')}
                </div>
                <div className="h-px bg-grid-line/50 flex-1" />
            </motion.div>

            {/* Section Title */}
            <motion.h2 
                initial={{ opacity: 0, y: 20 }}
                animate={isVisible ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
                transition={{ duration: 0.5, delay: 0.2 }}
                className="text-2xl md:text-3xl lg:text-4xl font-black text-white uppercase tracking-wider"
            >
                <DecryptionText text={t(`sections.${sectionId}.title`)} trigger={isVisible} />
            </motion.h2>

            {/* Section Content Block */}
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={isVisible ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
                transition={{ duration: 0.7, delay: 0.3 }}
                className="relative p-6 md:p-8 bg-black/40 backdrop-blur-md border border-grid-line/50 rounded-sm"
            >
                {/* Visual Corner Markers */}
                <div className="absolute top-0 left-0 w-2 h-2 border-t border-l border-neon-cyan/50" />
                <div className="absolute top-0 right-0 w-2 h-2 border-t border-r border-neon-cyan/50" />
                <div className="absolute bottom-0 left-0 w-2 h-2 border-b border-l border-neon-cyan/50" />
                <div className="absolute bottom-0 right-0 w-2 h-2 border-b border-r border-neon-cyan/50" />

                <div className="text-terminal-text text-base md:text-lg leading-relaxed mix-blend-screen">
                    <DecryptionText 
                        text={t(`sections.${sectionId}.content`)} 
                        trigger={isVisible} 
                        speed={30} 
                        scrambleChars="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()" 
                    />
                </div>

                {/* Specific Visual Widgets per Section */}
                {sectionId === 'dataCollection' && isVisible && (
                    <div className="mt-8">
                        <DataRadar />
                    </div>
                )}
            </motion.div>
        </div>
    );
}

// --- The Core "Decryption" Text Effect ---
function DecryptionText({ 
    text, 
    trigger, 
    speed = 50,
    scrambleChars = '01ABCDEFGHIJKLMNOPQRSTUVWXYZ' 
}: { 
    text: string; 
    trigger: boolean;
    speed?: number;
    scrambleChars?: string;
}) {
    const [displayText, setDisplayText] = useState('');
    
    useEffect(() => {
        if (!trigger) {
            setDisplayText('');
            return;
        }

        let iteration = 0;
        let interval: NodeJS.Timeout;
        
        const length = text.length;

        interval = setInterval(() => {
            setDisplayText(
                text.split('')
                    .map((letter, index) => {
                        if (index < iteration) {
                            return text[index];
                        }
                        if (letter === ' ') return ' ';
                        return scrambleChars[Math.floor(Math.random() * scrambleChars.length)];
                    })
                    .join('')
            );

            // Speed formula: decypts faster towards the end
            if (iteration >= length) {
                clearInterval(interval);
            }
            
            iteration += 1 / (length / 20); // Scale iterations based on text length
        }, speed);

        return () => clearInterval(interval);
    }, [text, trigger, speed, scrambleChars]);

    return <span>{displayText}</span>;
}

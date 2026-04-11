'use client';

import { useTranslations } from 'next-intl';
import { Fingerprint } from 'lucide-react';
import { ClassifiedText } from '@/shared/ui/atoms/classified-text';

// A wrapper to auto-parse [TEXT] tags from translation strings into ClassifiedText blocks
function parseClassifiedString(str: string) {
    const parts = str.split(/(\[.*?\])/g);
    
    return parts.map((part, index) => {
        if (part.startsWith('[') && part.endsWith(']')) {
            const innerText = part.slice(1, -1);
            return <ClassifiedText key={index} text={innerText} />;
        }
        return <span key={index}>{part}</span>;
    });
}

export function ClassifiedContent() {
    const t = useTranslations('Security.classified');

    return (
        <div className="w-full flex flex-col gap-8 relative">
            
            {/* Top secret watermark */}
            <div className="absolute -left-12 -top-12 opacity-5 pointer-events-none rotate-[-15deg]">
                <span className="font-display font-black text-8xl whitespace-nowrap text-red-500 border-8 border-red-500 p-4">
                    TOP SECRET
                </span>
            </div>

            <div className="flex items-center gap-4 border-b border-grid-line/50 pb-6 relative z-10">
                <div className="w-12 h-12 rounded-full border border-red-500/50 bg-red-500/10 flex items-center justify-center">
                    <Fingerprint className="w-6 h-6 text-red-500" />
                </div>
                <div>
                    <h2 className="text-2xl font-display font-medium text-white tracking-widest">{t('title')}</h2>
                    <p className="font-mono text-xs text-red-400 mt-1 uppercase">Clearance Level: Omega</p>
                </div>
            </div>

            <div className="space-y-6 font-mono text-muted-foreground leading-relaxed relative z-10 text-sm">
                <p>{parseClassifiedString(t('text1'))}</p>
                <div className="h-px w-full bg-grid-line/30 my-4" />
                <p>{parseClassifiedString(t('text2'))}</p>
            </div>
            
            <div className="mt-8 p-4 border border-neon-cyan/20 bg-neon-cyan/5 rounded flex items-start gap-4">
                <span className="animate-pulse text-neon-cyan font-mono font-bold">»</span>
                <p className="font-mono text-xs text-neon-cyan/80">
                    Hover mouse sequence over redacted blocks to initiate ocular decryption subroutines.
                </p>
            </div>

        </div>
    );
}

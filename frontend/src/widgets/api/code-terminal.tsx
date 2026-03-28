'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { ActiveEndpoint } from './api-dashboard';
import { Copy, Check, TerminalSquare } from 'lucide-react';
import { cn } from '@/lib/utils';

// Helper component for the typing effect
function TypewriterText({ text, speed = 15, onComplete }: { text: string, speed?: number, onComplete?: () => void }) {
    const [displayedText, setDisplayedText] = useState('');

    useEffect(() => {
        setDisplayedText(''); // Reset on text change
        let i = 0;
        const timer = setInterval(() => {
            if (i < text.length) {
                setDisplayedText(text.substring(0, i + 1));
                i++;
            } else {
                clearInterval(timer);
                if (onComplete) onComplete();
            }
        }, speed);

        return () => clearInterval(timer);
    }, [text, speed, onComplete]);

    return <span>{displayedText}</span>;
}

interface CodeTerminalProps {
    activeEndpoint: ActiveEndpoint;
}

export function CodeTerminal({ activeEndpoint }: CodeTerminalProps) {
    const t = useTranslations('Api');
    const [copiedContent, setCopiedContent] = useState<'request' | 'response' | null>(null);
    const [typingCompleted, setTypingCompleted] = useState<{ requestEndpointId: string | null }>({
        requestEndpointId: null,
    });

    const reqData = t.raw(`endpoints.${activeEndpoint.category}.items.${activeEndpoint.id}.request`);
    const resData = t.raw(`endpoints.${activeEndpoint.category}.items.${activeEndpoint.id}.response`);

    const requestCompleted = typingCompleted.requestEndpointId === activeEndpoint.id;

    const handleCopy = (content: string, type: 'request' | 'response') => {
        navigator.clipboard.writeText(content);
        setCopiedContent(type);
        setTimeout(() => setCopiedContent(null), 2000);
    };

    return (
        <div className="w-full flex w-full flex-col h-full bg-terminal-bg/80 border border-grid-line/50 rounded-xl overflow-hidden shadow-2xl relative">
            
            {/* Terminal Header */}
            <div className="h-10 bg-matrix-green/10 border-b border-grid-line/50 flex items-center justify-between px-4 shrink-0">
                <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500/50" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                    <div className="w-3 h-3 rounded-full bg-matrix-green/50" />
                </div>
                <div className="font-mono text-[10px] text-muted-foreground uppercase flex items-center gap-2">
                    <TerminalSquare className="w-3 h-3" />
                    CYBERVPN_BASH_V2.4
                </div>
            </div>

            <div className="flex-1 overflow-y-auto no-scrollbar p-6 flex flex-col gap-8 relative">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={`req-${activeEndpoint.id}`}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0, transition: { duration: 0.1 } }}
                    >
                        {/* Request Block */}
                        <div className="flex flex-col gap-3 relative group">
                            <div className="flex items-center justify-between">
                                <span className="font-mono text-xs font-bold text-neon-cyan uppercase tracking-widest">
                                    {t('labels.request')}
                                </span>
                                <button 
                                    onClick={() => handleCopy(reqData, 'request')}
                                    className="p-1.5 rounded bg-terminal-bg hover:bg-neon-cyan/20 border border-grid-line/50 hover:border-neon-cyan/50 text-muted-foreground hover:text-neon-cyan transition-colors"
                                    aria-label="Copy request code"
                                >
                                    {copiedContent === 'request' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                                </button>
                            </div>
                            
                            <div className="p-4 rounded-md bg-black/60 border border-grid-line/30 font-mono text-sm leading-relaxed overflow-x-auto whitespace-pre">
                                <span className="text-matrix-green select-none">$ </span>
                                <span className="text-gray-300">
                                    <TypewriterText 
                                        text={reqData} 
                                        speed={5} 
                                        onComplete={() => setTypingCompleted({ requestEndpointId: activeEndpoint.id })} 
                                    />
                                </span>
                            </div>
                        </div>

                        {/* Visual separator (fake loading line between req and res) */}
                        <div className="my-6 w-full h-[1px] bg-grid-line/20 relative">
                            {requestCompleted && (
                                <motion.div 
                                    className="absolute left-0 top-0 h-full w-1/4 bg-neon-cyan"
                                    initial={{ x: "-100%" }}
                                    animate={{ x: "400%" }}
                                    transition={{ duration: 1, ease: "easeInOut" }}
                                />
                            )}
                        </div>

                        {/* Response Block */}
                        <div className="flex flex-col gap-3 relative group">
                            <div className="flex items-center justify-between">
                                <span className={cn(
                                    "font-mono text-xs font-bold uppercase tracking-widest transition-colors duration-500",
                                    requestCompleted ? "text-neon-purple" : "text-muted-foreground"
                                )}>
                                    {t('labels.response')}
                                </span>
                                <button 
                                    onClick={() => handleCopy(resData, 'response')}
                                    disabled={!requestCompleted}
                                    className="p-1.5 rounded bg-terminal-bg hover:bg-neon-purple/20 border border-grid-line/50 hover:border-neon-purple/50 text-muted-foreground hover:text-neon-purple transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    aria-label="Copy response JSON"
                                >
                                    {copiedContent === 'response' ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                                </button>
                            </div>
                            
                            <div className="p-4 rounded-md bg-[#020205] border border-grid-line/30 font-mono text-sm leading-relaxed overflow-x-auto whitespace-pre relative group-hover:border-neon-purple/30 transition-colors">
                                {/* Only start typing the response after the request is done typing */}
                                {requestCompleted ? (
                                    <span className="text-gray-400">
                                        <TypewriterText text={resData} speed={2} />
                                    </span>
                                ) : (
                                    <span className="text-gray-600">Waiting for request execution...</span>
                                )}
                            </div>
                        </div>
                    </motion.div>
                </AnimatePresence>
            </div>
            
            {/* Static Scanline Overlay for the CRT effect */}
            <div className="absolute inset-0 pointer-events-none bg-[url('/scanline.png')] bg-repeat opacity-[0.03]" />
        </div>
    );
}

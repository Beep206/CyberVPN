'use client';

import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from 'motion/react';
import { OSPlatform } from './download-dashboard';
import { ChevronRight, FileCode2 } from 'lucide-react';
import { useState } from 'react';

interface ChangelogAccordionProps {
    selectedOS: OSPlatform;
}

// Mock changelog data depending on OS
const getChangelog = (os: OSPlatform) => {
    if (os === 'none') return [];
    
    // Generating some fake but plausible patch notes
    const notes = [
        { version: 'v2.4.1', date: '2026-03-10', changes: ['Upgraded neural tunnel routing.', 'Fixed memory leak in background worker.', 'Updated UI icons for high-DPI.'] },
        { version: 'v2.4.0', date: '2026-02-28', changes: ['Implemented AES-256-GCM hardware acceleration.', `Optimized ${os.toUpperCase()} kernel integration.`, 'Added split-tunneling per application.'] }
    ];
    return notes;
};

export function ChangelogAccordion({ selectedOS }: ChangelogAccordionProps) {
    const t = useTranslations('Download.changelog');
    const logs = getChangelog(selectedOS);
    const [expandedIndex, setExpandedIndex] = useState<number | null>(0);

    if (selectedOS === 'none') {
        return (
            <div className="p-6 border border-white/10 bg-black/40 backdrop-blur-md rounded-xl font-mono text-xs text-white/30 text-center uppercase tracking-widest">
                Select target OS to view directives
            </div>
        );
    }

    return (
        <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="border border-white/10 bg-black/60 backdrop-blur-xl rounded-xl overflow-hidden"
        >
            <div className="p-4 border-b border-white/5 bg-white/[0.02] flex items-center gap-2">
                <FileCode2 className="w-4 h-4 text-neon-purple" />
                <h3 className="font-mono text-xs text-white uppercase tracking-widest">{t('title')} // {selectedOS}</h3>
            </div>
            
            <div className="divide-y divide-white/5">
                {logs.length > 0 ? logs.map((log, i) => (
                    <div key={i} className="group">
                        <button 
                            onClick={() => setExpandedIndex(expandedIndex === i ? null : i)}
                            className="w-full flex items-center justify-between p-4 text-left hover:bg-white/[0.02] transition-colors"
                        >
                            <div className="flex items-center gap-4">
                                <span className="font-mono text-sm text-white font-bold">{log.version}</span>
                                <span className="font-mono text-[10px] text-white/40">{log.date}</span>
                            </div>
                            <ChevronRight className={`w-4 h-4 text-white/30 transition-transform ${expandedIndex === i ? 'rotate-90 text-neon-cyan' : ''}`} />
                        </button>
                        
                        <AnimatePresence>
                            {expandedIndex === i && (
                                <motion.div 
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{ height: 'auto', opacity: 1 }}
                                    exit={{ height: 0, opacity: 0 }}
                                    className="overflow-hidden"
                                >
                                    <div className="p-4 pt-0 pl-16 font-mono text-xs text-white/60 space-y-2">
                                        {log.changes.map((change, j) => (
                                            <div key={j} className="flex gap-2">
                                                <span className="text-neon-cyan/50">-</span>
                                                <span>{change}</span>
                                            </div>
                                        ))}
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                )) : (
                    <div className="p-6 font-mono text-xs text-white/30 text-center italic">
                        {t('empty')}
                    </div>
                )}
            </div>
        </motion.div>
    );
}

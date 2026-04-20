'use client';

import { useTranslations } from 'next-intl';
import { ActiveEndpoint } from './api-dashboard';
import { motion, AnimatePresence } from 'motion/react';
import { Shield } from 'lucide-react';

interface EndpointDetailsProps {
    activeEndpoint: ActiveEndpoint;
}

export function EndpointDetails({ activeEndpoint }: EndpointDetailsProps) {
    const t = useTranslations('Api');
    
    // We map the raw JSON data to a structure we can map over
    // Since 'params' is an array of objects in our JSON, we read it using next-intl raw features
    // If raw array doesn't work, we fallback to a safe approach. Next-intl supports `.raw()` for arrays.
    
    // Construct the translation path key prefix
    const tPrefix = `endpoints.${activeEndpoint.category}.items.${activeEndpoint.id}`;

    // Cast the params to the expected typescript structure.
    // In next-intl, arrays of objects can be fetched with t.raw("path")
    const params = t.raw(`${tPrefix}.params`) as Array<{ name: string; type: string; req: boolean; desc: string }>;

    return (
        <AnimatePresence mode="wait">
            <motion.div 
                key={activeEndpoint.id} // Re-animate when endpoint changes
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.4 }}
                className="flex flex-col gap-8 text-white w-full max-w-2xl"
            >
                <div>
                    <h2 className="font-display text-4xl font-black uppercase tracking-tighter shadow-black drop-shadow-lg mb-2">
                        {t(`${tPrefix}.title`)}
                    </h2>
                    <p className="font-mono text-muted-foreground text-sm leading-relaxed">
                        {t(`${tPrefix}.description`)}
                    </p>
                </div>

                <div className="bg-terminal-bg/80 border border-grid-line/50 p-6 rounded-lg relative overflow-hidden group">
                    <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-matrix-green/50 to-transparent" />
                    
                    <h3 className="font-mono text-xs font-bold text-matrix-green mb-4 uppercase tracking-widest flex items-center gap-2">
                        <Shield className="w-3 h-3" />
                        {t('labels.parameters')}
                    </h3>

                    {params && params.length > 0 ? (
                        <div className="flex flex-col gap-4">
                            {params.map((param, i) => (
                                <div key={i} className="flex flex-col sm:flex-row sm:items-baseline gap-2 border-b border-grid-line/30 pb-4 last:pb-0 last:border-0">
                                    <div className="flex items-center gap-3 sm:w-1/3 shrink-0">
                                        <code className="font-mono text-sm text-neon-cyan bg-neon-cyan/10 px-1.5 py-0.5 rounded">
                                            {param.name}
                                        </code>
                                        {param.req ? (
                                            <span className="font-mono text-[10px] text-red-500 uppercase tracking-wider bg-red-500/10 px-1 rounded-sm">Req</span>
                                        ) : (
                                            <span className="font-mono text-[10px] text-muted-foreground uppercase tracking-wider bg-terminal-bg px-1 rounded-sm">Opt</span>
                                        )}
                                    </div>
                                    <div className="flex flex-col gap-1 sm:w-2/3">
                                        <span className="font-mono text-xs text-neon-purple uppercase">
                                            {param.type}
                                        </span>
                                        <span className="font-mono text-sm text-muted-foreground">
                                            {param.desc}
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="font-mono text-sm text-muted-foreground italic">No parameters required.</p>
                    )}
                </div>

                {/* Requirements / Auth note */}
                <div className="p-4 border border-neon-cyan/20 bg-neon-cyan/5 rounded-lg flex items-start gap-3">
                    <div className="text-neon-cyan mt-0.5">ⓘ</div>
                    <div className="font-mono text-sm text-muted-foreground">
                        <strong className="text-white font-normal uppercase tracking-wide">Authorization:</strong> Bearer Token required for this request. Passed via <code className="text-neon-cyan">Authorization</code> header.
                    </div>
                </div>

            </motion.div>
        </AnimatePresence>
    );
}

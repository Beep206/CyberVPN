'use client';

import { useTranslations } from 'next-intl';
import { Network, Activity, ShieldAlert, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { CypherText } from '@/shared/ui/atoms/cypher-text';

type ProtocolRow = {
    key: string;
    isFeatured?: boolean;
};

const PROTOCOLS: ProtocolRow[] = [
    { key: 'wireguard' },
    { key: 'openvpn' },
    { key: 'stealth', isFeatured: true }
];

export function ProtocolGrid() {
    const t = useTranslations('Security.protocols');

    // Type coercion since next-intl returns arrays as objects in some configurations,
    // or we can safely assume it's an array based on our JSON structure.
    const headers = t.raw('headers') as string[];

    return (
        <div className="w-full flex justify-center lg:justify-end">
            <div className="w-full max-w-lg bg-black/40 border border-grid-line/50 rounded-xl overflow-hidden backdrop-blur-md">
                
                {/* Header */}
                <div className="bg-terminal-bg/80 border-b border-grid-line/50 p-6 flex flex-col gap-2 relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-4 opacity-5">
                        <Network className="w-24 h-24" />
                    </div>
                    <h3 className="text-xl font-display font-bold text-white relative z-10 flex items-center gap-2">
                        <Activity className="w-5 h-5 text-neon-cyan" />
                        <CypherText text={t('title')} loop loopDelay={8000} />
                    </h3>
                </div>

                {/* Table Data */}
                <div className="p-6 overflow-x-auto">
                    <table className="w-full text-left font-mono text-sm border-collapse">
                        <thead>
                            <tr className="border-b border-grid-line/30">
                                {headers.map((h, i) => (
                                    <th key={i} className="pb-4 font-normal text-muted-foreground uppercase text-xs tracking-wider">
                                        {h}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {PROTOCOLS.map((protocol, rowIdx) => {
                                const rowData = t.raw(protocol.key) as string[];

                                return (
                                    <tr 
                                        key={protocol.key} 
                                        className={cn(
                                            "border-b border-grid-line/10 hover:bg-white/5 transition-colors",
                                            protocol.isFeatured ? "bg-neon-cyan/5" : ""
                                        )}
                                    >
                                        {rowData.map((data, colIdx) => (
                                            <td key={colIdx} className={cn(
                                                "py-4 pr-4 align-middle",
                                                colIdx === 0 && "font-bold text-white flex items-center gap-2",
                                                protocol.isFeatured && colIdx > 0 ? "text-neon-cyan" : "text-muted-foreground"
                                            )}>
                                                {/* Add icon to the first column if it's the featured protocol */}
                                                {colIdx === 0 && protocol.isFeatured && (
                                                    <Check className="w-4 h-4 text-neon-cyan" />
                                                )}
                                                
                                                {/* Add a warning icon for "Low" DPI bypass to emphasize stealth */}
                                                {colIdx === 3 && data.includes('Low') && (
                                                    <ShieldAlert className="w-3 h-3 text-warning inline mr-1" />
                                                )}
                                                
                                                {data}
                                            </td>
                                        ))}
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>

            </div>
        </div>
    );
}

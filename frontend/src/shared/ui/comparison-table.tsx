import * as React from 'react';

export interface ComparisonTableRow {
    id: string;
    feature: string;
    legacy: string;
    cybervpn: string;
}

export interface ComparisonTableProps {
    title?: string;
    headers: {
        feature: string;
        legacy: string;
        cybervpn: string;
    };
    rows: ComparisonTableRow[];
    className?: string;
}

export function ComparisonTable({ title, headers, rows, className = '' }: ComparisonTableProps) {
    return (
        <div className={`w-full overflow-hidden cyber-card rounded-xl p-6 ${className}`}>
            {title && (
                <h3 className="text-2xl font-display text-center text-neon-cyan mb-8 uppercase tracking-wider">
                    {title}
                </h3>
            )}
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="border-b border-grid-line/50 text-muted-foreground uppercase text-sm font-mono tracking-wider">
                            <th className="py-4 px-4 font-semibold">{headers.feature}</th>
                            <th className="py-4 px-4 font-semibold text-muted-foreground/80">{headers.legacy}</th>
                            <th className="py-4 px-4 font-semibold text-[color:var(--color-matrix-green)] neon-text drop-shadow-[0_0_8px_rgba(0,255,136,0.5)]">
                                {headers.cybervpn}
                            </th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-grid-line/30 font-mono text-sm">
                        {rows.map((row) => (
                            <tr key={row.id} className="hover:bg-grid-line/10 transition-colors">
                                <td className="py-4 px-4 text-foreground/90 font-medium">
                                    {row.feature}
                                </td>
                                <td className="py-4 px-4 text-muted-foreground">
                                    {row.legacy}
                                </td>
                                <td className="py-4 px-4 text-[color:var(--color-matrix-green)] font-semibold bg-[color:var(--color-matrix-green)]/5 rounded-sm">
                                    {row.cybervpn}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

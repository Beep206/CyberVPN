'use client';

import * as React from 'react';
import { motion, type Variants } from 'motion/react';

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
    const tableVariants: Variants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: { staggerChildren: 0.1 }
        }
    };

    const rowVariants: Variants = {
        hidden: { opacity: 0, x: -20 },
        visible: { opacity: 1, x: 0, transition: { type: 'spring', stiffness: 100 } }
    };

    return (
        <div className={`w-full overflow-hidden cyber-card rounded-xl p-6 relative group ${className}`}>
            {/* Hover glow effect for the table container */}
            <div className="absolute inset-0 bg-gradient-to-br from-neon-cyan/0 via-neon-cyan/5 to-neon-purple/0 opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />

            {title && (
                <h3 className="text-2xl font-display text-center text-neon-cyan mb-8 uppercase tracking-wider relative z-10">
                    <span className="inline-block relative">
                        {title}
                        <span className="absolute -bottom-2 left-0 w-full h-px bg-gradient-to-r from-transparent via-neon-cyan/50 to-transparent" />
                    </span>
                </h3>
            )}
            <div className="overflow-x-auto relative z-10">
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
                    <motion.tbody 
                        variants={tableVariants}
                        initial="hidden"
                        whileInView="visible"
                        viewport={{ once: true, margin: '-50px' }}
                        className="divide-y divide-grid-line/30 font-mono text-sm"
                    >
                        {rows.map((row) => (
                            <motion.tr variants={rowVariants} key={row.id} className="hover:bg-grid-line/10 transition-colors">
                                <td className="py-4 px-4 text-foreground/90 font-medium whitespace-nowrap">
                                    {row.feature}
                                </td>
                                <td className="py-4 px-4 text-muted-foreground">
                                    {row.legacy}
                                </td>
                                <td className="py-4 px-4 text-[color:var(--color-matrix-green)] font-semibold bg-[color:var(--color-matrix-green)]/5 rounded-sm">
                                    <div className="flex items-center gap-2">
                                        <div className="w-1.5 h-1.5 rounded-full bg-[color:var(--color-matrix-green)] shadow-[0_0_8px_var(--color-matrix-green)] animate-pulse" />
                                        {row.cybervpn}
                                    </div>
                                </td>
                            </motion.tr>
                        ))}
                    </motion.tbody>
                </table>
            </div>
        </div>
    );
}

'use client';

import * as React from 'react';
import { motion, type Variants } from 'motion/react';
import { ScrambleText } from './scramble-text';
import { TiltCard } from './tilt-card';

export interface TechDataItem {
    id: string;
    label: string;
    value: string;
    scramble?: boolean;
}

export interface TechDataGridProps {
    title?: string;
    items: TechDataItem[];
    className?: string;
    columns?: 1 | 2 | 3 | 4;
}

export function TechDataGrid({ title, items, className = '', columns = 3 }: TechDataGridProps) {
    const gridCols = {
        1: 'grid-cols-1',
        2: 'grid-cols-1 md:grid-cols-2',
        3: 'grid-cols-1 md:grid-cols-3',
        4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
    };

    const containerVariants: Variants = {
        hidden: { opacity: 0 },
        visible: {
            opacity: 1,
            transition: { staggerChildren: 0.1 }
        }
    };

    const itemVariants: Variants = {
        hidden: { opacity: 0, y: 20 },
        visible: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 100 } }
    };

    return (
        <motion.div 
            variants={containerVariants}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-50px' }}
            className={`w-full ${className}`}
        >
            {title && (
                <motion.h4 
                    variants={itemVariants} 
                    className="text-sm font-mono text-muted-foreground uppercase tracking-widest mb-4 border-b border-grid-line/30 pb-2 relative"
                >
                    {title}
                    <div className="absolute bottom-0 left-0 w-1/3 h-px bg-neon-cyan/50 shadow-[0_0_8px_rgba(0,255,255,0.5)]" />
                </motion.h4>
            )}
            <div className={`grid gap-4 ${gridCols[columns]}`}>
                {items.map((item) => (
                    <motion.div variants={itemVariants} key={item.id} className="h-full">
                        <TiltCard className="flex flex-col gap-2 p-5 rounded-lg h-full border-grid-line/20 bg-terminal-surface/30">
                            <span className="text-xs font-mono text-muted-foreground/70 uppercase flex items-center gap-2">
                                <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full" />
                                {item.label}
                            </span>
                            <span className="text-sm md:text-base font-mono text-neon-cyan/90 break-words drop-shadow-[0_0_5px_rgba(0,255,255,0.3)]">
                                {item.scramble ? (
                                    <ScrambleText text={item.value} triggerOnHover />
                                ) : (
                                    item.value
                                )}
                            </span>
                        </TiltCard>
                    </motion.div>
                ))}
            </div>
        </motion.div>
    );
}

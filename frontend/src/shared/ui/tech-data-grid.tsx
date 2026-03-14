import * as React from 'react';
import { ScrambleText } from './scramble-text';

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

    return (
        <div className={`w-full ${className}`}>
            {title && (
                <h4 className="text-sm font-mono text-muted-foreground uppercase tracking-widest mb-4 border-b border-grid-line/30 pb-2">
                    {title}
                </h4>
            )}
            <div className={`grid gap-4 ${gridCols[columns]}`}>
                {items.map((item) => (
                    <div 
                        key={item.id} 
                        className="flex flex-col gap-1 p-4 border border-grid-line/20 bg-terminal-surface/30 rounded-md backdrop-blur-sm"
                    >
                        <span className="text-xs font-mono text-muted-foreground/70 uppercase">
                            {item.label}
                        </span>
                        <span className="text-sm md:text-base font-mono text-neon-cyan/90 break-words">
                            {item.scramble ? (
                                <ScrambleText text={item.value} />
                            ) : (
                                item.value
                            )}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

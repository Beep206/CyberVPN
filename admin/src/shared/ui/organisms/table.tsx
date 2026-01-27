import { cn } from "@/lib/utils";
import React from "react";
import { CypherText } from "@/shared/ui/atoms/cypher-text";

const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(({ className, ...props }, ref) => (
    <div className="relative w-full overflow-auto rounded-lg border border-grid-line/30 bg-terminal-surface/50 backdrop-blur">
        <table
            ref={ref}
            className={cn("w-full caption-bottom text-sm", className)}
            {...props}
        />
    </div>
));
Table.displayName = "Table";

const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(({ className, ...props }, ref) => (
    <thead ref={ref} className={cn("[&_tr]:border-b", className)} {...props} />
));
TableHeader.displayName = "TableHeader";

const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(({ className, ...props }, ref) => (
    <tbody
        ref={ref}
        className={cn("[&_tr:last-child]:border-0", className)}
        {...props}
    />
));
TableBody.displayName = "TableBody";

const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(({ className, ...props }, ref) => (
    <tr
        ref={ref}
        className={cn(
            "border-b border-grid-line/30 relative transition-all duration-200",
            "hover:bg-neon-cyan/5 hover:translate-x-1 hover:border-l-2 hover:border-l-neon-cyan",
            "hover:shadow-[inset_0_0_20px_rgba(0,255,255,0.05)]",
            className
        )}
        {...props}
    />
));
TableRow.displayName = "TableRow";

const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(({ className, children, ...props }, ref) => (
    <th
        ref={ref}
        className={cn(
            "h-12 px-4 text-left align-middle font-display text-xs text-neon-cyan uppercase tracking-wider",
            className
        )}
        {...props}
    >
        {typeof children === 'string' ? <CypherText text={children} speed={20} revealSpeed={50} /> : children}
    </th>
));
TableHead.displayName = "TableHead";

const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(({ className, ...props }, ref) => (
    <td
        ref={ref}
        className={cn("p-4 align-middle font-mono text-foreground", className)}
        {...props}
    />
));
TableCell.displayName = "TableCell";

export {
    Table,
    TableHeader,
    TableBody,
    TableHead,
    TableRow,
    TableCell,
};

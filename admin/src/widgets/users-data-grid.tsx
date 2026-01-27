'use client';

import {
    useReactTable,
    getCoreRowModel,
    flexRender,
    createColumnHelper,
    getSortedRowModel,
    SortingState
} from '@tanstack/react-table';
import { useState } from 'react';
import { User, UserStatus } from '@/entities/user/model/types';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/organisms/table';
import { MoreHorizontal, ShieldCheck, ShieldAlert, ShieldX } from 'lucide-react';
import { cn } from '@/lib/utils';
import { CypherText } from '@/shared/ui/atoms/cypher-text';

const columnHelper = createColumnHelper<User>();

const statusStyles: Record<UserStatus, string> = {
    active: "text-matrix-green border-matrix-green",
    expired: "text-muted-foreground border-muted-foreground",
    banned: "text-server-offline border-server-offline",
    trial: "text-neon-cyan border-neon-cyan"
};

const columns = [
    columnHelper.accessor('email', {
        header: 'IDENTITY',
        cell: info => <span className="font-cyber tracking-wide text-foreground"><CypherText text={info.getValue()} revealSpeed={20} /></span>
    }),
    columnHelper.accessor('plan', {
        header: 'SUBSCRIPTION',
        cell: info => <span className="uppercase text-xs font-bold text-neon-pink"><CypherText text={info.getValue()} revealSpeed={40} /></span>
    }),
    columnHelper.accessor('dataUsage', {
        header: 'DATA USAGE',
        cell: info => {
            const used = info.getValue();
            const limit = info.row.original.dataLimit;
            const percentage = Math.min(100, (used / limit) * 100);

            return (
                <div className="w-32">
                    <div className="flex justify-between text-xs mb-1 font-mono text-muted-foreground">
                        <span>{used} GB</span>
                        <span>{limit} GB</span>
                    </div>
                    <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-neon-cyan"
                            style={{ width: `${percentage}%` }}
                        />
                    </div>
                </div>
            )
        }
    }),
    columnHelper.accessor('status', {
        header: 'STATUS',
        cell: info => (
            <span className={cn(
                "uppercase text-[10px] px-2 py-0.5 border rounded-full font-bold",
                statusStyles[info.getValue()]
            )}>
                {info.getValue()}
            </span>
        )
    }),
    columnHelper.accessor('lastActive', {
        header: 'LAST SEEN',
        cell: info => <span className="text-xs text-muted-foreground">{info.getValue()}</span>
    }),
    columnHelper.display({
        id: 'actions',
        header: 'ACTIONS',
        cell: info => (
            <button className="text-muted-foreground hover:text-white transition-colors">
                <MoreHorizontal className="h-4 w-4" />
            </button>
        )
    })
];

const mockUsers: User[] = [
    { id: '1', email: 'neo@matrix.net', plan: 'cyber', status: 'active', dataUsage: 450, dataLimit: 1000, expiresAt: '2026-12-31', lastActive: '2 mins ago' },
    { id: '2', email: 'trinity@matrix.net', plan: 'pro', status: 'active', dataUsage: 120, dataLimit: 500, expiresAt: '2026-06-15', lastActive: '1 hr ago' },
    { id: '3', email: 'smith@agent.sys', plan: 'basic', status: 'banned', dataUsage: 55, dataLimit: 100, expiresAt: '2025-01-01', lastActive: '3 days ago' },
    { id: '4', email: 'morpheus@zion.org', plan: 'ultra', status: 'trial', dataUsage: 12, dataLimit: 50, expiresAt: '2026-02-28', lastActive: 'Just now' },
    { id: '5', email: 'cypher@traitor.net', plan: 'basic', status: 'expired', dataUsage: 99, dataLimit: 100, expiresAt: '2025-11-20', lastActive: '2 months ago' },
];

export function UsersDataGrid() {
    const [sorting, setSorting] = useState<SortingState>([]);

    const table = useReactTable({
        data: mockUsers,
        columns,
        state: { sorting },
        onSortingChange: setSorting,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
    });

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-display text-neon-pink">CLIENT DATABASE</h2>
                <div className="flex gap-2">
                    <input
                        type="text"
                        placeholder="SEARCH_IDENTITY..."
                        className="bg-black/20 border border-grid-line/50 rounded px-3 py-1.5 text-sm font-mono focus:border-neon-pink focus:outline-none w-64"
                    />
                </div>
            </div>

            <Table>
                <TableHeader>
                    {table.getHeaderGroups().map(headerGroup => (
                        <TableRow key={headerGroup.id}>
                            {headerGroup.headers.map(header => (
                                <TableHead key={header.id}>
                                    {header.isPlaceholder
                                        ? null
                                        : flexRender(header.column.columnDef.header, header.getContext())}
                                </TableHead>
                            ))}
                        </TableRow>
                    ))}
                </TableHeader>
                <TableBody>
                    {table.getRowModel().rows.map(row => (
                        <TableRow key={row.id}>
                            {row.getVisibleCells().map(cell => (
                                <TableCell key={cell.id}>
                                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                </TableCell>
                            ))}
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}

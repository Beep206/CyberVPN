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
import { useTranslations } from 'next-intl';
import { Server } from '@/entities/server/model/types';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/shared/ui/organisms/table';
import { ServerStatusDot } from '@/shared/ui/atoms/server-status-dot';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { Settings, Power, RotateCw, AlertTriangle } from 'lucide-react';
import { InceptionButton } from '@/components/ui/InceptionButton';
import { useServers } from '@/features/servers/hooks/useServers';

const columnHelper = createColumnHelper<Server>();

export function ServersDataGrid() {
    const t = useTranslations('ServersTable');
    const [sorting, setSorting] = useState<SortingState>([]);
    const { data: servers = [], isPending, error } = useServers();

    const columns = (() => {
        const statusLabels = {
            online: t('status.online'),
            offline: t('status.offline'),
            warning: t('status.warning'),
            maintenance: t('status.maintenance')
        } as const;

        return [
            columnHelper.accessor('name', {
                header: t('columns.serverName'),
                cell: info => <span className="font-bold text-foreground"><CypherText text={info.getValue()} revealSpeed={20} /></span>
            }),
            columnHelper.accessor('location', {
                header: t('columns.location'),
                cell: info => <CypherText text={info.getValue()} revealSpeed={30} />
            }),
            columnHelper.accessor('ip', {
                header: t('columns.ipAddress'),
                cell: info => <span className="text-neon-cyan/80"><CypherText text={info.getValue()} characters="0123456789." revealSpeed={40} /></span>
            }),
            columnHelper.accessor('protocol', {
                header: t('columns.protocol'),
                cell: info => <span className="uppercase text-xs border border-grid-line px-2 py-0.5 rounded"><CypherText text={info.getValue()} /></span>
            }),
            columnHelper.display({
                id: 'status',
                header: t('columns.status'),
                cell: info => (
                    <div className="flex items-center gap-2">
                        <ServerStatusDot status={info.row.original.status} />
                        <span className="uppercase text-xs">
                            {statusLabels[info.row.original.status] ?? info.row.original.status}
                        </span>
                    </div>
                )
            }),
            columnHelper.accessor('load', {
                header: t('columns.load'),
                cell: info => {
                    const load = info.getValue();
                    return (
                        <div className="w-24">
                            <div className="flex justify-between text-xs mb-1">
                                <span>{load}%</span>
                            </div>
                            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
                                <div
                                    className={`h-full ${load > 80 ? 'bg-server-warning' : 'bg-matrix-green'}`}
                                    style={{ width: `${load}%` }}
                                />
                            </div>
                        </div>
                    )
                }
            }),
            columnHelper.display({
                id: 'actions',
                header: t('columns.controls'),
                cell: () => (
                    <div className="flex gap-2">
                        <InceptionButton>
                            <button className="p-1 hover:text-neon-cyan transition-colors" title={t('actions.restart')} aria-label={t('actions.restart')}>
                                <RotateCw className="h-4 w-4" />
                            </button>
                        </InceptionButton>
                        <InceptionButton>
                            <button className="p-1 hover:text-neon-pink transition-colors" title={t('actions.stop')} aria-label={t('actions.stop')}>
                                <Power className="h-4 w-4" />
                            </button>
                        </InceptionButton>
                        <InceptionButton>
                            <button className="p-1 hover:text-foreground transition-colors" title={t('actions.config')} aria-label={t('actions.config')}>
                                <Settings className="h-4 w-4" />
                            </button>
                        </InceptionButton>
                    </div>
                )
            })
        ];
    })();

    // eslint-disable-next-line react-hooks/incompatible-library
    const table = useReactTable({
        data: servers,
        columns,
        state: { sorting },
        onSortingChange: setSorting,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getRowId: (row) => row.id,
    });

    if (error) {
        return (
            <div className="flex items-center gap-2 rounded-sm border border-server-warning/50 bg-server-warning/10 p-4 font-mono text-sm text-server-warning">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>{t('error') ?? 'Failed to load servers'}</span>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            <div className="flex justify-between items-center">
                <h2 className="text-xl font-display text-neon-cyan">{t('title')}</h2>
                <div className="flex gap-2">
                    <button className="bg-neon-cyan/10 border border-neon-cyan/50 text-neon-cyan px-4 py-2 text-sm font-mono hover:bg-neon-cyan/20 transition">
                        {t('deployNode')}
                    </button>
                </div>
            </div>

            {isPending ? (
                <div className="animate-pulse space-y-2">
                    {Array.from({ length: 5 }, (_, i) => (
                        <div key={i} className="h-12 rounded-xs bg-terminal-surface/50" />
                    ))}
                </div>
            ) : (
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
            )}
        </div>
    );
}

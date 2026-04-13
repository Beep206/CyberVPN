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
import { MobileDataList, type MobileDataListItem } from '@/shared/ui/mobile-data-list';
import { ServerStatusDot } from '@/shared/ui/atoms/server-status-dot';
import { CypherText } from '@/shared/ui/atoms/cypher-text';
import { Settings, Power, RotateCw, AlertTriangle } from 'lucide-react';
import { InceptionButton } from '@/components/ui/InceptionButton';
import { useServers } from '@/features/servers/hooks/useServers';

const columnHelper = createColumnHelper<Server>();

function getGovernanceTone(governanceState: Server['governanceState']) {
    switch (governanceState) {
        case 'plugin-active':
            return 'border-matrix-green/40 bg-matrix-green/10 text-matrix-green';
        case 'node-disabled':
            return 'border-red-500/40 bg-red-500/10 text-red-400';
        case 'no-plugin':
            return 'border-neon-purple/40 bg-neon-purple/10 text-neon-purple';
    }
}

function shortPluginUuid(pluginUuid: string | null) {
    if (!pluginUuid) return null;
    return pluginUuid.slice(0, 8);
}

export function ServersDataGrid() {
    const t = useTranslations('ServersTable');
    const [sorting, setSorting] = useState<SortingState>([]);
    const { data: servers = [], isPending, error } = useServers();
    const noDataLabel = t('labels.noData');

    const statusLabels = {
        online: t('status.online'),
        offline: t('status.offline'),
        warning: t('status.warning'),
        maintenance: t('status.maintenance')
    } as const;

    const governanceLabels = {
        'plugin-active': t('governance.pluginActive'),
        'no-plugin': t('governance.noPlugin'),
        'node-disabled': t('governance.nodeDisabled'),
    } as const;

    const governanceSummary = servers.reduce(
        (accumulator, server) => {
            accumulator[server.governanceState] += 1;
            return accumulator;
        },
        {
            'plugin-active': 0,
            'no-plugin': 0,
            'node-disabled': 0,
        } satisfies Record<Server['governanceState'], number>,
    );

    const renderServerActions = (server: Server) => (
        <>
            <InceptionButton>
                <button className="p-1 hover:text-neon-cyan transition-colors" title={t('actions.restart')} aria-label={`${t('actions.restart')} ${server.name}`}>
                    <RotateCw className="h-4 w-4" />
                </button>
            </InceptionButton>
            <InceptionButton>
                <button className="p-1 hover:text-neon-pink transition-colors" title={t('actions.stop')} aria-label={`${t('actions.stop')} ${server.name}`}>
                    <Power className="h-4 w-4" />
                </button>
            </InceptionButton>
            <InceptionButton>
                <button className="p-1 hover:text-foreground transition-colors" title={t('actions.config')} aria-label={`${t('actions.config')} ${server.name}`}>
                    <Settings className="h-4 w-4" />
                </button>
            </InceptionButton>
        </>
    );

    const columns = (() => {
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
                id: 'versions',
                header: t('columns.versions'),
                cell: info => (
                    <div className="space-y-1 text-xs font-mono">
                        <div className="flex items-center justify-between gap-3 text-muted-foreground">
                            <span>{t('labels.nodeVersion')}</span>
                            <span className="text-foreground">{info.row.original.nodeVersion ?? noDataLabel}</span>
                        </div>
                        <div className="flex items-center justify-between gap-3 text-muted-foreground">
                            <span>{t('labels.xrayVersion')}</span>
                            <span className="text-foreground">{info.row.original.xrayVersion ?? noDataLabel}</span>
                        </div>
                    </div>
                )
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
            columnHelper.display({
                id: 'governance',
                header: t('columns.governance'),
                cell: info => {
                    const { governanceState, activePluginUuid } = info.row.original;
                    const pluginUuid = shortPluginUuid(activePluginUuid);
                    return (
                        <div className="space-y-1">
                            <span className={`inline-flex rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${getGovernanceTone(governanceState)}`}>
                                {governanceLabels[governanceState]}
                            </span>
                            <div className="text-[11px] font-mono text-muted-foreground">
                                {t('labels.plugin')}: {pluginUuid ?? noDataLabel}
                            </div>
                        </div>
                    );
                }
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
                cell: info => (
                    <div className="flex gap-2">
                        {renderServerActions(info.row.original)}
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

    const mobileItems: MobileDataListItem[] = servers.map((server) => ({
        id: server.id,
        title: <CypherText text={server.name} revealSpeed={20} />,
        subtitle: (
            <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center rounded-full border border-grid-line/40 px-2 py-1 text-[10px] uppercase tracking-wider text-muted-foreground">
                    {server.protocol}
                </span>
                <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${getGovernanceTone(server.governanceState)}`}>
                    {governanceLabels[server.governanceState]}
                </span>
            </div>
        ),
        status: (
            <>
                <ServerStatusDot status={server.status} />
                <span>{statusLabels[server.status] ?? server.status}</span>
            </>
        ),
        priority: <span>{server.load}%</span>,
        primaryFields: [
            { label: t('columns.location'), value: server.location },
            { label: t('columns.ipAddress'), value: server.ip, emphasize: true },
        ],
        secondaryFields: [
            { label: t('columns.load'), value: `${server.load}%` },
            { label: t('labels.clients'), value: String(server.clients) },
            { label: t('labels.nodeVersion'), value: server.nodeVersion ?? noDataLabel },
            { label: t('labels.governance'), value: governanceLabels[server.governanceState] },
            { label: t('labels.plugin'), value: shortPluginUuid(server.activePluginUuid) ?? noDataLabel },
            { label: t('labels.uptime'), value: server.uptime, fullWidth: true },
        ],
        actions: renderServerActions(server),
    }));

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
            <div
                data-testid="servers-grid-toolbar"
                className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
            >
                <div className="space-y-3">
                    <h2 className="text-xl font-display text-neon-cyan">{t('title')}</h2>
                    <div className="flex flex-wrap gap-2">
                        <span className={`inline-flex rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.18em] ${getGovernanceTone('plugin-active')}`}>
                            {governanceLabels['plugin-active']}: {governanceSummary['plugin-active']}
                        </span>
                        <span className={`inline-flex rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.18em] ${getGovernanceTone('no-plugin')}`}>
                            {governanceLabels['no-plugin']}: {governanceSummary['no-plugin']}
                        </span>
                        <span className={`inline-flex rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.18em] ${getGovernanceTone('node-disabled')}`}>
                            {governanceLabels['node-disabled']}: {governanceSummary['node-disabled']}
                        </span>
                    </div>
                </div>
                <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
                    <button className="w-full bg-neon-cyan/10 border border-neon-cyan/50 text-neon-cyan px-4 py-2 text-sm font-mono hover:bg-neon-cyan/20 transition sm:w-auto">
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
                <>
                    <div data-testid="servers-mobile-list" className="md:hidden">
                        <MobileDataList items={mobileItems} />
                    </div>

                    <div data-testid="servers-desktop-table" className="hidden md:block">
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
                </>
            )}
        </div>
    );
}

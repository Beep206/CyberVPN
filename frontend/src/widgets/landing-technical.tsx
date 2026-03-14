'use client';

import { useTranslations } from 'next-intl';
import { motion } from 'motion/react';
import { ComparisonTable, ComparisonTableRow } from '@/shared/ui/comparison-table';
import { TechDataGrid, TechDataItem } from '@/shared/ui/tech-data-grid';
import { StatusBadgeLive } from '@/shared/ui/status-badge-live';

export function LandingTechnical() {
    const t = useTranslations('Landing');

    const comparisonRows: ComparisonTableRow[] = [
        {
            id: 'dpi',
            feature: t('comparison_table.rows.dpi.feature'),
            legacy: t('comparison_table.rows.dpi.legacy'),
            cybervpn: t('comparison_table.rows.dpi.cybervpn')
        },
        {
            id: 'speed',
            feature: t('comparison_table.rows.speed.feature'),
            legacy: t('comparison_table.rows.speed.legacy'),
            cybervpn: t('comparison_table.rows.speed.cybervpn')
        },
        {
            id: 'ip_blocking',
            feature: t('comparison_table.rows.ip_blocking.feature'),
            legacy: t('comparison_table.rows.ip_blocking.legacy'),
            cybervpn: t('comparison_table.rows.ip_blocking.cybervpn')
        },
        {
            id: 'privacy',
            feature: t('comparison_table.rows.privacy.feature'),
            legacy: t('comparison_table.rows.privacy.legacy'),
            cybervpn: t('comparison_table.rows.privacy.cybervpn')
        }
    ];

    const techSpecs: TechDataItem[] = [
        {
            id: 'enc',
            label: 'Encryption',
            value: t('tech_specs.encryption').split(': ')[1] || 'ChaCha20-Poly1305 / AES-128-GCM'
        },
        {
            id: 'trans',
            label: 'Transport',
            value: t('tech_specs.transport').split(': ')[1] || 'TCP, gRPC, WebSocket (HTTP Upgrade)'
        },
        {
            id: 'net',
            label: 'Network',
            value: t('tech_specs.network').split(': ')[1] || '10Gbps Uplinks, Global IPv6 Support'
        }
    ];

    const networkStats: TechDataItem[] = [
        {
            id: 'bw',
            label: 'Bandwidth',
            value: t('network_stats.bandwidth'),
            scramble: true
        },
        {
            id: 'nodes',
            label: 'Active Nodes',
            value: t('network_stats.nodes'),
            scramble: true
        },
        {
            id: 'cov',
            label: 'Coverage',
            value: t('network_stats.coverage'),
            scramble: true
        },
        {
            id: 'uptime',
            label: 'Network Availability',
            value: t('network_stats.uptime'),
            scramble: true
        }
    ];

    return (
        <section className="relative py-32 bg-terminal-bg/80 border-y border-grid-line/20 overflow-hidden">
            {/* Background Grid & Scanlines */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:40px_40px]" />
                <div className="absolute inset-0 scanline opacity-20" />
                
                {/* Asymmetric glows for depth */}
                <div className="absolute top-1/2 left-0 w-[500px] h-[500px] bg-neon-cyan/5 dark:bg-neon-cyan/10 rounded-full blur-[120px]" />
                <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-neon-purple/5 dark:bg-neon-purple/10 rounded-full blur-[100px]" />
            </div>

            <div className="container mx-auto px-4 max-w-6xl relative z-10">
                
                {/* Visual Explanation of Masquerade */}
                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true, margin: '-50px' }}
                    className="mb-24 text-center max-w-3xl mx-auto"
                >
                    <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-neon-purple/30 bg-neon-purple/10 text-neon-purple text-xs font-mono mb-6 backdrop-blur-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-neon-purple animate-pulse" />
                        ANTI-DPI ENGINE
                    </div>
                    <h2 className="text-4xl md:text-5xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-purple via-neon-cyan to-neon-purple mb-6 pb-2">
                        {t('how_it_works.title')}
                    </h2>
                    <p className="text-lg text-muted-foreground font-mono leading-relaxed p-6 bg-terminal-surface/40 backdrop-blur-md border border-grid-line/30 rounded-2xl shadow-lg relative overflow-hidden group">
                        <span className="absolute inset-0 w-full h-full bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                        <span className="absolute left-0 top-0 w-1 h-full bg-gradient-to-b from-neon-cyan to-neon-purple" />
                        {t('how_it_works.desc')}
                    </p>
                </motion.div>

                {/* Comparison Table */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true, margin: '-50px' }}
                    transition={{ delay: 0.2, type: 'spring', stiffness: 50 }}
                    className="mb-24 relative"
                >
                    <div className="absolute -inset-1 bg-gradient-to-r from-neon-cyan/20 to-neon-purple/20 rounded-[1.5rem] blur opacity-50 pointer-events-none" />
                    <ComparisonTable
                        title={t('comparison_table.title')}
                        headers={{
                            feature: t('comparison_table.headers.feature'),
                            legacy: t('comparison_table.headers.legacy'),
                            cybervpn: t('comparison_table.headers.cybervpn')
                        }}
                        rows={comparisonRows}
                        className="bg-terminal-bg/90 backdrop-blur-2xl shadow-2xl border-none"
                    />
                </motion.div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
                    {/* Live Node Status (spanning 5 columns) */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true, margin: '-50px' }}
                        className="lg:col-span-5 cyber-card p-6 md:p-8 rounded-2xl"
                    >
                        <div className="flex items-center justify-between mb-8">
                            <h3 className="text-2xl font-display text-neon-cyan uppercase flex items-center gap-3 m-0">
                                <span className="w-3 h-3 bg-neon-cyan rounded-sm shadow-[0_0_10px_rgba(0,255,255,0.8)] animate-pulse" />
                                {t('status_board.title')}
                            </h3>
                            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-500 text-xs font-mono tracking-widest">
                                <span className="relative flex h-2 w-2">
                                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]"></span>
                                </span>
                                LIVE
                            </div>
                        </div>
                        <div className="grid gap-5">
                            <StatusBadgeLive 
                                protocol={t('status_board.protocols.reality') || 'Reality'} 
                                status={t('status_board.item_online') || 'ONLINE'} 
                                nodeName="Node-RU-01" 
                                latency="24ms"
                                className="w-full justify-between"
                            />
                            <StatusBadgeLive 
                                protocol={t('status_board.protocols.reality') || 'Reality'} 
                                status={t('status_board.item_online') || 'ONLINE'} 
                                nodeName="Node-DE-12" 
                                latency="15ms" 
                                className="w-full justify-between"
                            />
                            <StatusBadgeLive 
                                protocol={t('status_board.protocols.vless_grpc') || 'VLESS-gRPC'} 
                                status={t('status_board.item_online') || 'ONLINE'} 
                                nodeName="Node-US-03" 
                                latency="110ms" 
                                className="w-full justify-between"
                            />
                        </div>
                    </motion.div>

                    {/* Tech & Network Stats Grid (spanning 7 columns) */}
                    <div className="lg:col-span-7 flex flex-col gap-10">
                        <TechDataGrid
                            title="Technical Specifications"
                            items={techSpecs}
                            columns={1}
                        />
                        <TechDataGrid
                            title={t('network_stats.title')}
                            items={networkStats}
                            columns={2}
                        />
                    </div>
                </div>
            </div>
        </section>
    );
}

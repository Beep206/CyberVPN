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
        <section className="relative py-24 bg-terminal-bg/50 border-y border-grid-line/20">
            <div className="container mx-auto px-4 max-w-6xl">
                
                {/* Visual Explanation of Masquerade */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    className="mb-20 text-center max-w-3xl mx-auto"
                >
                    <h2 className="text-3xl font-display font-bold text-neon-cyan mb-4">
                        {t('how_it_works.title')}
                    </h2>
                    <p className="text-lg text-muted-foreground font-mono leading-relaxed">
                        {t('how_it_works.desc')}
                    </p>
                </motion.div>

                {/* Comparison Table */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    whileInView={{ opacity: 1, scale: 1 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.2 }}
                    className="mb-20"
                >
                    <ComparisonTable
                        title={t('comparison_table.title')}
                        headers={{
                            feature: t('comparison_table.headers.feature'),
                            legacy: t('comparison_table.headers.legacy'),
                            cybervpn: t('comparison_table.headers.cybervpn')
                        }}
                        rows={comparisonRows}
                    />
                </motion.div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
                    {/* Live Node Status */}
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                    >
                        <h3 className="text-2xl font-display text-neon-purple mb-6 uppercase">
                            {t('status_board.title')}
                        </h3>
                        <div className="grid gap-4">
                            <StatusBadgeLive 
                                protocol={t('status_board.protocols.reality') || 'Reality'} 
                                status={t('status_board.item_online') || 'ONLINE'} 
                                nodeName="Node-RU-01" 
                                latency="24ms" 
                            />
                            <StatusBadgeLive 
                                protocol={t('status_board.protocols.reality') || 'Reality'} 
                                status={t('status_board.item_online') || 'ONLINE'} 
                                nodeName="Node-DE-12" 
                                latency="15ms" 
                            />
                            <StatusBadgeLive 
                                protocol={t('status_board.protocols.vless_grpc') || 'VLESS-gRPC'} 
                                status={t('status_board.item_online') || 'ONLINE'} 
                                nodeName="Node-US-03" 
                                latency="110ms" 
                            />
                        </div>
                    </motion.div>

                    {/* Tech & Network Stats Grid */}
                    <motion.div
                        initial={{ opacity: 0, x: 20 }}
                        whileInView={{ opacity: 1, x: 0 }}
                        viewport={{ once: true }}
                        className="flex flex-col gap-8"
                    >
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
                    </motion.div>
                </div>
            </div>
        </section>
    );
}

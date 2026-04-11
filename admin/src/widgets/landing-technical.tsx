import { getTranslations } from 'next-intl/server';
import { ComparisonTable, type ComparisonTableRow } from '@/shared/ui/comparison-table';
import { LazyMount } from '@/shared/ui/lazy-mount';
import { Reveal } from '@/shared/ui/reveal';
import { StatusBadgeLive } from '@/shared/ui/status-badge-live';
import { TechDataGrid, type TechDataItem } from '@/shared/ui/tech-data-grid';
import { LandingTechnicalScene } from '@/widgets/landing-technical-scene';

export async function LandingTechnical() {
  const t = await getTranslations('Landing');

  const comparisonRows: ComparisonTableRow[] = [
    {
      id: 'dpi',
      feature: t('comparison_table.rows.dpi.feature'),
      legacy: t('comparison_table.rows.dpi.legacy'),
      cybervpn: t('comparison_table.rows.dpi.cybervpn'),
    },
    {
      id: 'speed',
      feature: t('comparison_table.rows.speed.feature'),
      legacy: t('comparison_table.rows.speed.legacy'),
      cybervpn: t('comparison_table.rows.speed.cybervpn'),
    },
    {
      id: 'ip_blocking',
      feature: t('comparison_table.rows.ip_blocking.feature'),
      legacy: t('comparison_table.rows.ip_blocking.legacy'),
      cybervpn: t('comparison_table.rows.ip_blocking.cybervpn'),
    },
    {
      id: 'privacy',
      feature: t('comparison_table.rows.privacy.feature'),
      legacy: t('comparison_table.rows.privacy.legacy'),
      cybervpn: t('comparison_table.rows.privacy.cybervpn'),
    },
  ];

  const techSpecs: TechDataItem[] = [
    {
      id: 'enc',
      label: t('technical.labels.encryption'),
      value: t('tech_specs.encryption').split(': ')[1] || 'ChaCha20-Poly1305 / AES-128-GCM',
    },
    {
      id: 'trans',
      label: t('technical.labels.transport'),
      value: t('tech_specs.transport').split(': ')[1] || 'XHTTP (Next-Gen), gRPC, Reality-TCP',
    },
    {
      id: 'net',
      label: t('technical.labels.network'),
      value: t('tech_specs.network').split(': ')[1] || '10Gbps Uplinks, Global IPv6 Support',
    },
  ];

  const networkStats: TechDataItem[] = [
    { id: 'bw', label: t('technical.networkLabels.bandwidth'), value: t('network_stats.bandwidth'), scramble: true },
    { id: 'nodes', label: t('technical.networkLabels.nodes'), value: t('network_stats.nodes'), scramble: true },
    { id: 'cov', label: t('technical.networkLabels.coverage'), value: t('network_stats.coverage'), scramble: true },
    { id: 'uptime', label: t('technical.networkLabels.uptime'), value: t('network_stats.uptime'), scramble: true },
  ];

  return (
    <section className="relative py-32 bg-terminal-bg/80 border-y border-grid-line/20 overflow-hidden">
      <LazyMount
        className="absolute inset-0 z-0 pointer-events-none"
        defer="idle"
        minimumTier="full"
        placeholder={<div className="absolute inset-0 z-0" />}
      >
        <LandingTechnicalScene />
      </LazyMount>

      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-grid-white/[0.02] bg-[size:40px_40px]" />
        <div className="absolute inset-0 scanline opacity-20" />
        <div className="absolute top-1/2 left-0 w-[500px] h-[500px] bg-neon-cyan/5 dark:bg-neon-cyan/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-0 right-1/4 w-[400px] h-[400px] bg-neon-purple/5 dark:bg-neon-purple/10 rounded-full blur-[100px]" />
      </div>

      <div className="container mx-auto px-4 max-w-6xl relative z-10">
        <Reveal className="mb-24 text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-neon-purple/30 bg-neon-purple/10 text-neon-purple text-xs font-mono mb-6 backdrop-blur-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-neon-purple animate-pulse" />
            {t('how_it_works.badge')}
          </div>
          <h2 className="text-4xl md:text-5xl font-display font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-purple via-neon-cyan to-neon-purple mb-6 pb-2">
            {t('how_it_works.title')}
          </h2>
          <p className="text-lg text-muted-foreground font-mono leading-relaxed p-6 bg-terminal-surface/40 backdrop-blur-md border border-grid-line/30 rounded-2xl shadow-lg relative overflow-hidden group">
            <span className="absolute inset-0 w-full h-full bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <span className="absolute left-0 top-0 w-1 h-full bg-gradient-to-b from-neon-cyan to-neon-purple" />
            {t('how_it_works.desc')}
          </p>
        </Reveal>

        <Reveal delay={0.2} variant="scale" className="mb-24 relative">
          <div className="absolute -inset-1 bg-gradient-to-r from-neon-cyan/20 to-neon-purple/20 rounded-[1.5rem] blur opacity-50 pointer-events-none" />
          <ComparisonTable
            title={t('comparison_table.title')}
            headers={{
              feature: t('comparison_table.headers.feature'),
              legacy: t('comparison_table.headers.legacy'),
              cybervpn: t('comparison_table.headers.cybervpn'),
            }}
            rows={comparisonRows}
            className="bg-terminal-bg/90 backdrop-blur-2xl shadow-2xl border-none"
          />
        </Reveal>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
          <Reveal variant="left" className="lg:col-span-5 cyber-card p-6 md:p-8 rounded-2xl">
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-2xl font-display text-neon-cyan uppercase flex items-center gap-3 m-0">
                <span className="w-3 h-3 bg-neon-cyan rounded-sm shadow-[0_0_10px_rgba(0,255,255,0.8)] animate-pulse" />
                {t('status_board.title')}
              </h3>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-500 text-xs font-mono tracking-widest">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)]" />
                </span>
                {t('status_board.live')}
              </div>
            </div>
            <div className="grid gap-5">
              <StatusBadgeLive protocol={t('status_board.protocols.reality')} status={t('status_board.item_online')} nodeName="Node-RU-01" latency="24ms" className="w-full justify-between" />
              <StatusBadgeLive protocol={t('status_board.protocols.reality')} status={t('status_board.item_online')} nodeName="Node-DE-12" latency="15ms" className="w-full justify-between" />
              <StatusBadgeLive protocol={t('status_board.protocols.vless_grpc')} status={t('status_board.item_online')} nodeName="Node-US-03" latency="110ms" className="w-full justify-between" />
            </div>
          </Reveal>

          <div className="lg:col-span-7 flex flex-col gap-10">
            <TechDataGrid title={t('technical.specificationsTitle')} items={techSpecs} columns={1} />
            <TechDataGrid title={t('network_stats.title')} items={networkStats} columns={2} />
          </div>
        </div>
      </div>
    </section>
  );
}

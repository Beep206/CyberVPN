import type { Metadata } from 'next';
import { getTranslations } from "next-intl/server";
import { ServerCard } from "@/shared/ui/molecules/server-card";

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Dashboard' });
    return {
        title: t('title'),
        description: t('statusLabel'),
    };
}

const servers = [
    { id: '1', name: 'Tokyo Node 01', location: 'Japan, Tokyo', status: 'online' as const, ip: '45.32.12.90', load: 45, protocol: 'vless' as const },
    { id: '2', name: 'NYC Core', location: 'USA, New York', status: 'warning' as const, ip: '192.168.1.1', load: 82, protocol: 'wireguard' as const },
    { id: '3', name: 'London Edge', location: 'UK, London', status: 'online' as const, ip: '178.2.4.11', load: 23, protocol: 'xhttp' as const },
    { id: '4', name: 'Singapore Stealth', location: 'Singapore', status: 'maintenance' as const, ip: '201.10.3.55', load: 0, protocol: 'vless' as const },
];

export default async function Dashboard({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Dashboard' });
    return (
        <div className="p-8 space-y-8">
            <header className="flex flex-col md:flex-row justify-between md:items-center mb-8 bg-terminal-surface/30 p-4 rounded-xl border border-grid-line/30 backdrop-blur gap-4">
                <div>
                    <h1 className="text-2xl md:text-4xl font-display text-neon-cyan drop-shadow-glow break-words">{t('title')}</h1>
                    <p className="text-muted-foreground font-mono mt-1 text-sm md:text-base">{t('statusLabel')} <span className="text-matrix-green">{t('statusValue')}</span></p>
                </div>
                <div className="hidden md:block text-right font-cyber text-sm text-neon-pink">
                    {t('connectionStatus')}<br />
                    {t('encryptionStatus')}
                </div>
            </header>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="cyber-card p-6 rounded-xl">
                    <h2 className="text-xl font-mono text-neon-pink mb-2">{t('serverStatus')}</h2>
                    <div className="text-4xl font-display text-server-online drop-shadow-glow">
                        {servers.filter(s => s.status === 'online').length} / {servers.length}
                    </div>
                    <p className="text-sm text-muted-foreground mt-2">{t('nodesOnline')}</p>
                </div>
                <div className="cyber-card p-6 rounded-xl">
                    <h2 className="text-xl font-mono text-neon-pink mb-2">{t('activeSessions')}</h2>
                    <div className="text-4xl font-display text-neon-cyan drop-shadow-glow">1,337</div>
                    <p className="text-sm text-muted-foreground mt-2">{t('currentConnections')}</p>
                </div>
                <div className="cyber-card p-6 rounded-xl">
                    <h2 className="text-xl font-mono text-neon-pink mb-2">{t('networkLoad')}</h2>
                    <div className="text-4xl font-display text-matrix-green drop-shadow-glow">42 Pb/s</div>
                    <p className="text-sm text-muted-foreground mt-2">{t('aggregateThroughput')}</p>
                </div>
            </div>

            <h2 className="text-2xl font-display text-neon-purple mt-12 mb-6 pl-2 border-l-4 border-neon-purple">{t('serverMatrix')}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {servers.map((server, index) => (
                    <ServerCard key={server.id} server={server} index={index} />
                ))}
            </div>
        </div>
    );
}

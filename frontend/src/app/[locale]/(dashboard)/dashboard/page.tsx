import { getTranslations } from "next-intl/server";
import { DashboardStats } from "./components/DashboardStats";
import { ServerGrid } from "./components/ServerGrid";

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

            {/* Stats Grid - Now using real API data via TanStack Query */}
            <DashboardStats />

            <h2 className="text-2xl font-display text-neon-purple mt-12 mb-6 pl-2 border-l-4 border-neon-purple">{t('serverMatrix')}</h2>

            {/* Server Grid - Now using real API data via TanStack Query */}
            <ServerGrid />
        </div>
    );
}

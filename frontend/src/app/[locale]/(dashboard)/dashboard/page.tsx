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
        <div className="min-h-screen bg-terminal-bg text-foreground relative overflow-hidden p-4 md:p-8">
            {/* Background Grid */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(0,255,136,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(0,255,136,0.03)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />

            {/* Glow Effects */}
            <div className="absolute top-0 left-1/4 w-96 h-96 bg-neon-cyan/20 rounded-full blur-[100px] pointer-events-none" />
            <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-neon-purple/20 rounded-full blur-[100px] pointer-events-none" />

            <div className="max-w-7xl mx-auto relative z-10 space-y-8">
                {/* Header */}
                <header className="flex flex-col md:flex-row justify-between items-center mb-12 bg-terminal-surface/30 p-6 rounded-xl border border-grid-line/30 backdrop-blur gap-4 shadow-[0_0_30px_rgba(0,255,255,0.05)]">
                    <div className="flex items-center gap-4 w-full md:w-auto">
                        <div className="hidden md:flex w-12 h-12 rounded-lg bg-neon-cyan/10 border border-neon-cyan/30 items-center justify-center">
                            <span className="font-cyber text-2xl text-neon-cyan">VPN</span>
                        </div>
                        <div>
                            <h1 className="text-2xl md:text-3xl font-display text-white tracking-wider drop-shadow-glow break-words">
                                {t('title')}
                            </h1>
                            <div className="flex items-center gap-2 mt-1">
                                <span className="w-2 h-2 rounded-full bg-matrix-green animate-pulse" />
                                <p className="text-muted-foreground font-mono text-xs md:text-sm">
                                    {t('statusLabel')} <span className="text-matrix-green font-bold">{t('statusValue')}</span>
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="hidden md:block text-right font-cyber text-xs text-neon-pink opacity-80 border-l border-white/10 pl-4">
                        <div className="mb-1">{t('connectionStatus')}</div>
                        <div>{t('encryptionStatus')}</div>
                    </div>
                </header>

                {/* Main Content Area */}
                <div className="grid gap-8">
                    {/* Stats Grid */}
                    <DashboardStats />

                    {/* Server Section */}
                    <div className="space-y-4">
                        <div className="flex items-center gap-2 border-b border-neon-purple/30 pb-2 mb-6">
                            <div className="w-1 h-6 bg-neon-purple" />
                            <h2 className="text-xl font-display text-neon-purple tracking-wide">
                                {t('serverMatrix')}
                            </h2>
                        </div>
                        <ServerGrid />
                    </div>
                </div>
            </div>
        </div>
    );
}

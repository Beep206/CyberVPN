import { getTranslations } from "next-intl/server";
import { WalletClient } from "./components/WalletClient";

export default async function WalletPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Wallet' });

    return (
        <div className="p-8 space-y-8">
            <header className="mb-8">
                <h1 className="text-2xl md:text-4xl font-display text-neon-cyan drop-shadow-glow">
                    {t('title') || 'Wallet'}
                </h1>
                <p className="text-muted-foreground font-mono mt-2">
                    {t('subtitle') || 'Manage your balance and transactions'}
                </p>
            </header>

            <WalletClient />
        </div>
    );
}

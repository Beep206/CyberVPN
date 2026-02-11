import { getTranslations } from "next-intl/server";
import { SubscriptionsClient } from "./components/SubscriptionsClient";

export default async function SubscriptionsPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Subscriptions' });

    return (
        <div className="p-8 space-y-8">
            <header className="mb-8">
                <h1 className="text-2xl md:text-4xl font-display text-neon-cyan drop-shadow-glow">
                    {t('title') || 'Subscriptions'}
                </h1>
                <p className="text-muted-foreground font-mono mt-2">
                    {t('subtitle') || 'Manage your VPN subscription plans'}
                </p>
            </header>

            <SubscriptionsClient />
        </div>
    );
}

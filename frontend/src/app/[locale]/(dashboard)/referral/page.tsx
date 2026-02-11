import { getTranslations } from "next-intl/server";
import { ReferralClient } from "./components/ReferralClient";

export default async function ReferralPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Referral' });

    return (
        <div className="p-8 space-y-8">
            <header className="mb-8">
                <h1 className="text-2xl md:text-4xl font-display text-neon-cyan drop-shadow-glow">
                    {t('title') || 'Referral Program'}
                </h1>
                <p className="text-muted-foreground font-mono mt-2">
                    {t('subtitle') || 'Earn commissions by referring friends'}
                </p>
            </header>

            <ReferralClient />
        </div>
    );
}

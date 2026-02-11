import { getTranslations } from "next-intl/server";
import { PaymentHistoryClient } from "./components/PaymentHistoryClient";

export default async function PaymentHistoryPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'PaymentHistory' });

    return (
        <div className="p-8 space-y-8">
            <header className="mb-8">
                <h1 className="text-2xl md:text-4xl font-display text-neon-cyan drop-shadow-glow">
                    {t('title') || 'Payment History'}
                </h1>
                <p className="text-muted-foreground font-mono mt-2">
                    {t('subtitle') || 'View all your payment transactions'}
                </p>
            </header>

            <PaymentHistoryClient />
        </div>
    );
}

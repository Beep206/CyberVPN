import { getTranslations } from 'next-intl/server';
import { LinkedAccountsSection } from '@/features/profile/components/LinkedAccountsSection';

export default async function SettingsPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Navigation' });

    return (
        <div className="space-y-6 max-w-2xl">
            <h1 className="text-2xl font-display text-neon-cyan tracking-wider">
                {t('settings')}
            </h1>
            <LinkedAccountsSection />
        </div>
    );
}

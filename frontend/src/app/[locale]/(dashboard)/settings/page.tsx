import { getTranslations } from 'next-intl/server';
import { LinkedAccountsSection } from '@/features/profile/components/LinkedAccountsSection';
import { ProfileSection } from './sections/ProfileSection';
import { SecuritySection } from './sections/SecuritySection';
import { DevicesSection } from './sections/DevicesSection';

export default async function SettingsPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Settings' });

    return (
        <div className="p-8 space-y-8">
            <header className="mb-8">
                <h1 className="text-2xl md:text-4xl font-display text-neon-cyan drop-shadow-glow">
                    {t('title') || 'Settings'}
                </h1>
                <p className="text-muted-foreground font-mono mt-2">
                    {t('subtitle') || 'Manage your account preferences and security'}
                </p>
            </header>

            <div className="space-y-8 max-w-4xl">
                {/* Profile Settings */}
                <ProfileSection />

                {/* Security Settings */}
                <SecuritySection />

                {/* Linked Accounts */}
                <section>
                    <h2 className="text-xl font-display text-neon-purple mb-4 pl-2 border-l-4 border-neon-purple">
                        {t('linkedAccounts') || 'Linked Accounts'}
                    </h2>
                    <LinkedAccountsSection />
                </section>

                {/* Active Devices */}
                <DevicesSection />
            </div>
        </div>
    );
}

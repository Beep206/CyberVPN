import { getTranslations } from 'next-intl/server';
import { UsersDataGrid } from '@/widgets/users-data-grid';

export default async function UsersPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Users' });
    return (
        <div className="p-8 space-y-8">
            <div className="flex justify-between items-center mb-8 bg-terminal-surface/30 p-6 rounded-xl border border-grid-line/30 backdrop-blur">
                <div>
                    <h1 className="text-3xl font-display text-foreground tracking-widest">{t('title')}</h1>
                    <p className="text-muted-foreground font-mono mt-2">{t('subtitle')}</p>
                </div>
                <div className="text-right">
                    <div className="text-sm font-cyber text-neon-pink">{t('totalUsers', { count: '4,021' })}</div>
                    <div className="text-xs text-muted-foreground mt-1">{t('newToday', { count: '+12' })}</div>
                </div>
            </div>

            <UsersDataGrid />
        </div>
    );
}

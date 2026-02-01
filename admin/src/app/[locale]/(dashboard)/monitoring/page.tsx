import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';
import PlaceholderPage from '@/shared/ui/pages/placeholder-page';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Navigation' });
    return { title: t('monitoring') };
}

export default async function MonitoringPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    return <PlaceholderPage locale={locale} />;
}

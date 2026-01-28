import PlaceholderPage from '@/shared/ui/pages/placeholder-page';

export default async function SubscriptionsPage({
    params,
}: {
    params: Promise<{ locale: string }>;
}) {
    const { locale } = await params;
    return <PlaceholderPage locale={locale} />;
}

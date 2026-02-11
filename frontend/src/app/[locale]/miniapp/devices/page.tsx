import { getTranslations } from 'next-intl/server';
import { DevicesClient } from './components/DevicesClient';

export default async function DevicesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Devices' });

  return (
    <div className="space-y-6 p-4">
      <div>
        <h1 className="text-2xl font-display text-neon-cyan mb-2">
          {t('title') || 'Active Devices'}
        </h1>
        <p className="text-muted-foreground text-sm">
          {t('subtitle') || 'Manage your active sessions and devices'}
        </p>
      </div>

      <DevicesClient />
    </div>
  );
}

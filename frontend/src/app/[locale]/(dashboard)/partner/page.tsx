import { getTranslations } from 'next-intl/server';
import { PartnerClient } from './components/PartnerClient';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

interface PartnerPageProps {
  params: Promise<{
    locale: string;
  }>;
}

export async function generateMetadata({ params }: PartnerPageProps) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Partner' });

  return withSiteMetadata({
    title: t('pageTitle') || 'Partner Dashboard - CyberVPN',
    description: t('pageDescription') || 'Manage your partner codes and track earnings',
  });
}

export default async function PartnerPage({ params }: PartnerPageProps) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Partner' });

  return (
    <div className="max-w-7xl mx-auto w-full space-y-8">
      <div className="mb-8">
        <h1 className="text-4xl font-display text-neon-cyan mb-2 tracking-wider">
          {t('title') || 'PARTNER_DASHBOARD'}
        </h1>
        <p className="text-muted-foreground font-mono text-sm">
          {t('subtitle') || 'Manage codes, track earnings, grow your network'}
        </p>
      </div>

      <PartnerClient />
    </div>
  );
}

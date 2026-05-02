import { getTranslations } from 'next-intl/server';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';
import { DpiResistanceDashboard } from '@/widgets/network/dpi-resistance-dashboard';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'Network.dpi' });

  return withSiteMetadata({
    title: `${t('title')} | CyberVPN`,
    description: t('description'),
  }, {
    locale,
    canonicalPath: '/network/dpi-resistance',
    routeType: 'public',
  });
}

export default async function NetworkDpiResistancePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  return (
    <main className="min-h-screen bg-black text-terminal-text selection:bg-neon-cyan/30">
      <PublicTerminalHeader locale={locale} />

      <section className="flex-1 pt-16">
        <DpiResistanceDashboard />
      </section>

      <Footer locale={locale} />
    </main>
  );
}

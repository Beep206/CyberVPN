import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { locales } from '@/i18n/config';
import { SITE_URL } from '@/shared/lib/site-metadata';
import { SkipNavLink } from '@/shared/ui/atoms/skip-nav-link';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;

  return {
    title: 'VPN Command Center',
    description: 'Advanced Cyberpunk VPN Admin Interface',
    metadataBase: new URL(SITE_URL),
    alternates: {
      languages: Object.fromEntries(locales.map((entry) => [entry, `/${entry}`])),
      canonical: `/${locale}`,
    },
  };
}

export default async function RootLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: 'A11y' });

  return (
    <>
      <SkipNavLink label={t('skipToMainContent')} />
      {children}
    </>
  );
}

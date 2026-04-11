import type { Metadata } from 'next';
import { Suspense } from 'react';
import { Orbitron, JetBrains_Mono, Share_Tech_Mono } from 'next/font/google';
import Script from 'next/script';
import type { Organization, WebSite } from 'schema-dts';
import { AnalyticsReporters } from '@/app/providers/analytics-reporters';
import { AuthSessionBootstrap } from '@/app/providers/auth-provider';
import { DevTools } from '@/app/providers/dev-tools';
import { MotionProvider } from '@/app/providers/motion-provider';
import { ThemeProvider } from '@/app/providers/theme-provider';
import { getStaticParamsLocales } from '@/i18n/config';
import { getCachedTranslations, setRequestLocale } from '@/i18n/server';
import { JsonLd } from '@/shared/lib/json-ld';
import {
  SITE_URL,
  getHtmlLanguageAttributes,
  withSiteMetadata,
} from '@/shared/lib/site-metadata';
import { SkipNavLink } from '@/shared/ui/atoms/skip-nav-link';
import '../globals.css';

const orbitron = Orbitron({
  variable: '--font-display',
  subsets: ['latin'],
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-mono',
  subsets: ['latin'],
  display: 'swap',
});

const shareTechMono = Share_Tech_Mono({
  weight: '400',
  variable: '--font-cyber',
  subsets: ['latin'],
  display: 'swap',
});

const gaMeasurementId = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;
const isDevelopment = process.env.NODE_ENV === 'development';

export function generateStaticParams() {
  return getStaticParamsLocales().map((locale) => ({ locale }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;

  return withSiteMetadata(
    {
      title: 'VPN Command Center',
      description: 'Advanced Cyberpunk VPN Admin Interface',
    },
    {
      locale,
      canonicalPath: '/',
      routeType: 'public',
    },
  );
}

export default async function RootLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const htmlAttributes = getHtmlLanguageAttributes(locale);

  setRequestLocale(locale);
  const t = await getCachedTranslations(locale, 'A11y');

  return (
    <html lang={htmlAttributes.lang} dir={htmlAttributes.dir} suppressHydrationWarning>
      <body
        suppressHydrationWarning
        className={`
          ${orbitron.variable}
          ${jetbrainsMono.variable}
          ${shareTechMono.variable}
          antialiased bg-terminal-bg text-foreground min-h-screen selection:bg-neon-cyan/30
        `}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <MotionProvider>
            <Suspense fallback={null}>
              <AuthSessionBootstrap />
            </Suspense>
            <SkipNavLink label={t('skipToMainContent')} />
            <div className="relative z-10 min-h-full w-full">{children}</div>
            <div className="pointer-events-none fixed inset-0 z-50 scanline opacity-20" />

            <Suspense fallback={null}>
              <AnalyticsReporters />
            </Suspense>
            {isDevelopment ? <DevTools /> : null}
          </MotionProvider>
        </ThemeProvider>

        <JsonLd<Organization>
          data={{
            '@context': 'https://schema.org',
            '@type': 'Organization',
            name: 'CyberVPN',
            url: SITE_URL,
            logo: `${SITE_URL}/logo.png`,
            sameAs: ['https://t.me/cybervpn'],
          }}
        />

        <JsonLd<WebSite>
          data={{
            '@context': 'https://schema.org',
            '@type': 'WebSite',
            name: 'CyberVPN',
            url: SITE_URL,
          }}
        />

        {gaMeasurementId ? (
          <>
            <Script
              src={`https://www.googletagmanager.com/gtag/js?id=${gaMeasurementId}`}
              strategy="afterInteractive"
            />
            <Script id="ga4-init" strategy="afterInteractive">
              {`
                window.dataLayer = window.dataLayer || [];
                window.gtag = window.gtag || function gtag(){window.dataLayer.push(arguments);};
                window.gtag('js', new Date());
                window.gtag('config', '${gaMeasurementId}', { send_page_view: false });
              `}
            </Script>
          </>
        ) : null}
      </body>
    </html>
  );
}

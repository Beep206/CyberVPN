import type { Metadata } from 'next';
import { Orbitron, JetBrains_Mono, Share_Tech_Mono } from 'next/font/google';
import type { Organization, WebSite } from 'schema-dts';
import { DevTools } from '@/app/providers/dev-tools';
import { MotionProvider } from '@/app/providers/motion-provider';
import { ThemeProvider } from '@/app/providers/theme-provider';
import { JsonLd } from '@/shared/lib/json-ld';
import { SITE_URL } from '@/shared/lib/site-metadata';
import { WebVitalsReporter } from '@/shared/ui/atoms/web-vitals-reporter';
import './globals.css';

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

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        suppressHydrationWarning
        className={`
          ${orbitron.variable}
          ${jetbrainsMono.variable}
          ${shareTechMono.variable}
          antialiased bg-terminal-bg text-foreground min-h-screen overflow-hidden selection:bg-neon-cyan/30
        `}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <MotionProvider>
            <div className="relative z-10 h-full w-full">{children}</div>
            <div className="pointer-events-none fixed inset-0 z-50 scanline opacity-20" />

            <WebVitalsReporter />
            <DevTools />
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
            potentialAction: {
              '@type': 'SearchAction',
              target: `${SITE_URL}/search?q={search_term_string}`,
              // @ts-expect-error - schema.org query-input format
              'query-input': 'required name=search_term_string',
            },
          }}
        />
      </body>
    </html>
  );
}

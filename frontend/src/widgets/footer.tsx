import type { ReactNode } from 'react';

import {
  BookOpen,
  CreditCard,
  LifeBuoy,
  Send,
  Shield,
  Terminal,
  Zap,
} from 'lucide-react';
import { getLocale, getTranslations } from 'next-intl/server';

import { Link } from '@/i18n/navigation';
import { MagneticButton } from '@/shared/ui/magnetic-button';
import { FooterLiveStrip } from '@/widgets/footer-live-strip';

const COPYRIGHT_YEAR = '2026';

const ENTITY_LINKS = [
  { icon: Send, href: 'https://t.me/cybervpn', label: 'Telegram community', external: true },
  { icon: Shield, href: 'https://t.me/cybervpn_bot', label: 'Telegram bot', external: true },
  { icon: Zap, href: '/status', label: 'Status page', external: false },
  { icon: Terminal, href: '/docs', label: 'Documentation', external: false },
] as const;

const FOOTER_LINKS = {
  legal: [
    { label: 'privacy', href: '/privacy' },
    { label: 'terms', href: '/terms' },
    { label: 'security', href: '/security' },
  ],
  product: [
    { label: 'features', href: '/features' },
    { label: 'pricing', href: '/pricing' },
    { label: 'servers', href: '/network' },
    { label: 'download', href: '/download' },
    { label: 'api', href: '/api' },
  ],
  support: [
    { label: 'helpCenter', href: '/help' },
    { label: 'status', href: '/status' },
    { label: 'contact', href: '/contact' },
    { label: 'documentation', href: '/docs' },
  ],
} as const;

const KNOWLEDGE_LINKS = [
  { labelKey: 'guides', href: '/guides' },
  { labelKey: 'compare', href: '/compare' },
  { labelKey: 'devices', href: '/devices' },
  { labelKey: 'trust', href: '/trust' },
  { labelKey: 'audits', href: '/audits' },
] as const;

const PAYMENT_METHODS = [
  { id: 'visa', label: 'Visa' },
  { id: 'mastercard', label: 'Mastercard' },
  { id: 'mir', label: 'MIR' },
  { id: 'usdt', label: 'USDT' },
  { id: 'amex', label: 'American Express' },
] as const;

const SECTION_STYLES = {
  knowledge: {
    dotClassName: 'bg-neon-purple',
    frameClassName: 'border-neon-purple/30 bg-gradient-to-br from-neon-purple/20 to-neon-purple/5',
    glowClassName: 'bg-neon-purple/25',
    icon: BookOpen,
    iconClassName: 'text-neon-purple',
  },
  payments: {
    dotClassName: 'bg-warning',
    frameClassName: 'border-warning/30 bg-gradient-to-br from-warning/20 to-warning/5',
    glowClassName: 'bg-warning/25',
    icon: CreditCard,
    iconClassName: 'text-warning',
  },
  product: {
    dotClassName: 'bg-neon-cyan',
    frameClassName: 'border-neon-cyan/30 bg-gradient-to-br from-neon-cyan/20 to-neon-cyan/5',
    glowClassName: 'bg-neon-cyan/25',
    icon: Terminal,
    iconClassName: 'text-neon-cyan',
  },
  support: {
    dotClassName: 'bg-matrix-green',
    frameClassName: 'border-matrix-green/30 bg-gradient-to-br from-matrix-green/20 to-matrix-green/5',
    glowClassName: 'bg-matrix-green/25',
    icon: LifeBuoy,
    iconClassName: 'text-matrix-green',
  },
} as const;

type SectionKey = keyof typeof SECTION_STYLES;
type PaymentBrandId = (typeof PAYMENT_METHODS)[number]['id'];

function FooterSectionHeading({
  title,
  sectionKey,
}: {
  title: string;
  sectionKey: SectionKey;
}) {
  const { frameClassName, glowClassName, icon: Icon, iconClassName } = SECTION_STYLES[sectionKey];

  return (
    <div className="group inline-flex items-center gap-3">
      <div className="relative">
        <div className={`absolute inset-0 rounded-2xl blur-md opacity-60 transition-opacity duration-300 group-hover:opacity-100 ${glowClassName}`} />
        <div className={`relative flex h-10 w-10 items-center justify-center rounded-2xl border transition-transform duration-300 group-hover:-translate-y-0.5 ${frameClassName}`}>
          <Icon className={`h-4 w-4 transition-transform duration-300 group-hover:scale-110 group-hover:-rotate-6 ${iconClassName}`} />
        </div>
      </div>
      <h4 className="font-display text-lg font-bold text-foreground">
        {title}
      </h4>
    </div>
  );
}

function FooterLinksItem({
  children,
  href,
  locale,
  sectionKey,
  seoCta,
  seoZone,
}: {
  children: ReactNode;
  href: string;
  locale: string;
  sectionKey: Exclude<SectionKey, 'payments'>;
  seoCta?: string;
  seoZone?: string;
}) {
  const { dotClassName } = SECTION_STYLES[sectionKey];

  return (
    <li>
      <Link
        href={href}
        locale={locale}
        className="group inline-flex items-center gap-2 py-1 text-muted-foreground transition-colors hover:text-white"
        data-seo-cta={seoCta}
        data-seo-zone={seoZone}
      >
        <span className={`h-1.5 w-1.5 scale-0 rounded-full opacity-0 transition-all duration-300 group-hover:scale-125 group-hover:opacity-100 ${dotClassName}`} />
        <span className="transition-transform duration-300 group-hover:translate-x-1">
          {children}
        </span>
      </Link>
    </li>
  );
}

function PaymentBrandMark({ brand }: { brand: PaymentBrandId }) {
  switch (brand) {
    case 'visa':
      return (
        <div className="relative flex w-12 items-center justify-center">
          <span className="absolute left-0 top-1/2 h-3.5 w-2 -translate-y-1/2 -skew-x-[24deg] rounded-full bg-[#fbbf24]/90 blur-[1px]" />
          <span className="font-display text-[11px] font-black italic tracking-[-0.12em] text-[#60a5fa] drop-shadow-[0_0_14px_rgba(37,99,235,0.3)]">
            VISA
          </span>
        </div>
      );
    case 'mastercard':
      return (
        <div className="relative flex w-12 items-center justify-center gap-1.5 drop-shadow-[0_0_16px_rgba(247,158,27,0.2)]">
          <div className="relative h-4.5 w-5">
            <span className="absolute left-0 top-1/2 h-4.5 w-4.5 -translate-y-1/2 rounded-full bg-[#ea001b] shadow-[0_0_10px_rgba(234,0,27,0.3)]" />
            <span className="absolute right-0 top-1/2 h-4.5 w-4.5 -translate-y-1/2 rounded-full bg-[#f79e1b] shadow-[0_0_10px_rgba(247,158,27,0.3)]" />
            <span className="absolute left-1/2 top-1/2 h-4.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#ff5f00]/85" />
          </div>
          <span className="font-display text-[7px] font-black uppercase tracking-[0.18em] text-white/90">
            MC
          </span>
        </div>
      );
    case 'mir':
      return (
        <div className="relative flex w-12 items-center justify-center">
          <span className="absolute inset-x-0 bottom-[1px] h-px rounded-full bg-gradient-to-r from-[#4dc47d] via-[#33be79] to-[#1f8fff]" />
          <span className="font-display text-[10px] font-black tracking-[0.16em] text-white drop-shadow-[0_0_12px_rgba(31,143,255,0.22)]">
            MIR
          </span>
        </div>
      );
    case 'usdt':
      return (
        <div className="flex w-12 items-center justify-center gap-1.5">
          <div className="relative flex h-5.5 w-5.5 items-center justify-center rounded-full border border-[#26a17b]/40 bg-[#26a17b]/20 text-[#52c8a3] shadow-[0_0_12px_rgba(38,161,123,0.24)]">
            <span className="absolute top-1.5 h-0.5 w-2.5 rounded-full bg-current" />
            <span className="absolute top-2.5 h-0.5 w-1.5 rounded-full bg-current" />
            <span className="h-3 w-0.5 rounded-full bg-current" />
          </div>
          <span className="font-display text-[7px] font-black uppercase tracking-[0.16em] text-[#8fe1c8]">
            USDT
          </span>
        </div>
      );
    case 'amex':
      return (
        <div className="relative flex w-12 items-center justify-center">
          <span className="absolute inset-0 rounded-full bg-[#1977ff]/12 blur-md" />
          <span className="relative font-display text-[8px] font-black uppercase tracking-[0.24em] text-[#7bd7ff]">
            AMEX
          </span>
        </div>
      );
  }
}

function PaymentBrandIcon({ brand, label }: { brand: PaymentBrandId; label: string }) {
  return (
    <div
      role="img"
      aria-label={label}
      title={label}
      className="group/payment relative flex h-10 items-center justify-center"
    >
      <div className="absolute inset-x-2 bottom-0 h-px bg-gradient-to-r from-transparent via-warning/35 to-transparent opacity-0 transition-opacity duration-300 group-hover/payment:opacity-100" />
      <div className="transition-transform duration-300 group-hover/payment:-translate-y-0.5 group-hover/payment:scale-105">
        <PaymentBrandMark brand={brand} />
      </div>
    </div>
  );
}

export async function Footer({ locale: providedLocale }: { locale?: string } = {}) {
  const locale = providedLocale ?? await getLocale();
  const footerT = await getTranslations({ locale, namespace: 'Footer' });
  const headerT = await getTranslations({ locale, namespace: 'Header' });

  return (
    <footer className="relative w-full overflow-hidden border-t border-grid-line/50 bg-terminal-bg pt-16 pb-8">
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 h-px w-full bg-gradient-to-r from-transparent via-neon-cyan/50 to-transparent opacity-50 blur-[1px]" />
        <div className="absolute right-0 bottom-0 h-[500px] w-[500px] rounded-full bg-neon-purple/10 blur-[100px] dark:bg-neon-purple/5" />
        <div className="absolute top-0 left-0 h-[300px] w-[300px] rounded-full bg-neon-cyan/10 blur-[80px] dark:bg-neon-cyan/5" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{ backgroundImage: "url('/grid-pattern.svg')" }}
        />
      </div>

      <div className="container relative z-10 mx-auto px-6">
        <div className="mb-16 grid grid-cols-1 gap-12 sm:grid-cols-2 lg:grid-cols-12">
          <div className="space-y-6 sm:col-span-2 lg:col-span-4">
            <Link href="/" locale={locale} className="group inline-flex items-center gap-2">
              <div className="relative flex h-10 w-10 items-center justify-center rounded-xl border border-neon-cyan/30 bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 transition-colors group-hover:border-neon-cyan/60">
                <Shield className="h-6 w-6 text-neon-cyan group-hover:animate-pulse" />
              </div>
              <span className="font-display text-2xl font-bold tracking-tight text-white transition-colors group-hover:text-neon-cyan">
                Cyber<span className="text-neon-cyan">VPN</span>
              </span>
            </Link>

            <p className="max-w-sm font-mono text-sm leading-relaxed text-muted-foreground">
              {footerT('brandDescription')}
            </p>

            <div className="flex items-center gap-3 pt-2">
              {ENTITY_LINKS.map(({ icon: Icon, href, label, external }) => (
                <MagneticButton key={label} strength={15}>
                  {external ? (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="group relative flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/40 bg-background/50 text-muted-foreground transition-all duration-300 hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:text-neon-cyan"
                      data-seo-cta={href.includes('t.me') ? 'telegram' : undefined}
                      data-seo-zone={href.includes('t.me') ? 'footer_entity' : undefined}
                    >
                      <Icon className="h-4 w-4 transition-transform group-hover:scale-110" />
                      <span className="sr-only">{label}</span>
                    </a>
                  ) : (
                    <Link
                      href={href}
                      locale={locale}
                      className="group relative flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/40 bg-background/50 text-muted-foreground transition-all duration-300 hover:border-neon-cyan/50 hover:bg-neon-cyan/10 hover:text-neon-cyan"
                      data-seo-cta={href === '/docs' ? 'docs' : undefined}
                      data-seo-zone={href === '/docs' ? 'footer_entity' : undefined}
                    >
                      <Icon className="h-4 w-4 transition-transform group-hover:scale-110" />
                      <span className="sr-only">{label}</span>
                    </Link>
                  )}
                </MagneticButton>
              ))}
            </div>

            <div className="flex flex-wrap gap-4 pt-4 font-mono text-xs text-muted-foreground-low">
              {FOOTER_LINKS.legal.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  locale={locale}
                  className="px-1 py-1 transition-colors hover:text-neon-cyan"
                >
                  {footerT(`links.${link.label}`)}
                </Link>
              ))}
            </div>
          </div>

          <div className="space-y-6 lg:col-span-2">
            <FooterSectionHeading sectionKey="product" title={footerT('sections.product')} />
            <ul className="space-y-3 font-mono text-sm">
              {FOOTER_LINKS.product.map((link) => (
                <FooterLinksItem key={link.label} href={link.href} locale={locale} sectionKey="product">
                  {footerT(`links.${link.label}`)}
                </FooterLinksItem>
              ))}
            </ul>
          </div>

          <div className="space-y-6 lg:col-span-2">
            <FooterSectionHeading sectionKey="support" title={footerT('sections.support')} />
            <ul className="space-y-3 font-mono text-sm">
              {FOOTER_LINKS.support.map((link) => (
                <FooterLinksItem key={link.label} href={link.href} locale={locale} sectionKey="support">
                  {footerT(`links.${link.label}`)}
                </FooterLinksItem>
              ))}
            </ul>
          </div>

          <div className="space-y-6 lg:col-span-2">
            <FooterSectionHeading sectionKey="knowledge" title={footerT('sections.knowledge')} />
            <ul className="space-y-3 font-mono text-sm">
              {KNOWLEDGE_LINKS.map((link) => (
                <FooterLinksItem
                  key={link.href}
                  href={link.href}
                  locale={locale}
                  sectionKey="knowledge"
                  seoCta={link.href.replace('/', '') || 'home'}
                  seoZone="footer_knowledge"
                >
                  {footerT(`knowledgeLinks.${link.labelKey}`)}
                </FooterLinksItem>
              ))}
            </ul>
          </div>

          <div className="space-y-6 lg:col-span-2">
            <FooterSectionHeading sectionKey="payments" title={footerT('sections.paymentMethods')} />
            <div className="grid max-w-[12rem] grid-cols-3 gap-x-3 gap-y-2">
              {PAYMENT_METHODS.map((method) => (
                <PaymentBrandIcon key={method.id} brand={method.id} label={method.label} />
              ))}
            </div>
          </div>
        </div>

        <div className="relative flex flex-col items-center justify-between gap-4 border-t border-grid-line/20 pt-8 md:flex-row">
          <FooterLiveStrip
            encryptionLabel={headerT('encryptionLabel')}
            encryptionValue={headerT('encryptionValue')}
            integrity={headerT('integrity')}
            operationalStatus={footerT('operationalStatus')}
            systemLabel={headerT('systemLabel')}
            year={COPYRIGHT_YEAR}
          />
        </div>
      </div>
    </footer>
  );
}

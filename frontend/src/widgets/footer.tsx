import Link from 'next/link';
import { ArrowRight, Cpu, Send, Shield, Terminal, Zap } from 'lucide-react';
import { getTranslations } from 'next-intl/server';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
  { label: 'Guides', href: '/guides' },
  { label: 'Compare', href: '/compare' },
  { label: 'Devices', href: '/devices' },
  { label: 'Trust center', href: '/trust' },
  { label: 'Audits', href: '/audits' },
] as const;

export async function Footer() {
  const footerT = await getTranslations('Footer');
  const headerT = await getTranslations('Header');

  return (
    <footer className="relative w-full bg-terminal-bg border-t border-grid-line/50 overflow-hidden pt-16 pb-8">
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-0 left-1/4 w-full h-px bg-gradient-to-r from-transparent via-neon-cyan/50 to-transparent opacity-50 blur-[1px]" />
        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-neon-purple/10 dark:bg-neon-purple/5 rounded-full blur-[100px]" />
        <div className="absolute top-0 left-0 w-[300px] h-[300px] bg-neon-cyan/10 dark:bg-neon-cyan/5 rounded-full blur-[80px]" />
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{ backgroundImage: "url('/grid-pattern.svg')" }}
        />
      </div>

      <div className="container relative z-10 px-6 mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-12 mb-16">
          <div className="lg:col-span-4 space-y-6">
            <Link href="/" className="inline-flex items-center gap-2 group">
              <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-neon-cyan/20 to-neon-purple/20 border border-neon-cyan/30 group-hover:border-neon-cyan/60 transition-colors">
                <Shield className="h-6 w-6 text-neon-cyan group-hover:animate-pulse" />
              </div>
              <span className="font-display text-2xl font-bold tracking-tight text-white group-hover:text-neon-cyan transition-colors">
                Cyber<span className="text-neon-cyan">VPN</span>
              </span>
            </Link>

            <p className="text-muted-foreground font-mono text-sm leading-relaxed max-w-sm">
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
                      className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/40 bg-background/50 text-muted-foreground hover:text-neon-cyan hover:border-neon-cyan/50 hover:bg-neon-cyan/10 transition-all duration-300 group"
                      data-seo-cta={href.includes('t.me') ? 'telegram' : undefined}
                      data-seo-zone={href.includes('t.me') ? 'footer_entity' : undefined}
                    >
                      <Icon className="h-4 w-4 group-hover:scale-110 transition-transform" />
                      <span className="sr-only">{label}</span>
                    </a>
                  ) : (
                    <Link
                      href={href}
                      className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-grid-line/40 bg-background/50 text-muted-foreground hover:text-neon-cyan hover:border-neon-cyan/50 hover:bg-neon-cyan/10 transition-all duration-300 group"
                      data-seo-cta={href === '/docs' ? 'docs' : undefined}
                      data-seo-zone={href === '/docs' ? 'footer_entity' : undefined}
                    >
                      <Icon className="h-4 w-4 group-hover:scale-110 transition-transform" />
                      <span className="sr-only">{label}</span>
                    </Link>
                  )}
                </MagneticButton>
              ))}
            </div>
          </div>

          <div className="lg:col-span-2 space-y-6">
            <h4 className="font-display text-lg font-bold text-foreground flex items-center gap-2">
              <Terminal className="h-4 w-4 text-neon-purple" />
              Product
            </h4>
            <ul className="space-y-3 font-mono text-sm">
              {FOOTER_LINKS.product.map((link) => (
                <li key={link.label}>
                  <Link href={link.href} className="group inline-flex items-center gap-2 text-muted-foreground hover:text-white transition-colors py-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan opacity-0 scale-0 group-hover:opacity-100 group-hover:scale-125 transition-all duration-300" />
                    <span className="transition-transform duration-300 group-hover:translate-x-1">
                      {footerT(`links.${link.label}`)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="lg:col-span-2 space-y-6">
            <h4 className="font-display text-lg font-bold text-foreground flex items-center gap-2">
              <Cpu className="h-4 w-4 text-matrix-green" />
              Support
            </h4>
            <ul className="space-y-3 font-mono text-sm">
              {FOOTER_LINKS.support.map((link) => (
                <li key={link.label}>
                  <Link href={link.href} className="group inline-flex items-center gap-2 text-muted-foreground hover:text-white transition-colors py-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-matrix-green opacity-0 scale-0 group-hover:opacity-100 group-hover:scale-125 transition-all duration-300" />
                    <span className="transition-transform duration-300 group-hover:translate-x-1">
                      {footerT(`links.${link.label}`)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>

            <div className="border-t border-grid-line/20 pt-5">
              <div className="text-xs font-mono uppercase tracking-[0.3em] text-neon-purple">
                Knowledge
              </div>
              <ul className="mt-4 space-y-3 font-mono text-sm">
                {KNOWLEDGE_LINKS.map((link) => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="group inline-flex items-center gap-2 text-muted-foreground hover:text-white transition-colors py-1"
                      data-seo-zone="footer_knowledge"
                      data-seo-cta={link.href.replace('/', '') || 'home'}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-neon-purple opacity-0 scale-0 group-hover:opacity-100 group-hover:scale-125 transition-all duration-300" />
                      <span className="transition-transform duration-300 group-hover:translate-x-1">
                        {link.label}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="lg:col-span-4 space-y-6">
            <h4 className="font-display text-lg font-bold text-foreground flex items-center gap-2">
              <Zap className="h-4 w-4 text-warning" />
              Stay Connected
            </h4>
            <p className="text-muted-foreground font-mono text-sm">
              Join our encrypted frequency. Get updates on server locations, security protocols, and zero-day patches.
            </p>

            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-neon-cyan via-neon-purple to-neon-cyan rounded-lg opacity-30 group-hover:opacity-100 transition duration-500 blur group-hover:blur-md animate-gradient-x" />
              <div className="relative flex gap-2 p-1 bg-terminal-bg rounded-lg border border-grid-line/50">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground-low font-mono text-xs z-10 select-none">
                  root@user:~$
                </span>
                <Input
                  className="bg-transparent border-none text-foreground pl-32 focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/30 font-mono h-10"
                  placeholder="enter_email.exe"
                />
                <Button size="sm" className="bg-neon-cyan/10 text-neon-cyan hover:bg-neon-cyan hover:text-black font-mono tracking-wider border border-neon-cyan/20 h-10 px-4 transition-all">
                  <span className="mr-2">INIT</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="pt-6 flex flex-wrap gap-4 text-xs font-mono text-muted-foreground-low">
              {FOOTER_LINKS.legal.map((link) => (
                <Link key={link.label} href={link.href} className="hover:text-neon-cyan transition-colors py-1 px-1">
                  {footerT(`links.${link.label}`)}
                </Link>
              ))}
            </div>
          </div>
        </div>

        <div className="pt-8 border-t border-grid-line/20 flex flex-col md:flex-row items-center justify-between gap-4 relative">
          <FooterLiveStrip
            encryptionLabel={headerT('encryptionLabel')}
            encryptionValue={headerT('encryptionValue')}
            integrity={headerT('integrity')}
            systemLabel={headerT('systemLabel')}
            year={COPYRIGHT_YEAR}
          />
        </div>
      </div>
    </footer>
  );
}

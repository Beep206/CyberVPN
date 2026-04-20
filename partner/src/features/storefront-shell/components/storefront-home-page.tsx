import { Link } from '@/i18n/navigation';
import type { StorefrontSurfaceContext } from '@/features/storefront-shell/lib/runtime';

type StorefrontHomeLabels = {
  eyebrow: string;
  title: string;
  subtitle: string;
  checkoutCta: string;
  legalCta: string;
  supportCta: string;
  loginCta: string;
  merchantLabel: string;
  supportLabel: string;
  communicationLabel: string;
  realmLabel: string;
  storefrontKeyLabel: string;
  hostLabel: string;
  billingDescriptorLabel: string;
  refundModelLabel: string;
  chargebackModelLabel: string;
};

export function StorefrontHomePage({
  surfaceContext,
  labels,
}: {
  surfaceContext: StorefrontSurfaceContext;
  labels: StorefrontHomeLabels;
}) {
  return (
    <div className="relative mx-auto flex min-h-[calc(100dvh-8rem)] w-full max-w-6xl flex-col gap-8 px-4 py-8 md:px-6 md:py-12">
      <section className="grid gap-6 rounded-[2rem] border border-grid-line/20 bg-terminal-surface/45 p-6 shadow-[0_0_32px_rgba(0,255,255,0.06)] backdrop-blur md:grid-cols-[1.4fr_0.9fr] md:p-8">
        <div className="space-y-5">
          <div className="inline-flex items-center rounded-full border border-neon-cyan/30 bg-neon-cyan/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.24em] text-neon-cyan">
            {labels.eyebrow}
          </div>
          <div className="space-y-3">
            <h1 className="max-w-3xl text-3xl font-display font-black uppercase tracking-[0.1em] text-foreground md:text-5xl">
              {labels.title}
            </h1>
            <p className="max-w-2xl font-mono text-sm leading-6 text-muted-foreground md:text-base">
              {labels.subtitle}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href={surfaceContext.routes.checkout}
              className="inline-flex items-center justify-center rounded-lg bg-neon-cyan px-5 py-3 font-mono text-sm font-bold uppercase tracking-[0.18em] text-black transition-colors hover:bg-neon-cyan/90"
            >
              {labels.checkoutCta}
            </Link>
            <Link
              href={surfaceContext.routes.legal}
              className="inline-flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-bg/60 px-5 py-3 font-mono text-sm uppercase tracking-[0.18em] text-neon-cyan transition-colors hover:border-neon-cyan/40"
            >
              {labels.legalCta}
            </Link>
            <Link
              href={surfaceContext.routes.support}
              className="inline-flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-bg/60 px-5 py-3 font-mono text-sm uppercase tracking-[0.18em] text-neon-purple transition-colors hover:border-neon-purple/40"
            >
              {labels.supportCta}
            </Link>
            <Link
              href={surfaceContext.routes.login}
              className="inline-flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-bg/60 px-5 py-3 font-mono text-sm uppercase tracking-[0.18em] text-matrix-green transition-colors hover:border-matrix-green/40"
            >
              {labels.loginCta}
            </Link>
          </div>
        </div>
        <div className="grid gap-4">
          <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">{labels.realmLabel}</p>
            <p className="mt-2 font-display text-lg text-foreground">{surfaceContext.authRealmKey}</p>
            <p className="mt-2 font-mono text-xs text-muted-foreground">{surfaceContext.brandTagline}</p>
          </div>
          <div className="rounded-2xl border border-grid-line/20 bg-terminal-bg/55 p-4">
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">{labels.storefrontKeyLabel}</p>
            <p className="mt-2 font-display text-lg text-foreground">{surfaceContext.storefrontKey}</p>
            <p className="mt-2 font-mono text-xs text-muted-foreground">{labels.hostLabel}: {surfaceContext.host}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">{labels.merchantLabel}</p>
          <h2 className="mt-3 font-display text-xl text-foreground">{surfaceContext.merchantProfile.legalEntityName}</h2>
          <div className="mt-4 space-y-2 font-mono text-sm text-muted-foreground">
            <p>{labels.billingDescriptorLabel}: {surfaceContext.merchantProfile.billingDescriptor}</p>
            <p>{labels.refundModelLabel}: {surfaceContext.merchantProfile.refundResponsibilityModel}</p>
            <p>{labels.chargebackModelLabel}: {surfaceContext.merchantProfile.chargebackLiabilityModel}</p>
          </div>
        </article>
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">{labels.supportLabel}</p>
          <h2 className="mt-3 font-display text-xl text-foreground">{surfaceContext.supportProfile.label}</h2>
          <div className="mt-4 space-y-2 font-mono text-sm text-muted-foreground">
            <p>{surfaceContext.supportProfile.email}</p>
            <p>Response window: {surfaceContext.supportProfile.responseWindow}</p>
            <p>{surfaceContext.supportProfile.helpCenterUrl}</p>
          </div>
        </article>
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">{labels.communicationLabel}</p>
          <h2 className="mt-3 font-display text-xl text-foreground">{surfaceContext.communicationProfile.senderName}</h2>
          <div className="mt-4 space-y-2 font-mono text-sm text-muted-foreground">
            <p>{surfaceContext.communicationProfile.senderEmail}</p>
            <p>Sale channel: {surfaceContext.saleChannel}</p>
            <p>Default currency: {surfaceContext.defaultCurrency}</p>
          </div>
        </article>
      </section>
    </div>
  );
}

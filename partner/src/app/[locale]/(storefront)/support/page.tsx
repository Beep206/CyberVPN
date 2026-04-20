import type { Metadata } from 'next';
import { redirect } from 'next/navigation';
import { Link } from '@/i18n/navigation';
import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { getPartnerSurfaceContext } from '@/features/storefront-shell/lib/server-surface-context';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getCachedTranslations(locale, 'Storefront.meta');
  const surfaceContext = await getPartnerSurfaceContext();

  return withSiteMetadata(
    {
      title: surfaceContext.family === 'storefront'
        ? t('supportTitle', { brandName: surfaceContext.brandName })
        : 'Storefront support',
      description: surfaceContext.family === 'storefront'
        ? t('supportDescription', { brandName: surfaceContext.brandName })
        : 'Storefront support routing.',
    },
    {
      locale,
      canonicalPath: '/support',
      routeType: 'public',
    },
  );
}

export default async function StorefrontSupportRoute({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const surfaceContext = await getPartnerSurfaceContext();

  if (surfaceContext.family !== 'storefront') {
    redirect(`/${locale}/login`);
  }

  const t = await getCachedTranslations(locale, 'Storefront.support');

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-8 md:px-6 md:py-10">
      <section className="rounded-[2rem] border border-grid-line/20 bg-terminal-surface/45 p-6 shadow-[0_0_32px_rgba(0,255,255,0.06)] backdrop-blur md:p-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan">{t('eyebrow')}</p>
        <h1 className="mt-3 text-3xl font-display font-black uppercase tracking-[0.1em] text-foreground md:text-4xl">
          {t('title', { brandName: surfaceContext.brandName })}
        </h1>
        <p className="mt-3 max-w-3xl font-mono text-sm leading-6 text-muted-foreground">
          {t('subtitle')}
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">{t('channelLabel')}</p>
          <h2 className="mt-3 font-display text-xl text-foreground">{surfaceContext.supportProfile.label}</h2>
          <div className="mt-4 space-y-2 font-mono text-sm text-muted-foreground">
            <p>{surfaceContext.supportProfile.email}</p>
            <p>{t('responseWindowLabel')}: {surfaceContext.supportProfile.responseWindow}</p>
            <p>{surfaceContext.supportProfile.helpCenterUrl}</p>
          </div>
        </article>
        <article className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-surface/35 p-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">{t('communicationLabel')}</p>
          <h2 className="mt-3 font-display text-xl text-foreground">{surfaceContext.communicationProfile.senderName}</h2>
          <div className="mt-4 space-y-2 font-mono text-sm text-muted-foreground">
            <p>{surfaceContext.communicationProfile.senderEmail}</p>
            <p>{t('realmLabel')}: {surfaceContext.authRealmKey}</p>
            <p>{t('storefrontLabel')}: {surfaceContext.storefrontKey}</p>
          </div>
        </article>
      </section>

      <section className="rounded-[1.5rem] border border-grid-line/20 bg-terminal-bg/60 p-5">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-neon-cyan">Support routing boundary</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
            <h2 className="font-display text-lg text-foreground">Customer storefront lane</h2>
            <p className="mt-3 font-mono text-sm leading-6 text-muted-foreground">
              Use this branded support profile for storefront checkout, legal-surface, and service-access issues tied to {surfaceContext.brandName}.
            </p>
          </article>
          <article className="rounded-2xl border border-grid-line/20 bg-terminal-surface/35 p-4">
            <h2 className="font-display text-lg text-foreground">Partner operator lane</h2>
            <p className="mt-3 font-mono text-sm leading-6 text-muted-foreground">
              Workspace onboarding, payout, compliance, and attribution questions stay on the dedicated partner portal workflow and must not reuse customer storefront messaging.
            </p>
          </article>
        </div>
      </section>

      <div className="flex flex-wrap gap-3">
        <Link
          href={surfaceContext.routes.checkout}
          className="inline-flex items-center justify-center rounded-lg bg-neon-cyan px-4 py-3 font-mono text-sm font-bold uppercase tracking-[0.18em] text-black transition-colors hover:bg-neon-cyan/90"
        >
          {t('checkoutCta')}
        </Link>
        <Link
          href={surfaceContext.routes.legal}
          className="inline-flex items-center justify-center rounded-lg border border-grid-line/30 bg-terminal-bg/60 px-4 py-3 font-mono text-sm uppercase tracking-[0.18em] text-neon-purple transition-colors hover:border-neon-purple/40"
        >
          {t('legalCta')}
        </Link>
      </div>
    </div>
  );
}

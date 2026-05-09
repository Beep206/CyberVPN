import { getTranslations } from 'next-intl/server';

import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';

const ALLOWED_USE_ITEMS = [
    'privateAccess',
    'personalSubscription',
    'support',
] as const;

const PROHIBITED_ITEMS = [
    'spam',
    'phishing',
    'credentialStuffing',
    'malware',
    'attacks',
    'scraping',
    'illegalContent',
    'rightsAbuse',
    'sanctions',
    'resale',
    'publicProxy',
] as const;

const NETWORK_ITEMS = [
    'fairUse',
    'torrent',
    'nodeRules',
    'automation',
    'configSafety',
] as const;

const ENFORCEMENT_ITEMS = [
    'controls',
    'review',
    'evidence',
    'refunds',
] as const;

const REPORTING_ITEMS = [
    'abuseEmail',
    'supportEmail',
    'details',
] as const;

type MessageKey = string;

function PolicyList({
    itemKeys,
    path,
    t,
}: {
    itemKeys: readonly string[];
    path: string;
    t: (key: MessageKey) => string;
}) {
    return (
        <ul className="list-disc list-inside space-y-2 ml-4">
            {itemKeys.map((itemKey) => (
                <li key={itemKey}>{t(`${path}.${itemKey}`)}</li>
            ))}
        </ul>
    );
}

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'AcceptableUse' });

    return withSiteMetadata({
        title: t('meta.title'),
        description: t('meta.description'),
    }, {
        locale,
        canonicalPath: '/acceptable-use',
        routeType: 'public',
    });
}

export default async function AcceptableUsePage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'AcceptableUse' });

    return (
        <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
            <PublicTerminalHeader locale={locale} />
            <div className="container mx-auto max-w-4xl px-4 py-16">
                <article className="prose prose-invert prose-cyan max-w-none">
                    <h1 className="mb-8 font-display text-4xl font-bold text-matrix-green">
                        {t('title')}
                    </h1>

                    <p className="mb-8 text-lg text-gray-300">
                        {t('lastUpdated')}
                    </p>

                    <p className="mb-12 text-gray-300">
                        {t('intro')}
                    </p>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.scope.title')}
                        </h2>
                        <p className="text-gray-300">{t('sections.scope.content')}</p>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.allowedUse.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={ALLOWED_USE_ITEMS} path="sections.allowedUse.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.prohibited.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <p>{t('sections.prohibited.intro')}</p>
                            <PolicyList itemKeys={PROHIBITED_ITEMS} path="sections.prohibited.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.network.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={NETWORK_ITEMS} path="sections.network.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.enforcement.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={ENFORCEMENT_ITEMS} path="sections.enforcement.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.reporting.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={REPORTING_ITEMS} path="sections.reporting.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.changes.title')}
                        </h2>
                        <p className="text-gray-300">{t('sections.changes.content')}</p>
                    </section>
                </article>
            </div>
            <Footer locale={locale} />
        </main>
    );
}

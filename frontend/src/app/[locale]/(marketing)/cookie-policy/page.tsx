import { getTranslations } from 'next-intl/server';

import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';

const INVENTORY_ITEMS = [
    'locale',
    'auth',
    'transaction',
    'observability',
    'telegram',
    'thirdParty',
] as const;

const CONSENT_ITEMS = [
    'necessary',
    'nonEssential',
    'marketing',
    'changes',
] as const;

const RETENTION_ITEMS = [
    'auth',
    'transactions',
    'locale',
    'telemetry',
] as const;

const CONTROL_ITEMS = [
    'browser',
    'logout',
    'support',
] as const;

const BLOCKER_ITEMS = [
    'browserInventory',
    'setCookie',
    'consent',
    'legal',
    'pii',
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
    const t = await getTranslations({ locale, namespace: 'CookiePolicy' });

    return withSiteMetadata({
        title: t('meta.title'),
        description: t('meta.description'),
    }, {
        locale,
        canonicalPath: '/cookie-policy',
        routeType: 'public',
    });
}

export default async function CookiePolicyPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'CookiePolicy' });

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
                            {t('sections.inventory.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <p>{t('sections.inventory.intro')}</p>
                            <PolicyList itemKeys={INVENTORY_ITEMS} path="sections.inventory.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.consent.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={CONSENT_ITEMS} path="sections.consent.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.retention.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={RETENTION_ITEMS} path="sections.retention.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.controls.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={CONTROL_ITEMS} path="sections.controls.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.goLiveBlockers.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={BLOCKER_ITEMS} path="sections.goLiveBlockers.items" t={t} />
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

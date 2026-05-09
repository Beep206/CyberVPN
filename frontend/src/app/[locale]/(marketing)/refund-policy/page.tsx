import { getTranslations } from 'next-intl/server';

import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { Footer } from '@/widgets/footer';
import { PublicTerminalHeader } from '@/widgets/public-terminal-header';

const REVIEW_ITEMS = [
    'noGuarantee',
    'manualReview',
    'paidNoAccess',
    'duplicate',
    'serviceFault',
    'abuse',
    'fees',
] as const;

const PROVIDER_ITEMS = [
    'payram',
    'nowpayments',
    'cryptobot',
    'telegramStars',
    'digiseller',
    'yookassa',
] as const;

const ACCESS_ITEMS = [
    'fullRefund',
    'partialRefund',
    'trial',
    'pending',
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
    const t = await getTranslations({ locale, namespace: 'RefundPolicy' });

    return withSiteMetadata({
        title: t('meta.title'),
        description: t('meta.description'),
    }, {
        locale,
        canonicalPath: '/refund-policy',
        routeType: 'public',
    });
}

export default async function RefundPolicyPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'RefundPolicy' });

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
                            {t('sections.request.title')}
                        </h2>
                        <p className="text-gray-300">{t('sections.request.content')}</p>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.review.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={REVIEW_ITEMS} path="sections.review.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.providerRules.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={PROVIDER_ITEMS} path="sections.providerRules.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.access.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <PolicyList itemKeys={ACCESS_ITEMS} path="sections.access.items" t={t} />
                        </div>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.timing.title')}
                        </h2>
                        <p className="text-gray-300">{t('sections.timing.content')}</p>
                    </section>

                    <section className="mb-12">
                        <h2 className="mb-4 font-display text-2xl font-semibold text-neon-cyan">
                            {t('sections.evidence.title')}
                        </h2>
                        <p className="text-gray-300">{t('sections.evidence.content')}</p>
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

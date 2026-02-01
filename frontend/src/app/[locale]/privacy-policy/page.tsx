import { getTranslations } from 'next-intl/server';
import { TerminalHeader } from '@/widgets/terminal-header';
import { Footer } from '@/widgets/footer';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'PrivacyPolicy' });

    return {
        title: t('meta.title'),
        description: t('meta.description'),
    };
}

export default async function PrivacyPolicyPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'PrivacyPolicy' });

    return (
        <main className="min-h-screen bg-terminal-bg selection:bg-neon-pink selection:text-black">
            <TerminalHeader />
            <div className="container mx-auto px-4 py-16 max-w-4xl">
                <article className="prose prose-invert prose-cyan max-w-none">
                    <h1 className="text-4xl font-display font-bold text-matrix-green mb-8">
                        {t('title')}
                    </h1>

                    <p className="text-lg text-gray-300 mb-8">
                        {t('lastUpdated')}: {new Date().toLocaleDateString(locale)}
                    </p>

                    {/* Data Collection */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">
                            {t('sections.dataCollection.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <p>{t('sections.dataCollection.intro')}</p>
                            <ul className="list-disc list-inside space-y-2 ml-4">
                                <li>{t('sections.dataCollection.items.accountInfo')}</li>
                                <li>{t('sections.dataCollection.items.paymentInfo')}</li>
                                <li>{t('sections.dataCollection.items.deviceInfo')}</li>
                                <li>{t('sections.dataCollection.items.usageStats')}</li>
                            </ul>
                        </div>
                    </section>

                    {/* No-Log Policy */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">
                            {t('sections.noLogPolicy.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <p className="font-semibold text-matrix-green">
                                {t('sections.noLogPolicy.statement')}
                            </p>
                            <p>{t('sections.noLogPolicy.details')}</p>
                            <ul className="list-disc list-inside space-y-2 ml-4">
                                <li>{t('sections.noLogPolicy.notLogged.browsing')}</li>
                                <li>{t('sections.noLogPolicy.notLogged.connections')}</li>
                                <li>{t('sections.noLogPolicy.notLogged.traffic')}</li>
                                <li>{t('sections.noLogPolicy.notLogged.dns')}</li>
                            </ul>
                        </div>
                    </section>

                    {/* Data Retention */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">
                            {t('sections.dataRetention.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <p>{t('sections.dataRetention.description')}</p>
                            <ul className="list-disc list-inside space-y-2 ml-4">
                                <li>{t('sections.dataRetention.policies.accountData')}</li>
                                <li>{t('sections.dataRetention.policies.paymentRecords')}</li>
                                <li>{t('sections.dataRetention.policies.supportLogs')}</li>
                                <li>{t('sections.dataRetention.policies.deletedAccounts')}</li>
                            </ul>
                        </div>
                    </section>

                    {/* GDPR Rights */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">
                            {t('sections.gdprRights.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <p>{t('sections.gdprRights.intro')}</p>
                            <ul className="list-disc list-inside space-y-2 ml-4">
                                <li><strong>{t('sections.gdprRights.rights.access.title')}:</strong> {t('sections.gdprRights.rights.access.description')}</li>
                                <li><strong>{t('sections.gdprRights.rights.rectification.title')}:</strong> {t('sections.gdprRights.rights.rectification.description')}</li>
                                <li><strong>{t('sections.gdprRights.rights.erasure.title')}:</strong> {t('sections.gdprRights.rights.erasure.description')}</li>
                                <li><strong>{t('sections.gdprRights.rights.portability.title')}:</strong> {t('sections.gdprRights.rights.portability.description')}</li>
                                <li><strong>{t('sections.gdprRights.rights.objection.title')}:</strong> {t('sections.gdprRights.rights.objection.description')}</li>
                            </ul>
                        </div>
                    </section>

                    {/* Data Security */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">
                            {t('sections.dataSecurity.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <p>{t('sections.dataSecurity.description')}</p>
                            <ul className="list-disc list-inside space-y-2 ml-4">
                                <li>{t('sections.dataSecurity.measures.encryption')}</li>
                                <li>{t('sections.dataSecurity.measures.accessControl')}</li>
                                <li>{t('sections.dataSecurity.measures.secureProtocols')}</li>
                                <li>{t('sections.dataSecurity.measures.regularAudits')}</li>
                            </ul>
                        </div>
                    </section>

                    {/* Third-Party Services */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">
                            {t('sections.thirdParty.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <p>{t('sections.thirdParty.description')}</p>
                            <ul className="list-disc list-inside space-y-2 ml-4">
                                <li>{t('sections.thirdParty.services.payment')}</li>
                                <li>{t('sections.thirdParty.services.analytics')}</li>
                                <li>{t('sections.thirdParty.services.infrastructure')}</li>
                            </ul>
                        </div>
                    </section>

                    {/* Contact Information */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">
                            {t('sections.contact.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <p>{t('sections.contact.intro')}</p>
                            <div className="bg-terminal-bg-light p-6 rounded-lg border border-neon-cyan/20">
                                <p><strong>{t('sections.contact.email')}:</strong> privacy@cybervpn.app</p>
                                <p><strong>{t('sections.contact.address')}:</strong> {t('sections.contact.addressLine')}</p>
                            </div>
                        </div>
                    </section>

                    {/* Changes to Policy */}
                    <section className="mb-12">
                        <h2 className="text-2xl font-display font-semibold text-neon-cyan mb-4">
                            {t('sections.changes.title')}
                        </h2>
                        <div className="space-y-4 text-gray-300">
                            <p>{t('sections.changes.description')}</p>
                        </div>
                    </section>
                </article>
            </div>
            <Footer />
        </main>
    );
}

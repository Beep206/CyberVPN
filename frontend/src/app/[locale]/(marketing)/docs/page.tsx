import type { BreadcrumbList, TechArticle } from 'schema-dts';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { JsonLd } from '@/shared/lib/json-ld';
import {
  buildBreadcrumbListStructuredData,
  buildTechArticleStructuredData,
} from '@/shared/lib/structured-data';
import { DocsContainer } from '@/widgets/docs-container';
import { DocsContentServer } from '@/widgets/docs-content-server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    const t = await getTranslations({ locale, namespace: 'Docs' });

    return withSiteMetadata({
        title: t('meta_title'),
        description: t('meta_description'),
    }, {
        locale,
        canonicalPath: '/docs',
        routeType: 'public',
    });
}

export default async function DocsPage({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    setRequestLocale(locale);
    const t = await getTranslations({ locale, namespace: 'Docs' });
    const pageTitle = t('meta_title');
    const pageDescription = t('meta_description');
    const docsStructuredData = buildTechArticleStructuredData({
        locale,
        path: '/docs',
        title: pageTitle,
        description: pageDescription,
        sections: [
            t('section_getting_started'),
            t('section_routing'),
            t('section_security'),
            t('section_api'),
        ],
    });
    const breadcrumbStructuredData = buildBreadcrumbListStructuredData({
        locale,
        items: [
            { name: 'Home', path: '/' },
            { name: pageTitle, path: '/docs' },
        ],
    });

    return (
        <>
            <main className="w-full h-full relative">
                <div className="max-w-[1440px] mx-auto w-full">
                    <DocsContainer content={<DocsContentServer />} />
                </div>
            </main>

            <JsonLd<TechArticle> data={docsStructuredData} />
            <JsonLd<BreadcrumbList> data={breadcrumbStructuredData} />
        </>
    );
}

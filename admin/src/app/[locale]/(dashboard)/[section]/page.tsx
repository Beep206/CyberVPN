import { notFound } from 'next/navigation';
import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { AdminSectionOverview } from '@/shared/ui/pages/admin-section-overview';
import {
  ADMIN_NAV_ITEMS,
  ADMIN_SECTION_OVERVIEWS,
  ADMIN_SECTION_SLUGS,
  type AdminSectionSlug,
  isAdminSectionSlug,
} from '@/features/admin-shell/config/section-registry';

function assertAdminSection(section: string): asserts section is AdminSectionSlug {
  if (!isAdminSectionSlug(section)) {
    notFound();
  }
}

export function generateStaticParams() {
  return ADMIN_SECTION_SLUGS.map((section) => ({ section }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; section: string }>;
}) {
  const { locale, section } = await params;
  assertAdminSection(section);

  const t = await getCachedTranslations(locale, 'Sections');

  return withSiteMetadata(
    {
      title: t(`${section}.metaTitle`),
      description: t(`${section}.description`),
    },
    {
      locale,
      routeType: 'private',
      canonicalPath: `/${section}`,
    },
  );
}

export default async function AdminSectionPage({
  params,
}: {
  params: Promise<{ locale: string; section: string }>;
}) {
  const { locale, section } = await params;
  assertAdminSection(section);

  const t = await getCachedTranslations(locale, 'Sections');
  const config = ADMIN_SECTION_OVERVIEWS[section];
  const navItem = ADMIN_NAV_ITEMS.find((item) => item.href === `/${section}`);

  if (!navItem) {
    notFound();
  }

  return (
    <AdminSectionOverview
      icon={navItem.icon}
      title={t(`${section}.title`)}
      description={t(`${section}.description`)}
      currentState={t(`${section}.currentState`)}
      backendCoverage={t(`${section}.backendCoverage`)}
      nextFocus={t(`${section}.nextFocus`)}
      availableNowLabel={t('common.availableNow')}
      nextModulesLabel={t('common.nextModules')}
      currentStateLabel={t('common.currentState')}
      backendCoverageLabel={t('common.backendCoverage')}
      nextFocusLabel={t('common.nextFocus')}
      returnToDashboardLabel={t('common.returnToDashboard')}
      availableNow={config.availableNow.map((item) => t(`${section}.availableNow.${item}`))}
      nextModules={config.nextModules.map((item) => t(`${section}.nextModules.${item}`))}
      readinessTone={config.readinessTone}
    />
  );
}

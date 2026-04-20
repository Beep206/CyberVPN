import { notFound } from 'next/navigation';
import { getCachedTranslations } from '@/i18n/server';
import { withSiteMetadata } from '@/shared/lib/site-metadata';
import { PartnerSectionOverviewClient } from '@/features/partner-portal-state/components/partner-section-overview-client';
import {
  PARTNER_NAV_ITEMS,
  PARTNER_SECTION_OVERVIEWS,
  PARTNER_SECTION_SLUGS,
  type PartnerSectionSlug,
  isPartnerSectionSlug,
} from '@/features/partner-shell/config/section-registry';

function assertPartnerSection(
  section: string,
): asserts section is PartnerSectionSlug {
  if (!isPartnerSectionSlug(section)) {
    notFound();
  }
}

export function generateStaticParams() {
  return PARTNER_SECTION_SLUGS.map((section) => ({ section }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; section: string }>;
}) {
  const { locale, section } = await params;
  assertPartnerSection(section);

  const sectionT = await getCachedTranslations(locale, 'Sections');
  const navT = await getCachedTranslations(locale, 'Navigation');
  const navItem = PARTNER_NAV_ITEMS.find((item) => item.href === `/${section}`);

  if (!navItem) {
    notFound();
  }

  const sectionLabel = navT(navItem.labelKey);
  const sectionHint = navT(navItem.hintKey);

  return withSiteMetadata(
    {
      title: sectionT('common.metaTitle', { section: sectionLabel }),
      description: sectionHint,
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
  assertPartnerSection(section);

  const sectionT = await getCachedTranslations(locale, 'Sections');
  const navT = await getCachedTranslations(locale, 'Navigation');
  const config = PARTNER_SECTION_OVERVIEWS[section];
  const navItem = PARTNER_NAV_ITEMS.find((item) => item.href === `/${section}`);

  if (!navItem) {
    notFound();
  }

  const sectionLabel = navT(navItem.labelKey);
  const sectionHint = navT(navItem.hintKey);
  const accessStage = sectionT(`common.accessStages.${config.accessStage}`);

  return (
    <PartnerSectionOverviewClient
      section={section}
      title={sectionLabel}
      description={sectionHint}
      currentState={sectionT('common.currentStateTemplate', { section: sectionLabel })}
      backendCoverage={sectionT('common.backendCoverageTemplate', {
        phase: config.phaseTarget,
        ring: config.releaseRing,
      })}
      nextFocus={sectionT('common.nextFocusTemplate', {
        section: sectionLabel,
        phase: config.phaseTarget,
        accessStage,
      })}
      availableNowLabel={sectionT('common.availableNow')}
      nextModulesLabel={sectionT('common.nextModules')}
      currentStateLabel={sectionT('common.currentState')}
      backendCoverageLabel={sectionT('common.backendCoverage')}
      nextFocusLabel={sectionT('common.nextFocus')}
      returnToDashboardLabel={sectionT('common.returnToDashboard')}
      availableNow={config.availableNow.map((item) => sectionT(`common.availableNowItems.${item}`))}
      nextModules={config.nextModules.map((item) => sectionT(`common.nextModuleItems.${item}`))}
      readinessTone={config.readinessTone}
      requiredAccessLabel={accessStage}
    />
  );
}

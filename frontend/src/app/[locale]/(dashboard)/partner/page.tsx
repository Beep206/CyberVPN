import { notFound } from 'next/navigation';
import { canStage1CustomerDashboardSurfaceAccess } from '@/shared/lib/stage1-customer-surface-policy';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

interface PartnerPageProps {
  params: Promise<{
    locale: string;
  }>;
}

export async function generateMetadata({ params }: PartnerPageProps) {
  const { locale } = await params;

  return withSiteMetadata({
    title: 'Not Found',
    description: 'This customer dashboard surface is not available during the current public release.',
  }, {
    locale,
    canonicalPath: '/partner',
    routeType: 'private',
  });
}

export default async function PartnerPage({ params }: PartnerPageProps) {
  if (!canStage1CustomerDashboardSurfaceAccess('partner')) {
    notFound();
  }

  await params;

  return null;
}

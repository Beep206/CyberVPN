import type { ReactNode } from 'react';
import { redirect } from 'next/navigation';
import { getPartnerSurfaceContext } from '@/features/storefront-shell/lib/server-surface-context';
import { canPartnerSurfaceAccess } from '@/shared/lib/surface-policy';

export default async function LegacyAdminRoutesLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const surfaceContext = await getPartnerSurfaceContext();

  if (!canPartnerSurfaceAccess(surfaceContext.family, 'internal_admin_routes')) {
    redirect(`/${locale}/dashboard`);
  }

  return <>{children}</>;
}

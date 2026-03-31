import type { Metadata } from 'next';
import { withSiteMetadata } from '@/shared/lib/site-metadata';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;

  return withSiteMetadata(
    {
      title: 'Inception Effect Test | CyberVPN',
      description: 'Internal animation verification route for UI experiments.',
    },
    {
      locale,
      routeType: 'private',
    },
  );
}

export default function TestAnimationLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

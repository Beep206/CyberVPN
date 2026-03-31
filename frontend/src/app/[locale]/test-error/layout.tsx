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
      title: 'Route Error Boundary Test | CyberVPN',
      description: 'Internal error boundary verification route for QA and debugging.',
    },
    {
      locale,
      routeType: 'private',
    },
  );
}

export default function TestErrorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return children;
}

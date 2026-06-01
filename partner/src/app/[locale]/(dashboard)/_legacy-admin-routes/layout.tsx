import type { ReactNode } from 'react';
import { redirect } from 'next/navigation';

export default async function LegacyAdminRoutesLayout({
  params,
}: {
  children: ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  redirect(`/${locale}/dashboard`);
}

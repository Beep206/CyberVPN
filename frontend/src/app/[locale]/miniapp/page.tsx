import { redirect } from 'next/navigation';
import { connection } from 'next/server';

/**
 * Mini App root - redirects to /home
 * This page is only hit when accessing the root of the mini app.
 */
export default async function MiniAppRootPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  await connection();
  const { locale } = await params;
  redirect(`/${locale}/miniapp/home`);
}

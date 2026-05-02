import { redirect } from 'next/navigation';
import { connection } from 'next/server';

export default async function OAuthCallbackPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  await connection();
  const { locale } = await params;
  redirect(`/${locale}/login?oauth_error=deprecated_callback`);
}

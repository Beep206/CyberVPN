import { redirect } from 'next/navigation';

export default async function OAuthCallbackPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  redirect(`/${locale}/login?oauth_error=deprecated_callback`);
}

import { redirect } from 'next/navigation';

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
    const { locale } = await params;
    // Always redirect to dashboard, authentication logic will handle login redirect if needed
    redirect(`/${locale}/dashboard`);
}

import { Construction } from 'lucide-react';
import { getTranslations } from 'next-intl/server';

export default async function PlaceholderPage({
    locale,
}: {
    locale: string;
}) {
    const t = await getTranslations({ locale, namespace: 'Placeholder' });
    return (
        <div className="flex flex-col items-center justify-center h-[60vh] text-center space-y-4">
            <div className="relative">
                <Construction className="h-24 w-24 text-neon-cyan opacity-80 animate-pulse" />
                <div className="absolute inset-0 blur-xl bg-neon-cyan/20 rounded-full" />
            </div>
            <h1 className="text-3xl font-display text-foreground tracking-widest">{t('title')}</h1>
            <p className="text-muted-foreground font-mono max-w-md">
                {t('descriptionLine1')}
                {" "}
                {t('descriptionLine2')}
            </p>
            <div className="text-xs font-cyber text-neon-pink mt-8">{t('errorCode')}</div>
        </div>
    );
}

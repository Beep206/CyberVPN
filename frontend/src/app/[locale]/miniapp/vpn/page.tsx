import { getTranslations } from 'next-intl/server';
import { ShieldCheck } from 'lucide-react';
import { VpnConfigCard } from '../components/VpnConfigCard';

export default async function MiniAppVpnPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: 'MiniApp.vpn' });

  return (
    <div className="mx-auto max-w-screen-sm space-y-4">
      <div className="miniapp-card rounded-lg border p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-xl border border-neon-cyan/30 bg-neon-cyan/10 p-3">
            <ShieldCheck
              className="h-5 w-5 text-neon-cyan"
              aria-hidden="true"
            />
          </div>
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.18em] text-neon-cyan">
              {t('eyebrow')}
            </p>
            <h1 className="mt-2 font-display text-xl">{t('title')}</h1>
            <p className="mt-2 text-sm font-mono text-muted-foreground">
              {t('description')}
            </p>
          </div>
        </div>
      </div>

      <VpnConfigCard page="vpn" />
    </div>
  );
}

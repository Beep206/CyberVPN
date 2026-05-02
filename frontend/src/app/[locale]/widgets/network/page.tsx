import type { Metadata } from 'next';
import { Suspense } from 'react';
import { PublicNetworkEmbedCard } from '@/widgets/network/public-network-embed-card';
import type {
  PublicNetworkWidgetThemeVariant,
  PublicNetworkWidgetType,
} from '@/lib/api/public-network';

type WidgetPageProps = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

const ALLOWED_WIDGET_TYPES: PublicNetworkWidgetType[] = ['network_card', 'uptime_badge', 'speed_badge'];
const ALLOWED_THEME_VARIANTS: PublicNetworkWidgetThemeVariant[] = ['cyber', 'matrix', 'graphite'];

function resolveSingleSearchParam(
  value: string | string[] | undefined,
): string | undefined {
  if (Array.isArray(value)) {
    return value[0];
  }

  return value;
}

export const metadata: Metadata = {
  robots: {
    index: false,
    follow: false,
  },
};

async function NetworkWidgetShell({
  locale,
  searchParams,
}: {
  locale: string;
  searchParams: WidgetPageProps['searchParams'];
}) {
  const resolvedSearchParams = await searchParams;

  const widgetTypeCandidate = resolveSingleSearchParam(resolvedSearchParams.widgetType);
  const themeVariantCandidate = resolveSingleSearchParam(resolvedSearchParams.themeVariant);
  const regionId = resolveSingleSearchParam(resolvedSearchParams.regionId);

  const widgetType = ALLOWED_WIDGET_TYPES.includes(widgetTypeCandidate as PublicNetworkWidgetType)
    ? (widgetTypeCandidate as PublicNetworkWidgetType)
    : 'network_card';
  const themeVariant = ALLOWED_THEME_VARIANTS.includes(themeVariantCandidate as PublicNetworkWidgetThemeVariant)
    ? (themeVariantCandidate as PublicNetworkWidgetThemeVariant)
    : 'cyber';

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(0,255,255,0.1),transparent_32%),linear-gradient(180deg,#02040a_0%,#04070f_100%)] p-4">
      <PublicNetworkEmbedCard
        locale={locale}
        themeVariant={themeVariant}
        widgetType={widgetType}
        regionId={regionId}
      />
    </main>
  );
}

function NetworkWidgetFallback() {
  return (
    <div className="mx-auto w-full max-w-[440px] rounded-[1.75rem] border border-neon-cyan/20 bg-[radial-gradient(circle_at_top,rgba(0,255,255,0.14),transparent_36%),linear-gradient(160deg,rgba(4,10,20,0.98),rgba(2,5,12,0.96))] p-5 font-mono text-sm text-white/70 shadow-[0_0_48px_rgba(0,255,255,0.12)]">
      Loading network widget...
    </div>
  );
}

export default async function NetworkWidgetPage({
  params,
  searchParams,
}: WidgetPageProps) {
  const { locale } = await params;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,rgba(0,255,255,0.1),transparent_32%),linear-gradient(180deg,#02040a_0%,#04070f_100%)] p-4">
      <Suspense fallback={<NetworkWidgetFallback />}>
        <NetworkWidgetShell locale={locale} searchParams={searchParams} />
      </Suspense>
    </main>
  );
}

'use client';

import { reportMiniAppClientError } from '@/features/miniapp-runtime/lib/client-error-telemetry';
import { AlertCircle, RotateCcw, Stethoscope } from 'lucide-react';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { useEffect } from 'react';

export default function MiniAppError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations('MiniApp.error');

  useEffect(() => {
    reportMiniAppClientError({
      eventType: 'miniapp_route_error_boundary',
      errorName: error.name,
      errorMessage: error.message,
      chunk: error.digest,
    });
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full border border-red-400/30 bg-red-500/10">
        <AlertCircle className="h-6 w-6 text-red-300" aria-hidden="true" />
      </div>
      <div className="max-w-sm space-y-2">
        <h1 className="font-display text-lg text-foreground">{t('title')}</h1>
        <p className="text-sm font-mono text-muted-foreground">{t('description')}</p>
        <p className="text-xs font-mono text-muted-foreground">{t('code', { code: error.digest || 'UNKNOWN' })}</p>
      </div>
      <div className="flex flex-wrap justify-center gap-2">
        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-lg border border-grid-line/30 px-3 py-2 text-xs font-mono text-foreground transition-colors hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
        >
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          {t('retry')}
        </button>
        <Link
          href="/miniapp/diagnostics"
          className="inline-flex items-center gap-2 rounded-lg border border-grid-line/30 px-3 py-2 text-xs font-mono text-foreground transition-colors hover:border-neon-cyan/40 hover:text-neon-cyan focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-neon-cyan"
        >
          <Stethoscope className="h-4 w-4" aria-hidden="true" />
          {t('diagnostics')}
        </Link>
      </div>
    </div>
  );
}

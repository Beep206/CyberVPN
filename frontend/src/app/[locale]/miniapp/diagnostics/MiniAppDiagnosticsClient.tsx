'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Activity, CheckCircle2, CircleAlert, RefreshCw } from 'lucide-react';

type ProbeStatus = 'checking' | 'ok' | 'missing' | 'unavailable';

type RuntimeDiagnostics = {
  inTelegram: boolean;
  initDataPresent: boolean;
  initDataLength: number;
  initDataFingerprint: string;
  telegramUserPresent: boolean;
  platform: string;
  version: string;
  viewportHeight: number | null;
  viewportStableHeight: number | null;
  colorScheme: string;
  path: string;
  userAgentLength: number;
};

type NetworkProbe = {
  status: ProbeStatus;
  httpStatus?: number;
  contentType?: string | null;
};

function fingerprint(value: string): string {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return value ? `${value.length}:${(hash >>> 0).toString(16)}` : '0:0';
}

function collectRuntimeDiagnostics(): RuntimeDiagnostics {
  const webApp = window.Telegram?.WebApp;
  const initData = webApp?.initData ?? '';
  return {
    inTelegram: Boolean(webApp),
    initDataPresent: Boolean(initData),
    initDataLength: initData.length,
    initDataFingerprint: fingerprint(initData),
    telegramUserPresent: Boolean(webApp?.initDataUnsafe?.user?.id),
    platform: webApp?.platform ?? 'unknown',
    version: webApp?.version ?? 'unknown',
    viewportHeight: typeof webApp?.viewportHeight === 'number' ? webApp.viewportHeight : null,
    viewportStableHeight: typeof webApp?.viewportStableHeight === 'number' ? webApp.viewportStableHeight : null,
    colorScheme: webApp?.colorScheme ?? 'unknown',
    path: window.location.pathname,
    userAgentLength: navigator.userAgent.length,
  };
}

async function probe(url: string): Promise<NetworkProbe> {
  try {
    const response = await fetch(url, {
      cache: 'no-store',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
    return {
      status: response.ok ? 'ok' : 'unavailable',
      httpStatus: response.status,
      contentType: response.headers.get('content-type'),
    };
  } catch {
    return { status: 'unavailable' };
  }
}

function statusTone(status: ProbeStatus): string {
  if (status === 'ok') return 'text-neon-cyan';
  if (status === 'checking') return 'text-amber-200';
  return 'text-red-300';
}

export function MiniAppDiagnosticsClient({ locale }: { locale: string }) {
  const t = useTranslations('MiniApp.diagnostics');
  const [runtime, setRuntime] = useState<RuntimeDiagnostics | null>(null);
  const [health, setHealth] = useState<NetworkProbe>({ status: 'checking' });
  const [fingerprintProbe, setFingerprintProbe] = useState<NetworkProbe>({ status: 'checking' });
  const [sessionProbe, setSessionProbe] = useState<NetworkProbe>({ status: 'checking' });

  const healthPath = useMemo(() => `/${locale}/miniapp/health`, [locale]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) {
        setRuntime(collectRuntimeDiagnostics());
      }
    });
    void probe(healthPath).then(setHealth);
    void probe('/api/v1/runtime/fingerprint').then(setFingerprintProbe);
    void probe('/api/v1/auth/session').then(setSessionProbe);
    return () => {
      cancelled = true;
    };
  }, [healthPath]);

  const runtimeRows = runtime
    ? [
        ['telegram', runtime.inTelegram ? 'ok' : 'missing', runtime.inTelegram ? t('values.present') : t('values.missing')],
        [
          'initData',
          runtime.initDataPresent ? 'ok' : 'missing',
          runtime.initDataPresent
            ? t('values.initDataPresent', { length: runtime.initDataLength, fingerprint: runtime.initDataFingerprint })
            : t('values.missing'),
        ],
        [
          'user',
          runtime.telegramUserPresent ? 'ok' : 'missing',
          runtime.telegramUserPresent ? t('values.present') : t('values.missing'),
        ],
        ['platform', runtime.platform !== 'unknown' ? 'ok' : 'missing', runtime.platform],
        ['version', runtime.version !== 'unknown' ? 'ok' : 'missing', runtime.version],
        [
          'viewport',
          runtime.viewportHeight ? 'ok' : 'missing',
          runtime.viewportHeight ? `${runtime.viewportHeight}/${runtime.viewportStableHeight ?? '-'}` : t('values.missing'),
        ],
        ['path', 'ok', runtime.path],
        ['userAgent', 'ok', t('values.userAgentLength', { length: runtime.userAgentLength })],
      ] as const
    : [];

  const probeRows = [
    ['health', health, healthPath],
    ['fingerprint', fingerprintProbe, '/api/v1/runtime/fingerprint'],
    ['session', sessionProbe, '/api/v1/auth/session'],
  ] as const;

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
      <div className="rounded-lg border border-grid-line/30 bg-card/80 p-4">
        <div className="flex items-start gap-3">
          <Activity className="mt-1 h-5 w-5 text-neon-cyan" aria-hidden="true" />
          <div>
            <h1 className="font-display text-lg text-foreground">{t('title')}</h1>
            <p className="mt-1 text-sm font-mono text-muted-foreground">{t('description')}</p>
          </div>
        </div>
      </div>

      <section className="rounded-lg border border-grid-line/30 bg-card/80 p-4">
        <h2 className="mb-3 font-display text-sm uppercase tracking-[0.14em] text-foreground">{t('runtimeTitle')}</h2>
        <div className="space-y-2">
          {runtimeRows.map(([key, status, value]) => (
            <div key={key} className="flex items-start justify-between gap-3 border-b border-grid-line/20 pb-2 last:border-b-0">
              <span className="text-xs font-mono text-muted-foreground">{t(`fields.${key}`)}</span>
              <span className={`max-w-[65%] break-words text-right text-xs font-mono ${statusTone(status)}`}>{value}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-grid-line/30 bg-card/80 p-4">
        <h2 className="mb-3 font-display text-sm uppercase tracking-[0.14em] text-foreground">{t('networkTitle')}</h2>
        <div className="space-y-2">
          {probeRows.map(([key, result, path]) => (
            <div key={key} className="flex items-start justify-between gap-3 border-b border-grid-line/20 pb-2 last:border-b-0">
              <span className="text-xs font-mono text-muted-foreground">{t(`fields.${key}`)}</span>
              <span className={`flex max-w-[65%] items-center justify-end gap-2 break-words text-right text-xs font-mono ${statusTone(result.status)}`}>
                {result.status === 'ok' ? <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> : null}
                {result.status === 'checking' ? <RefreshCw className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : null}
                {result.status === 'unavailable' ? <CircleAlert className="h-3.5 w-3.5" aria-hidden="true" /> : null}
                {t(`statuses.${result.status}`)}
                {result.httpStatus ? ` · ${result.httpStatus}` : ''}
                {result.contentType ? ` · ${result.contentType.split(';')[0]}` : ''}
                {` · ${path}`}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

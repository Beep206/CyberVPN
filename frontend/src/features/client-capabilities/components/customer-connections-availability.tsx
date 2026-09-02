'use client';

import { AlertTriangle } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { CustomerVpnServiceStatus } from '@/lib/api/remnawave-status';
import { CustomerConnectionsCard } from './customer-connections-card';

type CustomerConnectionsAvailabilityProps = {
  isError: boolean;
  isPending: boolean;
  status: CustomerVpnServiceStatus | undefined;
  surface: 'dashboard' | 'miniapp';
};

type UnavailableState = 'degraded' | 'error' | 'pending' | 'unavailable';

function getUnavailableState({
  isError,
  isPending,
  status,
}: Pick<CustomerConnectionsAvailabilityProps, 'isError' | 'isPending' | 'status'>): UnavailableState {
  if (isError) {
    return 'error';
  }
  if (isPending) {
    return 'pending';
  }
  if (status?.degraded === true) {
    return 'degraded';
  }
  return 'unavailable';
}

export function CustomerConnectionsAvailability({
  isError,
  isPending,
  status,
  surface,
}: CustomerConnectionsAvailabilityProps) {
  const t = useTranslations(
    surface === 'miniapp'
      ? 'MiniApp.liveConnections'
      : 'Dashboard.vpnServiceStatus.liveConnections',
  );
  const isAvailable = !isPending
    && !isError
    && status?.degraded === false
    && status.connections_available === true;

  if (isAvailable) {
    return <CustomerConnectionsCard surface={surface} />;
  }

  const unavailableState = getUnavailableState({ isError, isPending, status });
  const className = surface === 'miniapp'
    ? 'miniapp-card rounded-lg border p-4'
    : 'rounded-[1.5rem] border border-amber-400/25 bg-terminal-surface/55 p-5 backdrop-blur md:p-6';

  return (
    <section
      aria-labelledby={`${surface}-live-connections-unavailable-title`}
      className={className}
      data-connections-state={unavailableState}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-300" aria-hidden="true" />
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-amber-200">
            {t('eyebrow')}
          </p>
          <h3
            id={`${surface}-live-connections-unavailable-title`}
            className="mt-2 font-display text-lg text-white"
          >
            {t('title')}
          </h3>
          <p role="status" aria-live="polite" className="mt-2 text-sm leading-6 text-amber-100/80">
            {t('errors.unavailable')}
          </p>
        </div>
      </div>
    </section>
  );
}

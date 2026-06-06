'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { DevToolsBootstrap } from '@/app/providers/dev-tools-bootstrap';
import { DevButton } from '@/features/dev/dev-button';

const LazyDevPanel = dynamic(
  () => import('@/features/dev/dev-panel').then((module) => module.DevPanel),
  {
    ssr: false,
  },
);

type DevToolsClientProps = {
  closeButtonLabel: string;
  openButtonLabel: string;
};

export function DevToolsClient({
  closeButtonLabel,
  openButtonLabel,
}: DevToolsClientProps) {
  const [isPanelEnabled, setPanelEnabled] = useState(false);

  return (
    <>
      <DevToolsBootstrap />
      {isPanelEnabled ? (
        <LazyDevPanel
          closeButtonLabel={closeButtonLabel}
          defaultOpen
          openButtonLabel={openButtonLabel}
        />
      ) : (
        <DevButton
          ariaLabel={openButtonLabel}
          onClick={() => setPanelEnabled(true)}
        />
      )}
    </>
  );
}
